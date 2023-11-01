import ckan.plugins as p
from ckan import model
from ckan.types import Context
from ckan.lib.jobs import DEFAULT_QUEUE_NAME
from typing import Any
import re

from ckanext.csvwmapandtransform import plugin
from ckanext.csvwmapandtransform import mapper
from ckanext.csvwmapandtransform.tasks import find_mapping

import ckan.logic as logic

import ckan.plugins.toolkit as toolkit
import ckanapi
import itertools

_get_or_bust = logic.get_or_bust

log = __import__("logging").getLogger(__name__)
#must be lower case alphanumeric and these symbols: -_
MAPPING_GROUP = "mappings"
METHOD_GROUP = "methods"


# @p.toolkit.chained_action  # requires CKAN 2.7+
# def datastore_create(original_action, context, data_dict):
#     #     # This gets called when xloader or datapusher loads a new resource or
#     #     # data dictionary is changed. We need to regenerate the zip when the latter
#     #     # happens, and it's ok if it happens at the other times too.
#     result = original_action(context, data_dict)
#     #     if 'resource_id' in data_dict:
#     #         res = model.Resource.get(data_dict['resource_id'])
#     #         #datapusher finished if True
#     #         datapush_finished=result.get('calculate_record_count',False)
#     #         if res and ('CSV' in res.format) and datapush_finished:
#     #             dataset = res.related_packages()[0]
#     #             log.debug('chained_action: enquery annotation job')
#     #             #plugin.enqueue_csvw_annotate(res.id, res.name, res.url, dataset.id, 'datastore_create')
#     return result

def csvwmapandtransform_find_mappings(context: Context, data_dict):
    # resource_id=data_dict.get('resource_id',None)
    # if not resource_id:
    #     msg = {'resource_id': ['this field is mandatory.']}
    #     raise p.toolkit.ValidationError(msg)
    # #get all mappings in mapping group
    groups=toolkit.get_action("group_list")({}, {})
    if MAPPING_GROUP in groups:
        mapping_group=toolkit.get_action("group_show")({},{"id": MAPPING_GROUP, "include_datasets": True})
    else:
        mapping_group=create_group(MAPPING_GROUP)
    packages=[ toolkit.get_action("package_show")({},{"id": package['id']}) for package in mapping_group.get('packages',None)]
    resources=list(itertools.chain.from_iterable([ package['resources'] for package in packages]))
    return resources


def csvwmapandtransform_test_mappings(context: Context, data_dict):
    data_url=data_dict.get('data_url',None)
    map_urls=data_dict.get('map_urls',None)
    if not map_urls:
        msg = {'map_urls': ['this field is mandatory.']}
        raise p.toolkit.ValidationError(msg)
    elif not data_url:
        msg = {'data_url': ['this field is mandatory.']}
        raise p.toolkit.ValidationError(msg)
    tests=[mapper.check_mapping(map_url=url, data_url=data_url) for url in map_urls]
    return tests


def csvwmapandtransform_transform(
    context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    ''' Start a the transformation job for a certain resource.

    :param resource_id: The resource id of the resource that you want the
        datapusher status for.
    :type resource_id: string
    '''

    #p.toolkit.check_access('csvwmapandtransform_transform_status', context, data_dict)

    if 'id' in data_dict:
        data_dict['resource_id'] = data_dict['id']
    res_id = _get_or_bust(data_dict, 'resource_id')
    resource = toolkit.get_action(u'resource_show'
                                          )({}, {
                                              u'id': res_id
                                          })
    log.debug('transform_started for: {}'.format(resource))
    enqueue_find_mapping(resource['id'], resource['name'], resource['url'], resource['package_id'], operation='changed')
    return {}


def csvwmapandtransform_map(context, data_dict):
    pass


def csvwmapandtransform_transform_status(
        context: Context, data_dict: dict[str, Any]) -> dict[str, Any]:
    ''' Get the status of a the transformation job for a certain resource.

    :param resource_id: The resource id of the resource that you want the
        datapusher status for.
    :type resource_id: string
    '''

    #p.toolkit.check_access('csvwmapandtransform_transform_status', context, data_dict)

    if 'id' in data_dict:
        data_dict['resource_id'] = data_dict['id']
    res_id = _get_or_bust(data_dict, 'resource_id')

    task = p.toolkit.get_action('task_status_show')(context, {
        'entity_id': res_id,
        'task_type': 'csvwmapandtransform',
        'key': 'csvwmapandtransform'
    })

    # datapusher_url = config.get('ckan.datapusher.url')
    # if not datapusher_url:
    #     raise p.toolkit.ValidationError(
    #         {'configuration': ['ckan.datapusher.url not in config file']})

    # value = json.loads(task['value'])
    # job_key = value.get('job_key')
    # job_id = value.get('job_id')
    # url = None
    # job_detail = None

    # if job_id:
    #     url = urljoin(datapusher_url, 'job' + '/' + job_id)
    #     try:
    #         timeout = config.get('ckan.requests.timeout')
    #         r = requests.get(url,
    #                          timeout=timeout,
    #                          headers={'Content-Type': 'application/json',
    #                                   'Authorization': job_key})
    #         r.raise_for_status()
    #         job_detail = r.json()
    #         for log in job_detail['logs']:
    #             if 'timestamp' in log:
    #                 date = time.strptime(
    #                     log['timestamp'], "%Y-%m-%dT%H:%M:%S.%f")
    #                 date = datetime.datetime.utcfromtimestamp(
    #                     time.mktime(date))
    #                 log['timestamp'] = date
    #     except (requests.exceptions.ConnectionError,
    #             requests.exceptions.HTTPError):
    #         job_detail = {'error': 'cannot connect to datapusher'}

    return {
        'status': task['state'],
        # 'job_id': job_id,
        # 'job_url': url,
        'last_updated': task['last_updated'],
        # 'job_key': job_key,
        # 'task_info': job_detail,
        'error': json.loads(task['error'])
    }

def get_actions():
    actions={
        'csvwmapandtransform_find_mappings': csvwmapandtransform_find_mappings,
        'csvwmapandtransform_transform': csvwmapandtransform_transform,
        'csvwmapandtransform_map': csvwmapandtransform_map,
        'csvwmapandtransform_test_mappings': csvwmapandtransform_test_mappings,
        'csvwmapandtransform_transform_status': csvwmapandtransform_transform_status
    }
    return actions


def create_group(name):
    local_ckan = ckanapi.LocalCKAN()
    group = local_ckan.action.group_create(name=name)
    return group

def enqueue_find_mapping(res_id, res_name, res_url, dataset_id, operation):
    # skip task if the dataset is already queued
    queue = DEFAULT_QUEUE_NAME
    jobs = toolkit.get_action("job_list")({"ignore_auth": True}, {"queues": [queue]})
    log.debug("jobs")
    log.debug(jobs)

    if jobs:
        for job in jobs:
            if not job["title"]:
                continue
            match = re.match(r'csvwmapandtransform \w+ "[^"]*" ([\w-]+)', job["title"])
            log.debug("match")
            log.debug(match)

            if match:
                queued_resource_id = match.groups()[0]
                if res_id == queued_resource_id:
                    log.info("Already queued resource: {} {}".format(res_name, res_id))
                    return

    # add this dataset to the queue
    log.debug("Queuing job find_mapping: {} {}".format(operation, res_name))
    toolkit.enqueue_job(
        find_mapping,
        [res_url, res_id, dataset_id],
        title='csvwmapandtransform {} "{}" {}'.format(operation, res_name, res_url),
        queue=queue,
    )
