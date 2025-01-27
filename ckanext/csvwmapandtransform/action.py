import ckan.plugins.toolkit as toolkit

if toolkit.check_ckan_version("2.10"):
    from ckan.types import Context
else:

    class Context(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)


import datetime
import itertools
import json
import os
from typing import Any

import ckanapi
import sqlalchemy as sa
from ckan import model
from ckan.lib.jobs import DEFAULT_QUEUE_NAME
from dateutil.parser import isoparse as parse_iso_date
from dateutil.parser import parse as parse_date

from ckanext.csvwmapandtransform import db, mapper
from ckanext.csvwmapandtransform.tasks import transform

log = __import__("logging").getLogger(__name__)
# must be lower case alphanumeric and these symbols: -_
MAPPING_GROUP = "mappings"
METHOD_GROUP = "methods"
JOB_TIMEOUT = 180


def find_first_matching_id(dicts: list, key: str, value: str):
    return next((d["id"] for d in dicts if d.get(key) == value), None)


def csvwmapandtransform_find_mappings(context: Context, data_dict):
    mapping_group_id = find_first_matching_id(
        toolkit.get_action("group_list")({}, {"all_fields": True}),
        key="name",
        value=MAPPING_GROUP,
    )
    if mapping_group_id:
        mapping_group = toolkit.get_action("group_show")(
            {"ignore_auth": True}, {"id": mapping_group_id, "include_datasets": True}
        )
    else:
        log.warn("group with name mappings not found!")
        mapping_group = create_group(MAPPING_GROUP)
        log.info("created group mappings")
    packages = mapping_group.get("packages", None)

    if packages:
        packages = [
            toolkit.get_action("package_show")({}, {"id": package["id"]})
            for package in packages
        ]
        resources = list(
            itertools.chain.from_iterable(
                [package["resources"] for package in packages]
            )
        )
    else:
        resources = list()
    return resources


def csvwmapandtransform_test_mappings(context: Context, data_dict):
    data_url = data_dict.get("data_url", None)
    map_urls = data_dict.get("map_urls", None)
    if not map_urls:
        msg = {"map_urls": ["this field is mandatory."]}
        raise toolkit.ValidationError(msg)
    elif not data_url:
        msg = {"data_url": ["this field is mandatory."]}
        raise toolkit.ValidationError(msg)
    tests = [mapper.check_mapping(map_url=url, data_url=data_url) for url in map_urls]
    return tests


def csvwmapandtransform_transform(
    context: Context, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Start a the transformation job for a certain resource.

    :param resource_id: The resource id of the resource that you want the
        datapusher status for.
    :type resource_id: string
    """
    if "id" in data_dict:
        data_dict["resource_id"] = data_dict["id"]
    res_id = toolkit.get_or_bust(data_dict, "resource_id")
    resource = toolkit.get_action("resource_show")(
        {"ignore_auth": True}, {"id": res_id}
    )
    data_dict["resource"] = resource
    toolkit.check_access("csvwmapandtransform_transform", context, data_dict)

    log.debug("transform_started for: {}".format(resource))
    res = enqueue_transform(
        resource["id"],
        resource["name"],
        resource["url"],
        resource["package_id"],
        operation="changed",
    )
    return res


@toolkit.side_effect_free
def csvwmapandtransform_transform_status(
    context: Context, data_dict: dict[str, Any]
) -> dict[str, Any]:
    """Get the status of a the transformation job for a certain resource.

    :param resource_id: The resource id of the resource that you want the
        datapusher status for.
    :type resource_id: string
    """
    toolkit.check_access("csvwmapandtransform_transform_status", context, data_dict)

    if "id" in data_dict:
        data_dict["resource_id"] = data_dict["id"]
    res_id = toolkit.get_or_bust(data_dict, "resource_id")
    job_id = None

    try:
        task = toolkit.get_action("task_status_show")(
            {},
            {
                "entity_id": res_id,
                "task_type": "csvwmapandtransform",
                "key": "csvwmapandtransform",
            },
        )
    except:
        status = None
    else:
        value = json.loads(task["value"])
        job_id = value.get("job_id")
        url = None
        job_detail = None
        try:
            error = json.loads(task["error"])
        except ValueError:
            # this happens occasionally, such as when the job times out
            error = task["error"]
        status = {
            "status": task["state"],
            "job_id": job_id,
            "job_url": url,
            "last_updated": task["last_updated"],
            "error": error,
        }
    if job_id:
        # get logs from db
        db.init()
        db_job = db.get_job(job_id)

        if db_job and db_job.get("logs"):
            for log in db_job["logs"]:
                if "timestamp" in log and isinstance(
                    log["timestamp"], datetime.datetime
                ):
                    log["timestamp"] = log["timestamp"].isoformat()
        status = dict(status, **db_job)
        # status['task_info']=db_job
    return status


def get_actions():
    actions = {
        "csvwmapandtransform_find_mappings": csvwmapandtransform_find_mappings,
        "csvwmapandtransform_transform": csvwmapandtransform_transform,
        "csvwmapandtransform_test_mappings": csvwmapandtransform_test_mappings,
        "csvwmapandtransform_transform_status": csvwmapandtransform_transform_status,
        "csvwmapandtransform_hook": csvwmapandtransform_hook,
    }
    return actions


def create_group(name):
    local_ckan = ckanapi.LocalCKAN()
    group = local_ckan.action.group_create(name=name)
    return group


def enqueue_transform(res_id, res_name, res_url, dataset_id, operation):
    # skip task if the dataset is already queued
    queue = DEFAULT_QUEUE_NAME
    # jobs = toolkit.get_action("job_list")({"ignore_auth": True}, {"queues": [queue]})
    # log.debug("test-jobs")
    # log.debug(jobs)
    # Check if this resource is already in the process of being xloadered
    task = {
        "entity_id": res_id,
        "entity_type": "resource",
        "task_type": "csvwmapandtransform",
        "last_updated": str(datetime.datetime.utcnow()),
        "state": "submitting",
        "key": "csvwmapandtransform",
        "value": "{}",
        "error": "{}",
        "detail": "",
    }
    try:
        existing_task = toolkit.get_action("task_status_show")(
            {},
            {
                "entity_id": res_id,
                "task_type": "csvwmapandtransform",
                "key": "csvwmapandtransform",
            },
        )
        assume_task_stale_after = datetime.timedelta(seconds=3600)
        assume_task_stillborn_after = datetime.timedelta(seconds=int(5))
        if existing_task.get("state") == "pending":
            # queued_res_ids = [
            #     re.search(r"'resource_id': u?'([^']+)'",
            #               job.description).groups()[0]
            #     for job in get_queue().get_jobs()
            #     if 'xloader_to_datastore' in str(job)  # filter out test_job etc
            # ]
            updated = parse_iso_date(existing_task["last_updated"])
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
                log.info(
                    "A pending task was found %r, but it is only %s hours" " old",
                    existing_task["id"],
                    time_since_last_updated,
                )
            else:
                log.info(
                    "A pending task was found %s for this resource, so "
                    "skipping this duplicate task",
                    existing_task["id"],
                )
                return False

        task["id"] = existing_task["id"]
    except toolkit.ObjectNotFound:
        pass

    callback_url = toolkit.url_for(
        "api.action", ver=3, logic_function="csvwmapandtransform_hook", qualified=True
    )
    # initioalize database for additional job data
    db.init()
    # Store details of the job in the db

    # add this dataset to the queue
    job = toolkit.enqueue_job(
        transform,
        [res_url, res_id, dataset_id, callback_url, task["last_updated"]],
        title='csvwmapandtransform {} "{}" {}'.format(operation, res_name, res_url),
        queue=queue,  # , timeout=JOB_TIMEOUT
    )
    try:
        db.add_pending_job(job.id, job_type=task["task_type"], result_url=callback_url)
    except sa.exc.IntegrityError:
        raise Exception("job_id {} already exists".format(task["id"]))

    # log.info("added a job to csvwmapandtransform database")
    # log.debug("enqueued job id".format(job.id)

    log.debug("Enqueued job {} to {} resource {}".format(job.id, operation, res_name))

    value = json.dumps({"job_id": job.id})
    task["value"] = value
    task["state"] = "pending"
    task["last_updated"] = str(datetime.datetime.utcnow())
    toolkit.get_action("task_status_update")(
        {"session": model.meta.create_local_session(), "ignore_auth": True}, task
    )
    return True


def csvwmapandtransform_hook(context, data_dict):
    """Update csvwmapandtransform task. This action is typically called by ckanext-csvwmapandtransform
    whenever the status of a job changes.

    :param metadata: metadata provided when submitting job. key-value pairs.
                     Must have resource_id property.
    :type metadata: dict
    :param status: status of the job from the csvwmapandtransform service. Allowed values:
                   pending, running, running_but_viewable, complete, error
                   (which must all be valid values for task_status too)
    :type status: string
    :param error: Error raised during job execution
    :type error: string

    NB here are other params which are in the equivalent object in
    ckan-service-provider (from job_status):
        :param sent_data: Input data for job
        :type sent_data: json encodable data
        :param job_id: An identifier for the job
        :type job_id: string
        :param result_url: Callback url
        :type result_url: url string
        :param data: Results from job.
        :type data: json encodable data
        :param requested_timestamp: Time the job started
        :type requested_timestamp: timestamp
        :param finished_timestamp: Time the job finished
        :type finished_timestamp: timestamp

    """

    metadata, status, job_info = toolkit.get_or_bust(
        data_dict, ["metadata", "status", "job_info"]
    )

    res_id = toolkit.get_or_bust(metadata, "resource_id")

    # Pass metadata, not data_dict, as it contains the resource id needed
    # on the auth checks
    # toolkit.check_access('xloader_submit', context, metadata)

    task = toolkit.get_action("task_status_show")(
        context,
        {
            "entity_id": res_id,
            "task_type": "csvwmapandtransform",
            "key": "csvwmapandtransform",
        },
    )

    task["state"] = status
    task["last_updated"] = str(datetime.datetime.utcnow())
    task["error"] = data_dict.get("error")
    # task['task_info'] = job_info
    resubmit = False

    if status in ("complete", "running_but_viewable"):
        # Create default views for resource if necessary (only the ones that
        # require data to be in the DataStore)
        resource_dict = toolkit.get_action("resource_show")(context, {"id": res_id})

        dataset_dict = toolkit.get_action("package_show")(
            context, {"id": resource_dict["package_id"]}
        )

        # Check if the uploaded file has been modified in the meantime
        if resource_dict.get("last_modified") and metadata.get("task_created"):
            try:
                last_modified_datetime = parse_date(resource_dict["last_modified"])
                task_created_datetime = parse_date(metadata["task_created"])
                if last_modified_datetime > task_created_datetime:
                    log.debug(
                        "Uploaded file more recent: %s > %s",
                        last_modified_datetime,
                        task_created_datetime,
                    )
                    resubmit = True
            except ValueError:
                pass
        # Check if the URL of the file has been modified in the meantime
        elif (
            resource_dict.get("url")
            and metadata.get("original_url")
            and resource_dict["url"] != metadata["original_url"]
        ):
            log.debug(
                "URLs are different: %s != %s",
                resource_dict["url"],
                metadata["original_url"],
            )
            resubmit = True
        # mark job completed in db
        log.debug(task)
        log.debug(job_info)

        if status == "complete":
            log.debug("job complete now update job db at: {}".format(task))
            db.init()
            job_id = json.loads(task["value"])["job_id"]
            db.mark_job_as_completed(job_id)

    context["ignore_auth"] = True
    toolkit.get_action("task_status_update")(context, task)

    if resubmit:
        log.debug(
            "Resource %s has been modified, " "resubmitting to csvwmapandtransform",
            res_id,
        )
        toolkit.get_action("csvwmapandtransform_transform")(
            context, {"resource_id": res_id}
        )
