
import json
import requests

# Usage to upload daily sql dump (can be huge)
# response = upload_file_to_analitico('s24-order-sorting', 's24-mysql-dump.sql', 'tok_xxx')
# print(response)

def upload_file_to_analitico(project_id, filename, token):
    """ Uploads given file to analitico cloud storage for processing """
    # obtain a signed upload url
    api_url = 'http://analitico.ai/api/project/' + project_id + '/upload/' + filename
    auth_response = requests.put(api_url, headers={
        'Authorization': token
        })

    if auth_response.status_code != 200:
        raise Exception('Could not obtain an upload url from analitico')
    auth_json = json.loads(auth_response.text)
    auth_url = auth_json['upload_url']

    # use the signed upload url to PUT the file in storage
    print('Uploading %s...' % filename)
    with open(filename, "rb") as f:
        upload_response = requests.put(auth_url, files={
            'upload_file': f
            })

    if upload_response.status_code != 200:
        raise Exception('Could not upload file to cloud storage')
    upload_json = json.loads(upload_response.text)
    print('Uploaded to %s' % upload_json['name'])
    return upload_json


