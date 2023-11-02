import json
import os
import tempfile

import ckanapi
import ckanapi.datapackage
import requests
from ckan.plugins.toolkit import get_action
#from ckanext.csvtocsvw.annotate import annotate_csv_upload
from ckanext.csvwmapandtransform import mapper

try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit


log = __import__("logging").getLogger(__name__)

CKAN_URL = os.environ.get("CKAN_SITE_URL", "http://localhost:5000")
CSVWMAPANDTRANSFORM_TOKEN = os.environ.get("CSVWMAPANDTRANSFORM_TOKEN", "")
CHUNK_INSERT_ROWS = 250


from werkzeug.datastructures import FileStorage as FlaskFileStorage


def update_resource_file(resource_id, f):
    context = {
        "ignore_auth": True,
        "user": "",
    }
    upload = cgi.FieldStorage()
    upload.filename = getattr(f, "name", "data")
    upload.file = f
    data = {
        "id": resource_id,
        "url": "will-be-overwritten-automatically",
        "upload": upload,
    }
    return get_action("resource_update")(context, data)



def find_mapping(res_url, res_id, dataset_id, skip_if_no_changes=True):
    # url = '{ckan}/dataset/{pkg}/resource/{res_id}/download/{filename}'.format(
    #         ckan=CKAN_URL, pkg=dataset_id, res_id=res_id, filename=res_url)
    tomap_res = get_action("resource_show")({"ignore_auth": True}, {"id": res_id})
    log.debug("Trying to find fitting mapping for: {}".format(tomap_res["url"]))
    # need to get it as string, casue url annotation doesnt work with private datasets
    # filename,filedata=annotate_csv_uri(csv_res['url'])
    mappings=get_action("csvwmapandtransform_find_mappings")({},{})
    log.debug("Found mappings: {}".format(mappings))
    # tests=get_action(u'csvwmapandtransform_test_mappings')(
    #             {}, {
    #                 u'data_url': resource['url'],
    #                 u'map_urls': [res['url'] for res in mapping_resources]
    #             }
    #         )
    log.debug("testing mappings with: {}".format(tomap_res['url']))
    # tests=get_action(u'csvwmapandtransform_test_map
    res=[{'mapping': res,'test': mapper.check_mapping(map_url=res['url'], data_url=tomap_res['url'], authorization=CSVWMAPANDTRANSFORM_TOKEN)} for res in mappings]
    for item in res:
        if item['test']:
            #the more rules can be applied and the more are not skipped the better the mapping
            item['rating']=item['test']['rules_applicable']-item['test']['rules_skipped']
    #sort by rating
    sorted_list = sorted(res, key=lambda x: x['rating'])
    log.debug("Rated mappings: {}".format(sorted_list))
    #best cnadidate is sorted_list[0]
    if sorted_list:
        best_condidate=sorted_list[0]['mapping']['url']
    else:
        best_condidate=None
    #run mapping and join data
    filename, graph_data, num_applied, num_skipped = mapper.get_joined_rdf(map_url= best_condidate,data_url=tomap_res['url'],authorization=CSVWMAPANDTRANSFORM_TOKEN)
    s = requests.Session()
    s.headers.update({"Authorization": CSVWMAPANDTRANSFORM_TOKEN})
    prefix, suffix = filename.rsplit(".", 1)
    if not prefix:
        prefix = "unnamed"
    if not suffix:
        suffix = "ttl"
    # log.debug(csv_data)
    # # Upload resource to CKAN as a new/updated resource
    ressouce_existing = resource_search(dataset_id, filename)
    with tempfile.NamedTemporaryFile(prefix=prefix, suffix="." + suffix) as graph_file:
        graph_file.write(graph_data.encode("utf-8"))
        graph_file.seek(0)
        tmp_filename = graph_file.name
        upload = FlaskFileStorage(open(tmp_filename, "rb"), filename)
        resource = dict(
            package_id=dataset_id,
            # url='dummy-value',
            upload=upload,
            name=filename,
            format="turtle",
        )
        if not ressouce_existing:
            log.debug("Writing new resource to - {}".format(dataset_id))
            # local_ckan.action.resource_create(**resource)
            metadata_res = get_action("resource_create")(
                {"ignore_auth": True}, resource
            )
            log.debug(ressouce_existing)

        else:
            log.debug("Updating resource - {}".format(ressouce_existing["id"]))
            # local_ckan.action.resource_patch(
            #     id=res['id'],
            #     **resource)
            resource["id"] = ressouce_existing["id"]
            get_action("resource_update")({"ignore_auth": True}, resource)

def get_url(action):
    """
    Get url for ckan action
    """
    if not urlsplit(CKAN_URL).scheme:
        ckan_url = "http://" + CKAN_URL.lstrip("/")
    ckan_url = CKAN_URL.rstrip("/")
    return "{ckan_url}/api/3/action/{action}".format(ckan_url=ckan_url, action=action)

def get_resource(id):
    local_ckan = ckanapi.LocalCKAN()
    try:
        res = local_ckan.action.resource_show(id=id)
    except:
        return False
    else:
        return res


def resource_search(dataset_id, res_name):
    local_ckan = ckanapi.LocalCKAN()
    dataset = local_ckan.action.package_show(id=dataset_id)
    log.debug(dataset)
    for res in dataset["resources"]:
        if res["name"] == res_name:
            return res
    return None
