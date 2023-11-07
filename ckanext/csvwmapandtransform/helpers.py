
# encoding: utf-8

from typing import Any
import ckan.plugins.toolkit as toolkit

def csvwmapandtransform__status_description(status: dict[str, Any]):
    _ = toolkit._

    if status.get('status'):
        captions = {
            'complete': _('Complete'),
            'pending': _('Pending'),
            'submitting': _('Submitting'),
            'error': _('Error'),
        }

        return captions.get(status['status'], status['status'].capitalize())
    else:
        return _('Not Uploaded Yet')

def csvwmapandtransform_show_tools(resource):
    from ckanext.csvwmapandtransform.plugin import DEFAULT_FORMATS
    if resource['format'].lower() in DEFAULT_FORMATS and"-joined" not in resource['url']:
        return True
    else:
        False

def get_helpers():
    return {
        "csvwmapandtransform__status_description": csvwmapandtransform__status_description,
        "csvwmapandtransform_show_tools": csvwmapandtransform_show_tools
    }

