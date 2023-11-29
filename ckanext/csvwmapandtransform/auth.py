from ckan.logic.auth.create import resource_create
from ckan.logic.auth.get import task_status_show

def csvwmapandtransform_transform(context, data_dict):
    return resource_create(context, data_dict)

def csvwmapandtransform_transform_status(context, data_dict):
    return task_status_show(context, data_dict)

def get_auth_functions():
    return {
        "csvwmapandtransform_transform": csvwmapandtransform_transform,
        "csvwmapandtransform_transform_status": csvwmapandtransform_transform_status,
    }
