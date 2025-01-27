from ckan.logic.auth.get import task_status_show

import ckanext.datastore.logic.auth as auth


def csvwmapandtransform_transform(context, data_dict):
    if "resource" in data_dict and data_dict["resource"].get("package_id"):
        data_dict["id"] = data_dict["resource"].get("package_id")
        privilege = "package_update"
    else:
        privilege = "resource_update"
    return auth.datastore_auth(context, data_dict, privilege=privilege)


def csvwmapandtransform_transform_status(context, data_dict):
    return task_status_show(context, data_dict)


def get_auth_functions():
    return {
        "csvwmapandtransform_transform": csvwmapandtransform_transform,
        "csvwmapandtransform_transform_status": csvwmapandtransform_transform_status,
    }
