# @odigos/opentelemetry-python

Odigos initializer of OpenTelemetry for Python

This package is utilized in the Odigos project to initialize OpenTelemetry components for automatic instrumentation of Python applications.

Note: This package is currently meant to be used in the odigos project with odigos OpAMP server. It cannot be used as a standalone package in arbitrary Python applications.


## Local development of `odigos-opentelemetry-python`
1. Start the Local PyPI Server:  
Build and run a local PyPI server with the following command:  
```sh
docker build -t local-pypi-server -f debug.Dockerfile . && docker run --rm --name pypi-server -p 8080:8080 local-pypi-server
```
- Note: You need to run the Docker build command each time you make changes to odigos-opentelemetry-python.  

2. Update the Development Configuration:  
The setup.py / requirements.txt should point to the local pypi repo to pull the python package.  
setup.py e.g:  
```
install_requires = [
odigos-opentelemetry-python @ http://localhost:8080/packages/odigos_opentelemetry_python-0.1.1-py3-none-any.whl
...
]
```
requirements.txt e.g:  
```
..
..
odigos-opentelemetry-python @ http://localhost:8080/packages/odigos_opentelemetry_python-0.1.1-py3-none-any.whl
```


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


