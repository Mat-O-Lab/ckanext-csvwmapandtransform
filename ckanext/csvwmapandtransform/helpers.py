# encoding: utf-8

from typing import Any
import ckan.plugins.toolkit as toolkit
import requests
import re, os


def csvwmapandtransform__status_description(status: dict[str, Any]):
    _ = toolkit._

    if status.get("status"):
        captions = {
            "complete": _("Complete"),
            "pending": _("Pending"),
            "submitting": _("Submitting"),
            "error": _("Error"),
        }

        return captions.get(status["status"], status["status"].capitalize())
    else:
        return _("Not Uploaded Yet")


def common_member(a, b):
    return any(i in b for i in a)


def csvwmapandtransform_show_tools(resource):
    from ckanext.csvwmapandtransform.plugin import DEFAULT_FORMATS

    format_parts = re.split("/|;", resource["format"].lower().replace(" ", ""))
    if common_member(format_parts, DEFAULT_FORMATS):
        return True
    else:
        False


def csvwmapandtransform_service_available():
    extract_url = os.environ.get("CKAN_RDFCONVERTER_URL", "")
    if not extract_url:
        return False  # If EXTRACT_URL is not set, return False
    try:
        # Perform a HEAD request (lightweight check) to see if the service responds
        response = requests.head(extract_url, timeout=5)
        if (200 <= response.status_code < 400) or response.status_code == 405:
            return True  # URL is reachable and returns a valid status code
        else:
            return False  # URL is reachable but response status is not valid
    except requests.RequestException as e:
        # If there's any issue (timeout, connection error, etc.)
        return False


def get_helpers():
    return {
        "csvwmapandtransform__status_description": csvwmapandtransform__status_description,
        "csvwmapandtransform_show_tools": csvwmapandtransform_show_tools,
        "csvwmapandtransform_service_available": csvwmapandtransform_service_available,
    }
