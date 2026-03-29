# @odigos/opentelemetry-python

Odigos initializer of OpenTelemetry for Python

This package is utilized in the Odigos project to initialize OpenTelemetry components for automatic instrumentation of Python applications.

Note: This package is currently meant to be used in the odigos project with odigos OpAMP server. It cannot be used as a standalone package in arbitrary Python applications.


## Local development of `odigos-opentelemetry-python`
requirements:

uv - `curl -LsSf https://astral.sh/uv/0.11.2/install.sh | sh`

Local developement mimics the flow in which instrumentations reach their uses (e.g. odiglet):
instrumentation wheel uploads to pypi -> odigos python instrumentation bundle releases version -> odiglet.

Instead of doing all that, use:
```
make build-release-docker
```
This releases a local version of the instrumentation and bundle, versioned as version `local`.

## Using the custom package.

### Building odiglet with custom python agent
In order to build an odiglet image with this custom code the following change should be made (Different for OSS and enterprise)
#### OSS/Enterprise
Update the python agent dependency with a reference to a local image (with "local" version). For example:

Change 
```
COPY --from=public.ecr.aws/odigos/agents/python-community:v1.0.66 /python-instrumentation/workspace /instrumentations/python
```
to
```
COPY --from=public.ecr.aws/odigos/agents/python-community:local /python-instrumentation/workspace /instrumentations/python
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


## Adding a new instrumentation to overload
1. Copy the source code of the new instrumentation to overload into the `instrumentations` dir.
2. In the instrumentation's `pyproject.toml` file, add the `odigos-` prefix to the name.
3. Update the `dependencies` in `pyproject.toml` to use the `odigos-*` for the relevant instrumentation.
4. Push your changed and push a new tag :)
