import ckan.plugins as p
from ckan import model
from ckan.types import Context
from ckan.lib.jobs import DEFAULT_QUEUE_NAME
from typing import Any
import re
import json

from ckanext.csvwmapandtransform import plugin
from ckanext.csvwmapandtransform import mapper
from ckanext.csvwmapandtransform.tasks import find_mapping

import ckan.logic as logic

import ckan.plugins.toolkit as toolkit
import ckanapi
import itertools
import datetime
from dateutil.parser import parse as parse_date
from dateutil.parser import isoparse as parse_iso_date

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
    res=enqueue_find_mapping(resource['id'], resource['name'], resource['url'], resource['package_id'], operation='changed')
    return res


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

    # task = p.toolkit.get_action('task_status_show')(context, {
    #     'entity_id': res_id,
    #     'task_type': 'csvwmapandtransform',
    #     'key': 'csvwmapandtransform'
    # })
    joblist =  toolkit.get_action("job_list")({"ignore_auth": True}, {})
    joblist =  get_jobs()
    log.debug('jobs queried')

    log.debug(joblist)

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
        'joblist': joblist,
        'status': 'dont have one',
        # 'status': task['state'],
        # # 'job_id': job_id,
        # # 'job_url': url,
        # 'last_updated': task['last_updated'],
        # # 'job_key': job_key,
        # # 'task_info': job_detail,
        # 'error': json.loads(task['error'])
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

def get_jobs():
    local_ckan = ckanapi.LocalCKAN()
    jobs = local_ckan.action.job_list()
    return jobs

def enqueue_find_mapping(res_id, res_name, res_url, dataset_id, operation):
    # skip task if the dataset is already queued
    queue = DEFAULT_QUEUE_NAME
    jobs = toolkit.get_action("job_list")({"ignore_auth": True}, {"queues": [queue]})
    log.debug("test-jobs")
    log.debug(jobs)
    # Check if this resource is already in the process of being xloadered
    task = {
        'entity_id': res_id,
        'entity_type': 'resource',
        'task_type': 'csvwmapandtransform',
        'last_updated': str(datetime.datetime.utcnow()),
        'state': 'submitting',
        'key': 'csvwmapandtransform',
        'value': '{}',
        'error': '{}',
    }
    try:
        existing_task = p.toolkit.get_action('task_status_show')({}, {
            'entity_id': res_id,
            'task_type': 'csvwmapandtransform',
            'key': 'csvwmapandtransform'
        })
        assume_task_stale_after = datetime.timedelta(seconds=3600)
        assume_task_stillborn_after = \
            datetime.timedelta(seconds=int(5))
        if existing_task.get('state') == 'pending':
            # queued_res_ids = [
            #     re.search(r"'resource_id': u?'([^']+)'",
            #               job.description).groups()[0]
            #     for job in get_queue().get_jobs()
            #     if 'xloader_to_datastore' in str(job)  # filter out test_job etc
            # ]
            updated = parse_iso_date(existing_task['last_updated'])
            time_since_last_updated = datetime.datetime.utcnow() - updated
            # if (res_id not in queued_res_ids
            #         and time_since_last_updated > assume_task_stillborn_after):
            #     # it's not on the queue (and if it had just been started then
            #     # its taken too long to update the task_status from pending -
            #     # the first thing it should do in the xloader job).
            #     # Let it be restarted.
            #     log.info('A pending task was found %r, but its not found in '
            #              'the queue %r and is %s hours old',
            #              existing_task['id'], queued_res_ids,
            #              time_since_last_updated)
            # elif time_since_last_updated > assume_task_stale_after:
            if time_since_last_updated > assume_task_stale_after:
                # it's been a while since the job was last updated - it's more
                # likely something went wrong with it and the state wasn't
                # updated than its still in progress. Let it be restarted.
                log.info('A pending task was found %r, but it is only %s hours'
                         ' old', existing_task['id'], time_since_last_updated)
            else:
                log.info('A pending task was found %s for this resource, so '
                         'skipping this duplicate task', existing_task['id'])
                return False

        task['id'] = existing_task['id']
    except p.toolkit.ObjectNotFound:
        pass
    
    p.toolkit.get_action('task_status_update')(
        # {'session': model.meta.create_local_session(), 'ignore_auth': True},
        {'ignore_auth': True},        
        task
    )

    # add this dataset to the queue
    job=toolkit.enqueue_job(
        find_mapping,
        [res_url, res_id, dataset_id],
        title='csvwmapandtransform {} "{}" {}'.format(operation, res_name, res_url),
        queue=queue,
    )
    log.debug("Enqueued job {} to {} resource {}".format(job.id, operation, res_name))

    value = json.dumps({'job_id': job.id})
    task['value'] = value
    task['state'] = 'pending'
    task['last_updated'] = str(datetime.datetime.utcnow())
    p.toolkit.get_action('task_status_update')(
        # {'session': model.meta.create_local_session(), 'ignore_auth': True},
        {'ignore_auth': True},        
        task
    )
    return True