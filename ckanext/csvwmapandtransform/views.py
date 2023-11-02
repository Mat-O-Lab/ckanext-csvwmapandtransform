from flask import Blueprint
from flask.views import MethodView
import ckan.logic as logic
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as core_helpers
import ckan.lib.base as base
from ckanext.csvwmapandtransform import mapper


log = __import__("logging").getLogger(__name__)


blueprint = Blueprint("csvwmapandtransform", __name__)

class TransformView(MethodView):
    def post(self, id: str, resource_id: str):
        try:
            toolkit.get_action(u'csvwmapandtransform_transform')(
                {}, {
                    u'resource_id': resource_id
                }
            )
        except logic.ValidationError:
            log.debug(ValidationError)
            pass

        return core_helpers.redirect_to(
            u'csvwmapandtransform.transform', id=id, resource_id=resource_id
        )
       

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action(u'package_show')({}, {u'id': id})
            resource = toolkit.get_action(u'resource_show'
                                          )({}, {
                                              u'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource

        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _(u'Resource not found'))
        transform_status=toolkit.get_action(u'csvwmapandtransform_transform_status')(
            {}, {
                        u'resource_id': resource_id
                    }
        )
        # try:
        #     transform_status=toolkit.get_action(u'csvwmapandtransform_transform_status')(
        #             {}, {
        #                 u'resource_id': resource_id
        #             }
        #     )
        # except:
        #     transform_status=None
            
    
        return base.render(
            u'csvwmapandtransform/transform.html',
            extra_vars={
                u'pkg_dict': pkg_dict,
                u'resource': resource,
                u'transform_status': transform_status,
            }
        )

class CreateMapView(MethodView):
    def post(self, id: str, resource_id: str):
        try:
            mapping_group=toolkit.get_action(u'csvwmapandtransform_find_mappings')(
                {}, {
                    u'resource_id': resource_id
                }
            )
        except logic.ValidationError:
            mapping_group=None

        return core_helpers.redirect_to(
            u'csvwmapandtransform.map', id=id, resource_id=resource_id
        )

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action(u'package_show')({}, {u'id': id})
            resource = toolkit.get_action(u'resource_show'
                                          )({}, {
                                              u'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource

        except (logic.NotFound, logic.NotAuthorized):
            base.abort(404, _(u'Resource not found'))
        
        return base.render(
            u'csvwmapandtransform/create_mapping.html',
            extra_vars={
                u'pkg_dict': pkg_dict,
                u'resource': resource,
            }
        )

blueprint.add_url_rule(
    u'/dataset/<id>/resource/<resource_id>/transform',
    view_func=TransformView.as_view(str(u'transform'))
)
blueprint.add_url_rule(
    u'/dataset/<id>/resource/<resource_id>/map',
    view_func=CreateMapView.as_view(str(u'map'))
)

def get_blueprint():
    return blueprint
