import json

import ckan.plugins.toolkit as toolkit
import requests

log = __import__("logging").getLogger(__name__)


def post_request(url, headers, data, files=None, timeout=None):
    ssl_verify = toolkit.asbool(
        toolkit.config.get("ckanext.csvwmapandtransform.ssl_verify", True)
    )
    if not ssl_verify:
        log.warning(
            "SSL verification disabled for rdfconverter — set ssl_verify=true in production"
        )
        requests.packages.urllib3.disable_warnings()

    try:
        if files:
            # should create a multipart form upload
            response = requests.post(
                url, data=data, headers=headers, files=files, verify=ssl_verify,
                timeout=timeout,
            )
        else:
            # a application json post request
            response = requests.post(
                url, data=json.dumps(data), headers=headers, verify=ssl_verify,
                timeout=timeout,
            )
        
        # Log response details before raising for non-OK responses
        if not response.ok:
            error_body = response.text[:500] if response.text else "No response body"
            log.error(
                f"HTTP {response.status_code} from {url}: {error_body}"
            )
        
        response.raise_for_status()
        return response

    except requests.exceptions.HTTPError as e:
        error_body = e.response.text[:500] if e.response and e.response.text else "No response body"
        log.error(
            f"HTTP Error {e.response.status_code if e.response else 'Unknown'} calling {url}: {error_body}"
        )
        return None
    except requests.exceptions.ConnectionError as e:
        log.error(f"Connection Error calling {url}: {str(e)}")
        return None
    except requests.exceptions.Timeout as e:
        log.error(f"Timeout calling {url}: {str(e)}")
        return None
    except Exception as e:
        log.error(f"Unexpected error calling {url}: {type(e).__name__}: {str(e)}")
        return None


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
    timeout = toolkit.config.get(
        "ckanext.csvwmapandtransform.rdfconverter_timeout_check", 30
    )
    r = post_request(url, headers, data, timeout=int(timeout))
    if r and r.status_code == 200:
        res = r.json()
        log.debug("map check results: {}".format(res))
        return res
    else:
        return None


def get_joined_rdf(map_url: str, data_url: str, authorization: None):
    log.info(f"Creating joined RDF with mapping: {map_url} and data: {data_url}")
    rdfconverter_url = toolkit.config.get(
        "ckanext.csvwmapandtransform.rdfconverter_url"
    )
    url = rdfconverter_url + "/api/createrdf?return_type=turtle"
    data = {"mapping_url": map_url, "data_url": data_url}
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    if authorization:
        headers["Authorization"] = authorization
    log.debug(f"Request headers: {list(headers.keys())}")
    log.debug(f"Request data: {data}")

    timeout = toolkit.config.get(
        "ckanext.csvwmapandtransform.rdfconverter_timeout_create", 120
    )
    r = post_request(url, headers, data, timeout=int(timeout))
    
    if r is None:
        log.error(
            f"Failed to get response from RDF converter at {url}. "
            f"Mapping: {map_url}, Data: {data_url}"
        )
        return (None, None, None, None)
    
    if r.status_code == 200:
        try:
            response_json = r.json()
            filename = response_json.get("filename")
            graph = response_json.get("graph")
            num_applied = response_json.get("num_mappings_applied")
            num_skipped = response_json.get("num_mappings_skipped")
            
            if not filename or not graph:
                log.error(
                    f"RDF converter returned incomplete response. "
                    f"Filename: {filename}, Graph present: {bool(graph)}"
                )
                return (None, None, None, None)
            
            log.info(
                f"Successfully created RDF: {filename} "
                f"(applied {num_applied} rules, skipped {num_skipped})"
            )
            return (filename, graph, num_applied, num_skipped)
            
        except (ValueError, KeyError) as e:
            log.error(
                f"Failed to parse RDF converter response: {type(e).__name__}: {str(e)}. "
                f"Response: {r.text[:500]}"
            )
            return (None, None, None, None)
    else:
        error_msg = r.text[:500] if r.text else "No error message"
        log.error(
            f"RDF converter returned status {r.status_code}. "
            f"Mapping: {map_url}, Data: {data_url}. "
            f"Error: {error_msg}"
        )
        return (None, None, None, None)
