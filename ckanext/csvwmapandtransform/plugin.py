import re

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.lib.plugins import DefaultTranslation
from ckanext.csvwmapandtransform import action, helpers
import ckanext.csvwmapandtransform.views as views

log = __import__("logging").getLogger(__name__)

DEFAULT_FORMATS = [
    "json",
    "json-ld",
    "turtle",
    "n3",
    "nt",
    "hext",
    "trig",
    "longturtle",
    "xml"
]


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
            "notify: {} {} '{}'".format(operation, type(entity), entity)
        )
        if isinstance(entity, model.Resource):
            log.debug("new uploaded resource")
            dataset = entity.related_packages()[0]
            
            if entity.format in DEFAULT_FORMATS and "-joined" not in entity.url:
                log.debug("plugin notify event for resource: {}".format(entity.id))
                toolkit.get_action('csvwmapandtransform_transform')({"ignore_auth": True},{u'id': entity.id})
                # action.enqueue_find_mapping(
                #     entity.id, entity.name, entity.url, dataset.id, operation
                # )
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

