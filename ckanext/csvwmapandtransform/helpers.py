
# encoding: utf-8

from typing import Any
import ckan.plugins.toolkit as toolkit

import re

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

def common_member(a, b):
    return any(i in b for i in a)

def csvwmapandtransform_show_tools(resource):
    from ckanext.csvwmapandtransform.plugin import DEFAULT_FORMATS
    format_parts=re.split('/|;', resource['format'].lower().replace(' ',''))
    if common_member(format_parts,DEFAULT_FORMATS):
        return True
    else:
        False

def get_helpers():
    return {
        "csvwmapandtransform__status_description": csvwmapandtransform__status_description,
        "csvwmapandtransform_show_tools": csvwmapandtransform_show_tools
    }

