import json

import ckan.plugins.toolkit as toolkit
import requests

log = __import__("logging").getLogger(__name__)


def post_request(url, headers, data, files=None):
    ssl_verify = toolkit.config.get("ckanext.csvwmapandtransform.ssl_verify")
    if not ssl_verify:
        requests.packages.urllib3.disable_warnings()

    try:
        if files:
            # should crate a multipart form upload
            response = requests.post(
                url, data=data, headers=headers, files=files, verify=ssl_verify
            )
        else:
            # a application json post request
            response = requests.post(
                url, data=json.dumps(data), headers=headers, verify=ssl_verify
            )
        response.raise_for_status()

    except Exception as e:
        # placeholder for save file / clean-up
        log.error(e)
        return None
        # raise SystemExit(e) from None
    return response


def check_mapping(map_url: str, data_url: str, authorization: None):
    rdfconverter_url = toolkit.config.get(
        "ckanext.csvwmapandtransform.rdfconverter_url"
    )
    log.debug("checking mapping at: {} with data url: {}".format(map_url, data_url))
    # curl -X 'POST' 'http://docker-dev.iwm.fraunhofer.de:5003/api/checkmapping' -H 'accept: application/json' -H 'Content-Type: application/json' -d '{"data_url": "https://raw.githubusercontent.com/Mat-O-Lab/CSVToCSVW/main/examples/example-metadata.json", "mapping_url": "https://github.com/Mat-O-Lab/MapToMethod/raw/main/examples/example-map.yaml"}'
    url = rdfconverter_url + "/api/checkmapping"
    log.debug("rdf converter api call: {}".format(url))
    data = {"mapping_url": map_url, "data_url": data_url}
    headers = {"Content-Type": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    r = post_request(url, headers, data)
    # r=requests.get(rdfconverter_url+"/info")
    # log.debug(r)
    if r and r.status_code == 200:
        res = r.json()
        log.debug("map check results: {}".format(res))
        return res
    else:
        log.debug("map check error: {}".format(r))
        return None


def get_joined_rdf(map_url: str, data_url: str, authorization: None):
    log.debug("createing joined rdf: {} with data url: {}".format(map_url, data_url))
    rdfconverter_url = toolkit.config.get(
        "ckanext.csvwmapandtransform.rdfconverter_url"
    )
    url = rdfconverter_url + "/api/createrdf?return_type=turtle"
    data = {"mapping_url": map_url, "data_url": data_url}
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    log.debug(f"headers: {headers}")

    r = post_request(url, headers, data)
    if r and r.status_code == 200:
        r = r.json()
        filename = r["filename"]
        print(
            "applied {} mapping rules and skipped {}".format(
                r["num_mappings_applied"], r["num_mappings_skipped"]
            )
        )
        return (
            filename,
            r["graph"],
            r["num_mappings_applied"],
            r["num_mappings_skipped"],
        )
    else:
        return (
            None,
            None,
            None,
            None,
        )
