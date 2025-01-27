import json
import os

import ckan.lib.base as base
import ckan.lib.helpers as core_helpers
import ckan.plugins.toolkit as toolkit
import requests
from ckan.common import _
from flask import Blueprint, Request, request
from flask.views import MethodView

from ckanext.csvwmapandtransform.helpers import csvwmapandtransform_service_available

log = __import__("logging").getLogger(__name__)


blueprint = Blueprint("csvwmapandtransform", __name__)


class TransformView(MethodView):
    def post(self, id: str, resource_id: str):
        try:
            toolkit.get_action("csvwmapandtransform_transform")(
                {}, {"resource_id": resource_id}
            )
        except toolkit.ObjectNotFound:
            base.abort(404, "Dataset not found")
        except toolkit.NotAuthorized:
            base.abort(403, _("Not authorized to see this page"))
        except toolkit.ValidationError:
            log.debug(toolkit.ValidationError)

        return core_helpers.redirect_to(
            "csvwmapandtransform.transform", id=id, resource_id=resource_id
        )

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action("package_show")({}, {"id": id})
            resource = toolkit.get_action("resource_show")({}, {"id": resource_id})

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource

            status = toolkit.get_action("csvwmapandtransform_transform_status")(
                {}, {"resource_id": resource_id}
            )
        except toolkit.ObjectNotFound:
            base.abort(404, "Resource not found")
        except toolkit.NotAuthorized:
            base.abort(403, _("Not authorized to see this page"))

        return base.render(
            "csvwmapandtransform/transform.html",
            extra_vars={
                "pkg_dict": pkg_dict,
                "resource": resource,
                "status": status,
                "status_url": toolkit.url_for(
                    "csvwmapandtransform.status",
                    id=id,
                    resource_id=resource_id,
                    qualified=True,
                ),
                "service_status": csvwmapandtransform_service_available(),
                "refresh_rate": 10,
            },
        )


class CreateMapView(MethodView):
    def post(self, id: str, resource_id: str):
        return core_helpers.redirect_to(
            "csvwmapandtransform.map", id=id, resource_id=resource_id
        )

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action("package_show")({}, {"id": id})
            resource = toolkit.get_action("resource_show")({}, {"id": resource_id})

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource
        except toolkit.ObjectNotFound:
            base.abort(404, "Dataset not found")
        except toolkit.NotAuthorized:
            base.abort(403, _("Not authorized to see this page"))
        # iframe_url = toolkit.url_for(
        #     "api.action",
        #     ver=3,
        #     logic_function="csvwmapandtransform_map",
        #     qualified=True
        # )
        # iframe_url='http://docker-dev.iwm.fraunhofer.de:6002/'
        iframe_url = toolkit.url_for(
            "csvwmapandtransform.iframe_maptomethod",
            id=id,
            resource_id=resource_id,
            qualified=True,
        )
        return base.render(
            "csvwmapandtransform/create_mapping.html",
            extra_vars={
                "pkg_dict": pkg_dict,
                "resource": resource,
                "iframe_url": iframe_url,
            },
        )


def iframe_maptomethod(id, resource_id):
    # extra_vars['q'] = q = request.args.get('q', '')
    # if 'data_url' in data_dict:
    #     url = data_dict['data_url']
    headers = {
        "Content-Type": "application/json",
        "Authorization": toolkit.config.get("ckanext.csvwmapandtransform.ckan_token"),
        "Accept": "text/html",
    }
    resource_dict = toolkit.get_action("resource_show")({}, {"id": resource_id})

    # log.debug(request.values)
    data = {
        "data_url": resource_dict["url"],
        "method_url": "https://github.com/Mat-O-Lab/MSEO/raw/main/methods/DIN_EN_ISO_527-3.drawio.ttl",
        "advanced-data_subject_super_class_uris-0": "http://www.w3.org/ns/csvw#Column",
        "advanced-data_subject_super_class_uris-1": "http://www.w3.org/ns/oa#Annotation",
        "advanced-data_mapping_predicate_uri": "http://purl.obolibrary.org/obo/RO_0010002",
        "advanced-method_object_super_class_uris-0": "https://spec.industrialontologies.org/ontology/core/Core/InformationContentEntity",
        "advanced-method_object_super_class_uris-1": "http://purl.obolibrary.org/obo/BFO_0000008",
    }
    ssl_verify = toolkit.config.get("ckanext.csvwmapandtransform.ssl_verify")
    if not ssl_verify:
        requests.packages.urllib3.disable_warnings()
    maptomethod_url = toolkit.config.get("ckanext.csvwmapandtransform.maptomethod_url")
    html = requests.post(
        url=maptomethod_url + "/create_mapper",
        headers=headers,
        data=json.dumps(data),
        verify=ssl_verify,
    )
    # html=requests.post(url="http://docker-dev.iwm.fraunhofer.de:6002"+"/create_mapper", headers=headers, data=json.dumps(data))
    html.raise_for_status()
    result = html.text
    # log.debug("Response from MapToMethod: {}".format(result))
    return result


class StatusView(MethodView):

    def get(self, id: str, resource_id: str):
        pkg_dict = {}
        try:
            pkg_dict = toolkit.get_action("package_show")({}, {"id": id})
            status = toolkit.get_action("csvwmapandtransform_transform_status")(
                {}, {"resource_id": resource_id}
            )
        except toolkit.ObjectNotFound:
            base.abort(404, "Resource not found")
        except toolkit.NotAuthorized:
            base.abort(403, _("Not authorized to see this page"))

        if status and "logs" in status.keys():
            for index, item in enumerate(status["logs"]):
                status["logs"][index]["timestamp"] = (
                    core_helpers.time_ago_from_timestamp(item["timestamp"])
                )
                if item["level"] == "DEBUG":
                    status["logs"][index]["alertlevel"] = "info"
                    status["logs"][index]["icon"] = "bug-slash"
                    status["logs"][index]["class"] = "success"
                elif item["level"] == "INFO":
                    status["logs"][index]["alertlevel"] = "info"
                    status["logs"][index]["icon"] = "check"
                    status["logs"][index]["class"] = "success"
                else:
                    status["logs"][index]["alertlevel"] = "error"
                    status["logs"][index]["icon"] = "exclamation"
                    status["logs"][index]["class"] = "failure"
        return {"pkg_dict": pkg_dict, "status": status}


blueprint.add_url_rule(
    "/dataset/<id>/resource/<resource_id>/transform/status",
    view_func=StatusView.as_view(str("status")),
)

blueprint.add_url_rule(
    "/dataset/<id>/resource/<resource_id>/transform",
    view_func=TransformView.as_view(str("transform")),
)
blueprint.add_url_rule(
    "/dataset/<id>/resource/<resource_id>/map",
    view_func=CreateMapView.as_view(str("map")),
)

blueprint.add_url_rule(
    "/dataset/<id>/resource/<resource_id>/maptomethod", view_func=iframe_maptomethod
)


def get_blueprint():
    return blueprint
