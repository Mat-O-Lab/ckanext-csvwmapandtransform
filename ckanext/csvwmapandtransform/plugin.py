import re

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.lib.jobs import DEFAULT_QUEUE_NAME
from ckan.lib.plugins import DefaultTranslation
from ckanext.csvwmapandtransform import action, helpers
import ckanext.csvwmapandtransform.views as views

log = __import__("logging").getLogger(__name__)


class CsvwMapAndTransformPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IDomainObjectModification)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.IActions)
    # plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)
    

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("fanstatic", "csvwmapandtransform")

    # IDomainObjectModification

    def notify(self, entity, operation):
        """
        Send a notification on entity modification.

        :param entity: instance of module.Package.
        :param operation: 'new', 'changed' or 'deleted'.
        """
        if operation == "deleted":
            return

        log.debug(
            "notify: {} {} '{}'".format(operation, type(entity).__name__, entity.name)
        )
        if isinstance(entity, model.Resource):
            log.debug("new uploaded resource")
            dataset = entity.related_packages()[0]
            if entity.format == "CSV":
                log.debug("plugin notify event for resource: {}".format(entity.id))
                enqueue_csvw_annotate(
                    entity.id, entity.name, entity.url, dataset.id, operation
                )
        else:
            return

    # ITemplateHelpers

    def get_helpers(self):
        return helpers.get_helpers()

    # IActions

    def get_actions(self):
        actions = action.get_actions()
        return actions
    
    # IBlueprint

    def get_blueprint(self):
        return views.get_blueprint()

def enqueue_csvw_annotate(res_id, res_name, res_url, dataset_id, operation):
    # skip task if the dataset is already queued
    queue = DEFAULT_QUEUE_NAME
    jobs = toolkit.get_action("job_list")({"ignore_auth": True}, {"queues": [queue]})
    log.debug("jobs")
    log.debug(jobs)

    # if jobs:
    #     for job in jobs:
    #         if not job["title"]:
    #             continue
    #         match = re.match(r'CSVtoCSVW \w+ "[^"]*" ([\w-]+)', job["title"])
    #         log.debug("match")
    #         log.debug(match)

    #         if match:
    #             queued_resource_id = match.groups()[0]
    #             if res_id == queued_resource_id:
    #                 log.info("Already queued resource: {} {}".format(res_name, res_id))
    #                 return

    # # add this dataset to the queue
    # log.debug("Queuing job csvw_annotate: {} {}".format(operation, res_name))
    # toolkit.enqueue_job(
    #     annotate_csv,
    #     [res_url, res_id, dataset_id],
    #     title='CSVtoCSVW {} "{}" {}'.format(operation, res_name, res_url),
    #     queue=queue,
    # )
