import datetime
import json
import logging
import sys
import tempfile
from urllib.parse import urlsplit

import ckanapi
import ckanapi.datapackage
import ckanapi.errors
import requests
from ckan import model
from ckan.plugins.toolkit import asbool, config, get_action
from rq import get_current_job
from werkzeug.datastructures import FileStorage as FlaskFileStorage

from ckanext.csvwmapandtransform import db, mapper

log = logging.getLogger(__name__)

CHUNK_INSERT_ROWS = 250


def transform(
    res_url, res_id, dataset_id, callback_url, last_updated, skip_if_no_changes=True
):
    tomap_res = get_action("resource_show")({"ignore_auth": True}, {"id": res_id})
    context = {"session": model.meta.create_local_session(), "ignore_auth": True}
    metadata = {
        "ckan_url": config.get("ckan.site_url"),
        "resource_id": res_id,
        "task_created": last_updated,
        "original_url": res_url,
    }
    token = config.get("ckanext.csvwmapandtransform.ckan_token")
    job_info = dict()
    job_dict = dict(metadata=metadata, status="running", job_info=job_info)
    job_id = get_current_job().id
    errored = False
    error_message = None
    db.init()

    # Set-up logging to the db
    handler = StoringHandler(job_id, job_dict)
    level = logging.DEBUG
    handler.setLevel(level)
    logger = logging.getLogger(job_id)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    # also show logs on stderr
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)

    job_start = datetime.datetime.utcnow()

    callback_csvwmapandtransform_hook(callback_url, api_key=token, job_dict=job_dict)
    logger.info("Job started: transform for resource {}".format(res_id))
    logger.info("Trying to find fitting mapping for: <a href='{url}' target='_blank'>{name}</a>".format(
        url=tomap_res["url"], name=tomap_res["url"].split("/")[-1]
    ))

    mappings = get_action("csvwmapandtransform_find_mappings")({}, {})
    mapping_urls = [res["url"] for res in mappings]
    logger.info("Mappings found: {} YAML resources".format(len(mapping_urls)))

    tested_ok = 0
    tested_failed = 0
    res = []
    for map_url in mapping_urls:
        result = mapper.check_mapping(
            map_url=map_url,
            data_url=tomap_res["url"],
            authorization=token,
        )
        if result is None:
            logger.warning(
                "check_mapping failed for {} — skipped".format(map_url.split("/")[-1])
            )
            tested_failed += 1
        else:
            tested_ok += 1
        res.append({"mapping": map_url, "test": result})

    logger.info(
        "Tested {}: {} ok, {} failed".format(len(mapping_urls), tested_ok, tested_failed)
    )

    # remove None resulting test Items
    valid_items = [item for item in res if item["test"]]
    for item in valid_items:
        item["rating"] = (
            item["test"].get("rules_applicable", 0) - item["test"].get("rules_skipped", 0)
        )
    # sort by rating descending
    sorted_list = sorted(valid_items, key=lambda x: x["rating"], reverse=True)
    rated_summary = [
        {
            "url": m["mapping"],
            "name": m["mapping"].split("/")[-1],
            "rating": m["rating"],
            "skipped": m["test"].get("rules_skipped", 0),
        }
        for m in sorted_list
    ]
    if rated_summary:
        TOP_N = 10
        shown = rated_summary[:TOP_N]
        rest = len(rated_summary) - TOP_N
        rows = "".join(
            "<tr><td><a href='{}' target='_blank'>{}</a></td><td>{}</td><td>{}</td></tr>".format(
                m["url"], m["name"], m["rating"], m["skipped"]
            )
            for m in shown
        )
        if rest > 0:
            rows += "<tr><td colspan='3'><em>… and {} more</em></td></tr>".format(rest)
        table = (
            "<strong>Rated mappings ({}):</strong>"
            "<div style='overflow-x:auto'>"
            "<table class='table table-sm table-bordered table-striped'>"
            "<thead><tr><th>Mapping</th><th>Rating</th><th>Skipped</th></tr></thead>"
            "<tbody>{}</tbody></table></div>"
        ).format(len(rated_summary), rows)
        logger.info(table)
    else:
        logger.info("Rated mappings: (none)")
    callback_csvwmapandtransform_hook(callback_url, api_key=token, job_dict=job_dict)

    strategy = config.get("ckanext.csvwmapandtransform.mapping_strategy", "exact")
    if strategy == "exact":
        candidates = [
            item
            for item in sorted_list
            if item["test"].get("rules_skipped", 0) == 0
            and item["test"].get("rules_applicable", 0) > 0
        ]
    elif strategy == "best_match":
        candidates = [item for item in sorted_list if item["rating"] > 0]
    else:
        logger.warning(
            "Unknown mapping_strategy '{}', falling back to 'exact'.".format(strategy)
        )
        candidates = [
            item
            for item in sorted_list
            if item["test"].get("rules_skipped", 0) == 0
            and item["test"].get("rules_applicable", 0) > 0
        ]
    logger.info(
        "Strategy '{}': {} candidate(s) found.".format(strategy, len(candidates))
    )
    best_condidate = candidates[0]["mapping"] if candidates else None
    if best_condidate:
        winner_name = best_condidate.split("/")[-1]
        winner_rating = candidates[0]["rating"]
        logger.info(
            "Winner: <a href='{url}' target='_blank'>{name}</a> (rating={rating}, strategy={strategy})".format(
                url=best_condidate, name=winner_name, rating=winner_rating, strategy=strategy
            )
        )

    if best_condidate:
        filename, graph_data, num_applied, num_skipped = mapper.get_joined_rdf(
            map_url=best_condidate,
            data_url=tomap_res["url"],
            authorization=token,
        )
        if not filename:
            errored = True
            error_message = "Failed to generate RDF from mapping {} for resource {}".format(
                best_condidate.split("/")[-1], res_id
            )
            logger.error(
                error_message + ". Check previous error messages for details."
            )
        else:
            s = requests.Session()
            s.headers.update({"Authorization": token})
            prefix, suffix = filename.rsplit(".", 1)
            if not prefix:
                prefix = "unnamed"
            if not suffix:
                suffix = "ttl"

            try:
                resource_existing = resource_search(dataset_id, filename)
            except ckanapi.errors.NotFound:
                errored = True
                error_message = "Dataset {} not found when searching for existing resource".format(
                    dataset_id
                )
                logger.error(error_message)
                resource_existing = None

            if not errored:
                with tempfile.NamedTemporaryFile(
                    prefix=prefix, suffix="." + suffix
                ) as graph_file:
                    graph_file.write(graph_data.encode("utf-8"))
                    graph_file.seek(0)
                    tmp_filename = graph_file.name
                    upload = FlaskFileStorage(open(tmp_filename, "rb"), filename)
                    resource = dict(
                        package_id=dataset_id,
                        upload=upload,
                        name=filename,
                        format="text/turtle; charset=utf-8",
                    )
                    try:
                        if not resource_existing:
                            logger.info("Writing new resource <strong>{}</strong> to dataset {}".format(
                                filename, dataset_id
                            ))
                            metadata_res = get_action("resource_create")(
                                {"ignore_auth": True}, resource
                            )
                        else:
                            logger.info(
                                "Updating resource <a href='{url}' target='_blank'>{name}</a>".format(
                                    url=resource_existing["url"],
                                    name=resource_existing["url"].split("/")[-1],
                                )
                            )
                            resource["id"] = resource_existing["id"]
                            metadata_res = get_action("resource_update")(
                                {"ignore_auth": True}, resource
                            )
                        logger.info(
                            "Job completed — results at <a href='{url}' target='_blank'>{name}</a>".format(
                                url=metadata_res["url"],
                                name=metadata_res["url"].split("/")[-1],
                            )
                        )
                    except Exception as e:
                        errored = True
                        error_message = "Failed to write resource {} to dataset {}: {}".format(
                            filename, dataset_id, str(e)
                        )
                        logger.error(error_message)
    else:
        logger.warning(
            "No mapping candidate found for <a href='{url}' target='_blank'>{name}</a>".format(
                url=tomap_res["url"], name=tomap_res["url"].split("/")[-1]
            )
        )

    # all is done — update job status
    duration = (datetime.datetime.utcnow() - job_start).total_seconds()
    logger.info(
        "Job finished in {:.1f}s — status: {}".format(
            duration, "error" if errored else "ok"
        )
    )
    if errored:
        job_dict["status"] = "error"
        job_dict["error"] = error_message
    else:
        job_dict["status"] = "complete"
    callback_csvwmapandtransform_hook(callback_url, api_key=token, job_dict=job_dict)
    return "error" if errored else None


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
    for res in dataset["resources"]:
        if res["name"] == res_name:
            return res
    return None


def callback_csvwmapandtransform_hook(result_url, api_key, job_dict):
    """Tells CKAN about the result of the csvwmapandtransform (i.e. calls the callback
    function 'csvwmapandtransform_hook'). Usually called by the csvwmapandtransform queue job.
    """
    headers = {"Content-Type": "application/json"}
    if api_key:
        if ":" in api_key:
            header, key = api_key.split(":")
        else:
            header, key = "Authorization", api_key
        headers[header] = key
    ssl_verify = asbool(config.get("ckanext.csvwmapandtransform.ssl_verify", True))
    if not ssl_verify:
        requests.packages.urllib3.disable_warnings()
    try:
        result = requests.post(
            result_url,
            data=json.dumps(job_dict, cls=DatetimeJsonEncoder),
            verify=ssl_verify,
            headers=headers,
        )
    except requests.ConnectionError:
        log.warning(
            "Callback to {} failed — CKAN task_status will not be updated".format(
                urlsplit(result_url).path
            )
        )
        return False

    return result.status_code == requests.codes.ok


class StoringHandler(logging.Handler):
    """A handler that stores the logging records in a database."""

    def __init__(self, task_id, input):
        logging.Handler.__init__(self)
        self.task_id = task_id
        self.input = input

    def emit(self, record):
        conn = db.ENGINE.connect()
        try:
            # Turn strings into unicode to stop SQLAlchemy
            # "Unicode type received non-unicode bind param value" warnings.
            message = str(record.getMessage())
            level = str(record.levelname)
            module = str(record.module)
            funcName = str(record.funcName)

            conn.execute(
                db.LOGS_TABLE.insert().values(
                    job_id=self.task_id,
                    timestamp=datetime.datetime.utcnow(),
                    message=message,
                    level=level,
                    module=module,
                    funcName=funcName,
                    lineno=record.lineno,
                )
            )
        except Exception as e:
            sys.stderr.write("StoringHandler DB write failed: {}\n".format(e))
        finally:
            conn.close()


class DatetimeJsonEncoder(json.JSONEncoder):
    # Custom JSON encoder
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)
