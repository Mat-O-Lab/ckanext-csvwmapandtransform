# encoding: utf-8
"""
ckanext-csvwmapandtransform

A CKAN extension to automate mapping of CSVW metadata documents to knowledge graphs
and run automatic pipelines.
"""

# Expose package version from setuptools-scm
try:
    from importlib.metadata import version, PackageNotFoundError
except ImportError:
    # Python < 3.8 fallback
    from importlib_metadata import version, PackageNotFoundError

try:
    __version__ = version("ckanext-csvwmapandtransform")
except PackageNotFoundError:
    # Package is not installed
    __version__ = "unknown"

__all__ = ["__version__"]
