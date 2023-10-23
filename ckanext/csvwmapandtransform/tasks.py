import json
import os
import tempfile

import ckanapi
import ckanapi.datapackage
import requests
from ckan.plugins.toolkit import get_action
#from ckanext.csvtocsvw.annotate import annotate_csv_upload


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



def annotate_csv(res_url, res_id, dataset_id, skip_if_no_changes=True):
    # url = '{ckan}/dataset/{pkg}/resource/{res_id}/download/{filename}'.format(
    #         ckan=CKAN_URL, pkg=dataset_id, res_id=res_id, filename=res_url)
    csv_res = get_action("resource_show")({"ignore_auth": True}, {"id": res_id})
    log.debug("Annotating: {}".format(csv_res["url"]))
    # need to get it as string, casue url annotation doesnt work with private datasets
    # filename,filedata=annotate_csv_uri(csv_res['url'])

    s = requests.Session()
    s.headers.update({"Authorization": CSVWMAPANDTRANSFORM_TOKEN})
    csv_data = s.get(csv_res["url"]).content
    prefix, suffix = csv_res["url"].rsplit("/", 1)[-1].rsplit(".", 1)
    if not prefix:
        prefix = "unnamed"
    if not suffix:
        suffix = "csv"
    # log.debug(csv_data)
    # with tempfile.NamedTemporaryFile(prefix=prefix, suffix="." + suffix) as csv:
    #     csv.write(csv_data)
    #     csv.seek(0)
    #     csv_name = csv.name
    #     result = annotate_csv_upload(csv.name)
    # meta_data = json.dumps(result["filedata"], indent=2)
    # log.debug("Got result with name: {}".format(result["filename"]))
    # # replace csv url and name
    # csv_name = csv_name.rsplit("/", 1)[-1]
    # dummy_url = "file:///src/{}/".format(csv_name)
    # filename = prefix + "-metadata.json"
    # log.debug("replacing url: {} with {}".format(dummy_url, csv_res["url"]))
    # log.debug("replacing id: {} with {}".format(csv_name, csv_res["name"]))
    # meta_data = meta_data.replace(dummy_url, csv_res["url"] + "/").replace(
    #     csv_name, csv_res["name"]
    # )

    # # Upload resource to CKAN as a new/updated resource
    # # res=get_resource(res_id)
    # metadata_res = resource_search(dataset_id, filename)
    # # log.debug(meta_data)
    # prefix, suffix = filename.rsplit(".", 1)

    # # f = tempfile.NamedTemporaryFile(prefix=prefix,suffix='.'+suffix,delete=False)
    # with tempfile.NamedTemporaryFile(
    #     prefix=prefix, suffix="." + suffix
    # ) as metadata_file:
    #     metadata_file.write(meta_data.encode("utf-8"))
    #     metadata_file.seek(0)
    #     temp_file_name = metadata_file.name
    #     upload = FlaskFileStorage(open(temp_file_name, "rb"), filename)
    #     resource = dict(
    #         package_id=dataset_id,
    #         # url='dummy-value',
    #         upload=upload,
    #         name=filename,
    #         format="json-ld",
    #     )
    #     if not metadata_res:
    #         log.debug("Writing new resource to - {}".format(dataset_id))
    #         # local_ckan.action.resource_create(**resource)
    #         metadata_res = get_action("resource_create")(
    #             {"ignore_auth": True}, resource
    #         )
    #         log.debug(metadata_res)

    #     else:
    #         log.debug("Updating resource - {}".format(metadata_res["id"]))
    #         # local_ckan.action.resource_patch(
    #         #     id=res['id'],
    #         #     **resource)
    #         resource["id"] = metadata_res["id"]
    #         get_action("resource_update")({"ignore_auth": True}, resource)
    # # delete the datastore created from datapusher
    # delete_datastore_resource(csv_res["id"], s)
    # # use csvw metadata to readout the cvs
    # parse = CSVWtoRDF(meta_data, csv_data)
    # # pick table one, can only put one table to datastore
    # table_key = next(iter(parse.tables))
    # table_data = parse.tables[table_key]
    # headers = simple_columns(table_data["columns"])
    # log.debug(headers)

    # column_names = [column["id"] for column in headers]
    # table_records = list()
    # for line in table_data["lines"]:
    #     record = dict()
    #     for i, value in enumerate(line[1:]):
    #         record[column_names[i]] = value
    #     table_records.append(record)
    # # log.debug(table_records[:3])
    # count = 0
    # for i, chunk in enumerate(chunky(table_records, CHUNK_INSERT_ROWS)):
    #     records, is_it_the_last_chunk = chunk
    #     count += len(records)
    #     log.info(
    #         "Saving chunk {number} {is_last}".format(
    #             number=i, is_last="(last)" if is_it_the_last_chunk else ""
    #         )
    #     )
    #     send_resource_to_datastore(
    #         csv_res["id"], headers, records, s, is_it_the_last_chunk
    #     )


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
    