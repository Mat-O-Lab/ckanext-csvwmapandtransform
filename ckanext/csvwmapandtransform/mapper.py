import json
import os
import re

import requests

maptomethod_url = os.environ.get("CKAN_MAPTOMETHOD_URL")
rdfconverter_url = os.environ.get("CKAN_RDFCONVERTER_URL")

log = __import__("logging").getLogger(__name__)

def post_request(url, headers, data, files=None):
    try:
        if files:
            # should crate a multipart form upload
            response = requests.post(url, data=data, headers=headers, files=files)
        else:
            # a application json post request
            response = requests.post(url, data=json.dumps(data), headers=headers)
        response.raise_for_status()

    except requests.exceptions.RequestException as e:
        # placeholder for save file / clean-up
        raise SystemExit(e) from None
    return response

# def get_request(url, headers, data, files=None):
#     try:
#         if files:
#             # should crate a multipart form upload
#             response = requests.get(url, data=data, headers=headers, files=files)
#         else:
#             # a application json post request
#             response = requests.get(url, data=json.dumps(data), headers=headers)
#         response.raise_for_status()

#     except requests.exceptions.RequestException as e:
#         # placeholder for save file / clean-up
#         raise SystemExit(e) from None
#     return response


def check_mapping(map_url: str, data_url: str):
    log.debug("checking mapping at: {} with data url: {}".format(map_url,data_url))
    #curl -X 'POST' 'http://docker-dev.iwm.fraunhofer.de:5003/api/checkmapping' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"data_url": "https://raw.githubusercontent.com/Mat-O-Lab/CSVToCSVW/main/examples/example-metadata.json", "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"}'
    #url = rdfconverter_url + "/info"
    #url = rdfconverter_url+ "/api/checkmapping"
    url = "http://docker-dev.iwm.fraunhofer.de:6001"+"/api/checkmapping"
    log.debug("rdf converter api call: {}".format(url))
    data = {"mapping_url": map_url, "data_url": data_url}    
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    r = post_request(url, headers, data)
    #r=requests.get(rdfconverter_url+"/info")
    #log.debug(r)
    if r.status_code == 200:
        res=r.json()
        log.debug("map check results: {}".format(res))
        return res
    else:
        log.debug("map check error: {}".format(r))
        return r

def get_joined_rdf(map_url: str, data_url: str):
    # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/annotation' \ -H 'accept: application/json' \ -H 'Content-Type: application/json' \ -d '{ "data_url": "https://github.com/Mat-O-Lab/CSVToCSVW/raw/main/examples/example.csv", "separator": "auto", "header_separator": "auto", "encoding": "auto" }'
    log.debug("createing joined rdf: {} with data url: {}".format(map_url,data_url))
    #curl -X 'POST' 'http://docker-dev.iwm.fraunhofer.de:5003/api/checkmapping' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"data_url": "https://raw.githubusercontent.com/Mat-O-Lab/CSVToCSVW/main/examples/example-metadata.json", "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"}'
    #url = rdfconverter_url + "/info"
    #url = rdfconverter_url+ "/api/checkmapping"
    #url = rdfconverter_url+"/api/createrdf"
    url = "http://docker-dev.iwm.fraunhofer.de:6001"+"/api/createrdf"
    data = {
        "mapping_url": map_url,
        "data_url": data_url
    }
    headers = {'Content-type': 'application/json',
               'Accept': 'application/json'}
    r = post_request(url, headers, data)
    if r.status_code == 200:
        r=r.json()
        filename=r['filename']
        print("applied {} mapping rules and skipped {}".format(r['num_mappings_applied'],r['num_mappings_skipped']))
        return filename, r['graph'], r['num_mappings_applied'], r['num_mappings_skipped']
    else:
        return None, None, 0, 0

# def annotate_csv_upload(
#     filepath: str,
#     encoding: str = "auto",
# ):
#     # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/annotate_upload?encoding=auto' \ -H 'accept: application/json' \ -H 'Content-Type: multipart/form-data' \ -F 'file=@detection_runs.csv;type=text/csv'
#     url = csvtocsvw_url + "/api/annotate_upload?encoding=auto"
#     headers = {"accept": "application/json"}
#     head, tail = os.path.split(filepath)
#     files = {"file": (tail, open(filepath, "rb"), "text/csv")}
#     response = requests.post(url, headers=headers, files=files)
#     if response.status_code == 200:
#         return response.json()
#     else:
#         return response


# def csvw_to_rdf(
#     meta_url: str,
#     format: str = "turtle",
# ):
#     # curl -X 'POST' \ 'https://csvtocsvw.matolab.org/api/rdf' \ -H 'accept: application/json' \ -H 'Content-Type: application/json' \ -d '{ "metadata_url": "https://github.com/Mat-O-Lab/resources/raw/main/rdfconverter/tests/detection_runs-metadata.json", "format": "turtle" }'
#     url = csvtocsvw_url + "/api/rdf"
#     data = {"metadata_url": meta_url, "format": format}
#     headers = {"Content-type": "application/json", "Accept": "application/json"}
#     # r = requests.post(url, data=json.dumps(data), headers=headers)
#     r = post_request(url, headers, data)
#     if r.status_code == 200:
#         d = r.headers["content-disposition"]
#         fname = re.findall("filename=(.+)", d)[0]
#         print("got serialized table with name {}".format(fname))
#         return fname, r.content
#     else:
#         return False
