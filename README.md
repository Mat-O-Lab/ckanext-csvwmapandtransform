[![Tests](https://github.com/Mat-O-Lab/ckanext-csvwmapandtransform/actions/workflows/test.yml/badge.svg)](https://github.com/Mat-O-Lab/ckanext-csvwmapandtransform/actions/workflows/test.yml)

# ckanext-csvwmapandtransform

Extension automatically generating csvw metadata for uploaded textual tabular data. It uploads the data of the first table documented into a datastore for the source csv file.
**should be used as replacement for datapusher**

## Requirements
Needs a running instance of the [MapToMethod Application](https://github.com/Mat-O-Lab/MapToMethod) and [RDFConverter Application](https://github.com/Mat-O-Lab/RDFConverter)
Point at it through env variables.
Also needed is a Api Token for an account with the right privaledges to make the background job work on private datasets and ressources.

```bash
CSVWMAPANDTRANSFORM_TOKEN=${CKAN_API_TOKEN}
MAPTOMETHOD_CONTAINER_NAME="ckan_maptomethod"
MAPTOMETHOD_APP_PORT=5002
# must be reachable from outside container net or iframe wil not work 
CKAN_MAPTOMETHOD_URL=http://<CKAN_HOST>:${MAPTOMETHOD_APP_PORT}
RDFCONVERTER_CONTAINER_NAME="ckan_rdfconverter"
RDFCONVERTER_APP_PORT=5003
CKAN_RDFCONVERTER_URL=http://${RDFCONVERTER_CONTAINER_NAME}:${RDFCONVERTER_APP_PORT}
CSVWMAPANDTRANSFORM_SQLALCHEMY_URL=postgresql://ckandbuser:ckandbpassword@db/ckandb
PARSER_PORT=3001
MAPPER_PORT=4000
CONVERTER_PORT=5000
```

You can set the default formats to run trusformation on by setting the env variable CSVWMAPANDTRANSFORM_FORMATS for example
```bash
CSVWMAPANDTRANSFORM_FORMATS="json-ld turtle n3 nt hext trig longturtle xml"
```
else it will react to the following  formats: "json json-ld turtle n3 nt hext trig longturtle xml"


CSVWMAPANDTRANSFORM_FORMATS="json json-ld turtle n3 nt hext trig longturtle xml"

**TODO:** For example, you might want to mention here which versions of CKAN this
extension works with.

If your extension works across different versions you can add the following table:

Compatibility with core CKAN versions:

| CKAN version    | Compatible?   |
| --------------- | ------------- |
| 2.8 and arlier  | not tested    |
| 2.9             | yes    |
| 2.10            | yes    |

Suggested values:

* "yes"
* "not tested" - I can't think of a reason why it wouldn't work
* "not yet" - there is an intention to get it working
* "no"


## Installation

**TODO:** Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-csvwmapandtransform:

1. Activate your CKAN virtual environment, for example:

     . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

    git clone https://github.com/Mat-O-Lab/ckanext-csvwmapandtransform.git
    cd ckanext-csvwmapandtransform
    pip install -e .
	pip install -r requirements.txt

3. Add `csvwmapandtransform` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

     sudo service apache2 reload


## Config settings

None at present

**TODO:** Document any optional config settings here. For example:

	# The minimum number of hours to wait before re-checking a resource
	# (optional, default: 24).
	ckanext.csvwmapandtransform.some_setting = some_default_value


## Developer installation

To install ckanext-csvwmapandtransform for development, activate your CKAN virtualenv and
do:

    git clone https://github.com/Mat-O-Lab/ckanext-csvwmapandtransform.git
    cd ckanext-csvwmapandtransform
    python setup.py develop
    pip install -r dev-requirements.txt


## Tests

To run the tests, do:

    pytest --ckan-ini=test.ini


## Releasing a new version of ckanext-csvwmapandtransform

If ckanext-csvwmapandtransform should be available on PyPI you can follow these steps to publish a new version:

1. Update the version number in the `setup.py` file. See [PEP 440](http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers) for how to choose version numbers.

2. Make sure you have the latest version of necessary packages:

    pip install --upgrade setuptools wheel twine

3. Create a source and binary distributions of the new version:

       python setup.py sdist bdist_wheel && twine check dist/*

   Fix any errors you get.

4. Upload the source distribution to PyPI:

       twine upload dist/*

5. Commit any outstanding changes:

       git commit -a
       git push

6. Tag the new release of the project on GitHub with the version number from
   the `setup.py` file. For example if the version number in `setup.py` is
   0.0.1 then do:

       git tag 0.0.1
       git push --tags

## License

[AGPL](https://www.gnu.org/licenses/agpl-3.0.en.html)

# Acknowledgments
The authors would like to thank the Federal Government and the Heads of Government of the Länder for their funding and support within the framework of the [Platform Material Digital](https://www.materialdigital.de) consortium. Funded by the German [Federal Ministry of Education and Research (BMBF)](https://www.bmbf.de/bmbf/en/) through the [MaterialDigital](https://www.bmbf.de/SharedDocs/Publikationen/de/bmbf/5/31701_MaterialDigital.pdf?__blob=publicationFile&v=5) Call in Project [KupferDigital](https://www.materialdigital.de/project/1) - project id 13XP5119.

