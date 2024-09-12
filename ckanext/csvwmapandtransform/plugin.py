import re, os

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan import model
from ckan.lib.plugins import DefaultTranslation

if toolkit.check_ckan_version("2.10"):
    from ckan.types import Context
else:

    class Context(dict):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)


from typing import Any

from ckanext.csvwmapandtransform import action, helpers, auth, views

log = __import__("logging").getLogger(__name__)

DEFAULT_FORMATS = os.environ.get("CSVWMAPANDTRANSFORM_FORMATS", "").lower().split()
if not DEFAULT_FORMATS:
    DEFAULT_FORMATS = [
        "json",
        "turtle",
        "text/turtle" "n3",
        "nt",
        "hext",
        "trig",
        "longturtle",
        "xml",
        "json-ld",
        "ld+json",
    ]


class CsvwMapAndTransformPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IResourceUrlChange)
    plugins.implements(plugins.IResourceController, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, "templates")
        toolkit.add_public_directory(config_, "public")
        toolkit.add_resource("fanstatic", "csvwmapandtransform")

    # IResourceUrlChange

    def notify(self, resource: model.Resource):
        context: Context = {"ignore_auth": True}
        resource_dict = toolkit.get_action("resource_show")(
            context,
            {
                "id": resource.id,
            },
        )
        self._sumbit_transform(resource_dict)

    # IResourceController

    if not toolkit.check_ckan_version("2.10") or toolkit.check_ckan_version("2.11"):

        def after_create(self, context, resource_dict):
            self.after_resource_create(context, resource_dict)

        # def before_show(self, resource_dict):
        #     self.before_resource_show(resource_dict)

        def after_update(self, context: Context, resource_dict: dict[str, Any]):
            self._sumbit_transform(resource_dict)

    def after_resource_create(self, context: Context, resource_dict: dict[str, Any]):
        self._sumbit_transform(resource_dict)

    def _sumbit_transform(self, resource_dict: dict[str, Any]):
        context = {"model": model, "ignore_auth": True, "defer_commit": True}
        format = resource_dict.get("format", None)
        submit = (
            format
            and format.lower() in DEFAULT_FORMATS
            and "-joined" not in resource_dict["url"]
        )
        log.debug(
            "Submitting resource {0} with format {1}".format(
                resource_dict["id"], format
            )
            + " to csvwmapandtransform_transform"
        )

        if not submit:
            return

        try:
            log.debug(
                "Submitting resource {0}".format(resource_dict["id"])
                + " to csvwmapandtransform_transform"
            )
            toolkit.get_action("csvwmapandtransform_transform")(
                context, {"id": resource_dict["id"]}
            )

        except toolkit.ValidationError as e:
            # If RDFConverter is offline want to catch error instead
            # of raising otherwise resource save will fail with 500
            log.critical(e)
            pass

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

    # IAuthFunctions

    def get_auth_functions(self):
        return auth.get_auth_functions()
