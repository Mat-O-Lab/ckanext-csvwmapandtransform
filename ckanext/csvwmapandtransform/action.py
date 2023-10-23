import ckan.plugins as p
from ckan import model
from ckanext.csvwmapandtransform import plugin
import ckan.plugins.toolkit as toolkit
import ckanapi
import itertools

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

def csvwmapandtransform_find_mappings(context, data_dict):
    resource_id=data_dict.get('resource_id',None)
    if not resource_id:
        msg = {'resource_id': ['this field is mandatory.']}
        raise p.toolkit.ValidationError(msg)
    #get all mappings in mapping group
    groups=toolkit.get_action("group_list")({}, {})
    if MAPPING_GROUP in groups:
        mapping_group=toolkit.get_action("group_show")({},{"id": MAPPING_GROUP, "include_datasets": True})
    else:
        mapping_group=create_group(MAPPING_GROUP)
    packages=[ toolkit.get_action("package_show")({},{"id": package['id']}) for package in mapping_group.get('packages',None)]
    resources=list(itertools.chain.from_iterable([ package['resources'] for package in packages]))
    return resources
    

def csvwmapandtransform_transform(context, data_dict):
    pass

def csvwmapandtransform_map(context, data_dict):
    pass

def get_actions():
    actions={
        'csvwmapandtransform_find_mappings': csvwmapandtransform_find_mappings,
        'csvwmapandtransform_transform': csvwmapandtransform_transform,
        'csvwmapandtransform_map': csvwmapandtransform_map
    }
    return actions


def create_group(name):
    local_ckan = ckanapi.LocalCKAN()
    group = local_ckan.action.group_create(name=name)
    return group
