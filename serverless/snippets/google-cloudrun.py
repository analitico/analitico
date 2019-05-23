##
## Google Cloudrun deployment is out backup option, deployments end up here only if explicitely specified in job for now
##


def k8_deploy_cloudrun(item: ItemMixin, endpoint: ItemMixin, job: Job, factory: Factory) -> dict:
    """ Takes an item that has already been built into a Docker and deploys it """
    docker = item.get_attribute("docker")
    if docker is None:
        raise AnaliticoException(
            f"{item.id} cannot be deployed to {endpoint.id} because its docker has not been built yet."
        )

    # service name is the id of the endpoint unless otherwise specified
    service = k8_normalize_name(job.get_attribute("service_id", endpoint.id))

    # max concurrent connections per docker
    concurrency = int(job.get_attribute("concurrency", 20))

    # To deploy on Google Cloud Run we use a command like this:
    # https://cloud.google.com/sdk/gcloud/reference/beta/run/deploy
    # gcloud beta run deploy cloudrun02 --image eu.gcr.io/analitico-api/cloudrun02 --set-env-vars=TARGET=Pippo
    cmd_args = [
        "gcloud",
        "beta",
        "run",
        "deploy",
        service,
        "--image",
        docker["image"],
        "--allow-unauthenticated",
        "--concurrency",
        str(concurrency),
        "--region",
        K8_DEFAULT_CLOUDRUN_REGION,
    ]
    cmd_line = " ".join(cmd_args)

    # run build job using google cloud build
    job.append_logs(f"Deploying {item.id} to {endpoint.id} on Google Cloud Run\n{cmd_line}\n\n")
    response = subprocess.run(cmd_args, encoding="utf-8", stdout=PIPE, stderr=PIPE)
    job.append_logs(response.stderr)
    job.append_logs(response.stdout)
    response.check_returncode()

    # Example of response.sterr:
    # Deploying container to Cloud Run service [\x1b[1mep-test-001\x1b[m] in project [\x1b[1manalitico-api\x1b[m] region [\x1b[1mus-central1\x1b[m]\n
    # Deploying new service...\n
    # Setting IAM Policy.........................done\n
    # Creating Revision.......................................................done\n
    # Routing traffic.......................done\n
    # Done.\n

    # This is what it looks like on a Mac:
    # Service [\x1b[1mep-t0est-001\x1b[m] revision [\x1b[1mep-test-001-00001\x1b[m] has been deployed and is serving traffic at \x1b[1mhttps://ep-test-001-zqsrcwjkta-uc.a.run.app\x1b[m\n
    # This is what it looks like on the server (no bash bold escape sequences like \x1b[1m):
    # Service [ep-test-001] revision [ep-test-001-b65066cc-bd08-4e5e-b4fe-aa86c59280be] has been deployed and is serving traffic at https://ep-test-001-zqsrcwjkta-uc.a.run.app\\n

    logs = response.stderr.replace("\x1b[1m", "")  # remove escape sequences
    revision = re_match_group(r"revision \[([a-z0-9-]*)", logs)
    region = re_match_group(r"region \[([a-z0-9-]*)", logs)
    url = re_match_group(r"is serving traffic at (https:\/\/[a-zA-Z0-9-\.]*)", logs)

    # save deployment information inside item and job
    attrs = collections.OrderedDict(
        {
            "type": "google/cloudrun",
            "name": service,
            "revision": revision,
            "region": region,
            "url": url,
            "concurrency": concurrency,
            "docker": docker,
        }
    )
    item.set_attribute("service", attrs), item.save()
    endpoint.set_attribute("service", attrs), endpoint.save()
    job.set_attribute("service", attrs), job.save()
    return attrs
