from flask import Blueprint
from flask.views import MethodView
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as core_helpers
import ckan.lib.base as base
from ckanext.csvwmapandtransform import mapper


log = __import__("logging").getLogger(__name__)


blueprint = Blueprint("csvwmapandtransform", __name__)

class TransformView(MethodView):
    def post(self, id: str, resource_id: str):
        try:
            toolkit.get_action('csvwmapandtransform_transform')(
                {}, {
                    'resource_id': resource_id
                }
            )
        except toolkit.ValidationError:
            log.debug(toolkit.ValidationError)
        
        return core_helpers.redirect_to(
            'csvwmapandtransform.transform', id=id, resource_id=resource_id
        )
       

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action('package_show')({}, {'id': id})
            resource = toolkit.get_action('resource_show'
                                          )({}, {
                                              'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource

        except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
            base.abort(404, _('Resource not found'))
        status=toolkit.get_action('csvwmapandtransform_transform_status')(
            {}, {
                        'resource_id': resource_id
                    }
        )
        #status=None 
        # try:
        #     transform_status=toolkit.get_action('csvwmapandtransform_transform_status')(
        #             {}, {
        #                 'resource_id': resource_id
        #             }
        #     )
        # except:
        #     transform_status=None
            
    
        return base.render(
            'csvwmapandtransform/transform.html',
            extra_vars={
                'pkg_dict': pkg_dict,
                'resource': resource,
                'status': status,
            }
        )

class CreateMapView(MethodView):
    def post(self, id: str, resource_id: str):
        try:
            mapping_group=toolkit.get_action('csvwmapandtransform_find_mappings')(
                {}, {
                    'resource_id': resource_id
                }
            )
        except toolkit.ValidationError:
            mapping_group=None

        return core_helpers.redirect_to(
            'csvwmapandtransform.map', id=id, resource_id=resource_id
        )

    def get(self, id: str, resource_id: str):
        try:
            pkg_dict = toolkit.get_action('package_show')({}, {'id': id})
            resource = toolkit.get_action('resource_show'
                                          )({}, {
                                              'id': resource_id
                                          })

            # backward compatibility with old templates
            toolkit.g.pkg_dict = pkg_dict
            toolkit.g.resource = resource

        except (toolkit.ObjectNotFound, toolkit.NotAuthorized):
            base.abort(404, _('Resource not found'))
        
        return base.render(
            'csvwmapandtransform/create_mapping.html',
            extra_vars={
                'pkg_dict': pkg_dict,
                'resource': resource,
            }
        )

blueprint.add_url_rule(
    '/dataset/<id>/resource/<resource_id>/transform',
    view_func=TransformView.as_view(str('transform'))
)
blueprint.add_url_rule(
    '/dataset/<id>/resource/<resource_id>/map',
    view_func=CreateMapView.as_view(str('map'))
)

def get_blueprint():
    return blueprint
