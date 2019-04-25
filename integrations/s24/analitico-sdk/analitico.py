import os
import os.path
import requests
import logging
import json
from datetime import datetime

logger = logging.getLogger("analitico")


def time_ms(started_on=None):
    """ Returns the time elapsed since given time in ms """
    return datetime.now() if started_on is None else int((datetime.now() - started_on).total_seconds() * 1000)


class AnaliticoSdk:
    """ Utility methods for Analitico services """

    # stable endpoint
    API_ENDPOINT = "https://s24.analitico.ai/api/"

    # latest and greatest, could be up could be down
    STAGING_API_ENDPOINT = "https://s24.analitico.ai/api/"

    @staticmethod
    def upload_dataset_asset(dataset_id, asset_id, asset_path, token, endpoint=API_ENDPOINT) -> dict:
        """
        Uploads an asset like a csv file to a dataset. If the dataset is configured as
        an extract-transform-load pipeline this will also trigger and update automatically.
        Args:
            dataset_id: The identifier of the dataset, eg: ds_xxxxx
            asset_id: The identifier of the asset, eg: customers.csv
            asset_path: Path of asset on disk
            token: The authorization toke to be used for this call
            endpoint: Analitico APIs endpoint to be used
            assert dataset_id and asset_id and asset_path and token and endpoint
            assert asset_path and os.path.isfile(asset_path)
        Return: a dictionary with the server's reply (asset's information)
        """
        try:
            url = endpoint + "datasets/{}/assets/{}".format(dataset_id, asset_id)
            logger.debug("Analitico.upload_dataset_asset - %s", url)
            asset_path = os.path.expanduser(asset_path)
            with open(asset_path, "rb") as f:
                started_on = time_ms()
                logger.info("Analitico.upload_dataset_asset - uploading %s", asset_id)
                response = requests.post(url, data=f, headers={
                    "Authorization": "Bearer " + token,
                    "Content-Disposition": 'attachment; filename="' + asset_id + '"',
                    'Content-Type': 'text/csv'
                })
                if not response.ok:
                    message = "POST {} - returned {}".format(url, response.text)
                    logger.error(message)
                    raise Exception(message)

                assert response.ok
                logger.info("POST %s - uploaded %s in %d ms", url, asset_id, time_ms(started_on))
                response_json = response.json()
                # logger.info(json.dumps(response_json, indent=4))
                return response_json
        except IOError as exc:
            logger.error("Analitico.upload_dataset_asset - uploading error " + str(exc), exc_info=exc)
            raise exc
