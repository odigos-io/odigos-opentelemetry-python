# @odigos/opentelemetry-python

Odigos initializer of OpenTelemetry for Python

This package is utilized in the Odigos project to initialize OpenTelemetry components for automatic instrumentation of Python applications.

Note: This package is currently meant to be used in the odigos project with odigos OpAMP server. It cannot be used as a standalone package in arbitrary Python applications.


## Local development of `odigos-opentelemetry-python`
In order to debug local changes you can use the `./debug.sh` script

requirements:

1. fswatch - `brew install fswatch`
2. build - `pip install build`

When running the script, it sets an fswatch on the repo and any file changes causes the whole repo to be rebuild and served via the PyPI server

Simply run `./debug.sh`

## Using the custom package.

### Building odiglet with custom python agent
In order to build an odiglet image with this custom code the following change should be made (Different for OSS and enterprise)
#### OSS
Update the python agent setup.py to access the local pypi server
Inside `agents/python/setup.py` Uncomment `# index_url = ....` and make sure it is pointing to the correct version in the pypi

```index_url = 'http://host.docker.internal:8080/packages/odigos_opentelemetry_python-1.0.42-py3-none-any.whl'```

#### Enterprise
Update the python agent requirements.txt with a reference to the local pypi server for example:

Change `odigos-opentelemetry-python==1.0.42` to `odigos-opentelemetry-python @ http://host.docker.internal:8080/packages/odigos_opentelemetry_python-1.0.42-py3-none-any.whl`

## Publishing a New Version to PyPI
1. Ensure all changes are merged into the `main` branch.

2. Create a tag for the new version.
```bash
git tag <TAG>
```
3. Push the tag to the remote repository.
```bash
git push origin <TAG>
```
4. Let the [GitHub workflow](https://github.com/odigos-io/odigos-opentelemetry-python/blob/main/.github/workflows/publish.yaml) handle versioning and publishing to [odigos-opentelemetry-python on PyPI](https://pypi.org/project/odigos-opentelemetry-python/).
