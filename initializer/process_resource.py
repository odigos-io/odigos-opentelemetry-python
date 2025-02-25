# Copyright The OpenTelemetry Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This package implements `OpenTelemetry Resources
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/resource/sdk.md#resource-sdk>`_:

    *A Resource is an immutable representation of the entity producing
    telemetry. For example, a process producing telemetry that is running in
    a container on Kubernetes has a Pod name, it is in a namespace and
    possibly is part of a Deployment which also has a name. All three of
    these attributes can be included in the Resource.*

Resource objects are created with `Resource.create`, which accepts attributes
(key-values). Resources should NOT be created via constructor except by `ResourceDetector`
instances which can't use `Resource.create` to avoid infinite loops. Working with
`Resource` objects should only be done via the Resource API methods. Resource
attributes can also be passed at process invocation in the
:envvar:`OTEL_RESOURCE_ATTRIBUTES` environment variable. You should register
your resource with the  `opentelemetry.sdk.trace.TracerProvider` by passing
them into their constructors. The `Resource` passed to a provider is available
to the exporter, which can send on this information as it sees fit.

.. code-block:: python

    trace.set_tracer_provider(
        TracerProvider(
            resource=Resource.create({
                "service.name": "shoppingcart",
                "service.instance.id": "instance-12",
            }),
        ),
    )
    print(trace.get_tracer_provider().resource.attributes)

    {'telemetry.sdk.language': 'python',
    'telemetry.sdk.name': 'opentelemetry',
    'telemetry.sdk.version': '0.13.dev0',
    'service.name': 'shoppingcart',
    'service.instance.id': 'instance-12'}

Note that the OpenTelemetry project documents certain `"standard attributes"
<https://github.com/open-telemetry/opentelemetry-specification/blob/main/specification/resource/semantic_conventions/README.md>`_
that have prescribed semantic meanings, for example ``service.name`` in the
above example.
"""

import os
import sys
from types import ModuleType
from typing import Optional
from opentelemetry.sdk.resources import Resource, ResourceDetector
from opentelemetry.semconv.resource import ResourceAttributes
psutil: Optional[ModuleType] = None

try:
    import psutil as psutil_module

    psutil = psutil_module
except ImportError:
    pass

CLOUD_PROVIDER = ResourceAttributes.CLOUD_PROVIDER
CLOUD_ACCOUNT_ID = ResourceAttributes.CLOUD_ACCOUNT_ID
CLOUD_REGION = ResourceAttributes.CLOUD_REGION
CLOUD_AVAILABILITY_ZONE = ResourceAttributes.CLOUD_AVAILABILITY_ZONE
CONTAINER_NAME = ResourceAttributes.CONTAINER_NAME
CONTAINER_ID = ResourceAttributes.CONTAINER_ID
CONTAINER_IMAGE_NAME = ResourceAttributes.CONTAINER_IMAGE_NAME
CONTAINER_IMAGE_TAG = ResourceAttributes.CONTAINER_IMAGE_TAG
DEPLOYMENT_ENVIRONMENT = ResourceAttributes.DEPLOYMENT_ENVIRONMENT
FAAS_NAME = ResourceAttributes.FAAS_NAME
FAAS_ID = ResourceAttributes.FAAS_ID
FAAS_VERSION = ResourceAttributes.FAAS_VERSION
FAAS_INSTANCE = ResourceAttributes.FAAS_INSTANCE
HOST_NAME = ResourceAttributes.HOST_NAME
HOST_ARCH = ResourceAttributes.HOST_ARCH
HOST_TYPE = ResourceAttributes.HOST_TYPE
HOST_IMAGE_NAME = ResourceAttributes.HOST_IMAGE_NAME
HOST_IMAGE_ID = ResourceAttributes.HOST_IMAGE_ID
HOST_IMAGE_VERSION = ResourceAttributes.HOST_IMAGE_VERSION
KUBERNETES_CLUSTER_NAME = ResourceAttributes.K8S_CLUSTER_NAME
KUBERNETES_NAMESPACE_NAME = ResourceAttributes.K8S_NAMESPACE_NAME
KUBERNETES_POD_UID = ResourceAttributes.K8S_POD_UID
KUBERNETES_POD_NAME = ResourceAttributes.K8S_POD_NAME
KUBERNETES_CONTAINER_NAME = ResourceAttributes.K8S_CONTAINER_NAME
KUBERNETES_REPLICA_SET_UID = ResourceAttributes.K8S_REPLICASET_UID
KUBERNETES_REPLICA_SET_NAME = ResourceAttributes.K8S_REPLICASET_NAME
KUBERNETES_DEPLOYMENT_UID = ResourceAttributes.K8S_DEPLOYMENT_UID
KUBERNETES_DEPLOYMENT_NAME = ResourceAttributes.K8S_DEPLOYMENT_NAME
KUBERNETES_STATEFUL_SET_UID = ResourceAttributes.K8S_STATEFULSET_UID
KUBERNETES_STATEFUL_SET_NAME = ResourceAttributes.K8S_STATEFULSET_NAME
KUBERNETES_DAEMON_SET_UID = ResourceAttributes.K8S_DAEMONSET_UID
KUBERNETES_DAEMON_SET_NAME = ResourceAttributes.K8S_DAEMONSET_NAME
KUBERNETES_JOB_UID = ResourceAttributes.K8S_JOB_UID
KUBERNETES_JOB_NAME = ResourceAttributes.K8S_JOB_NAME
KUBERNETES_CRON_JOB_UID = ResourceAttributes.K8S_CRONJOB_UID
KUBERNETES_CRON_JOB_NAME = ResourceAttributes.K8S_CRONJOB_NAME
OS_DESCRIPTION = ResourceAttributes.OS_DESCRIPTION
OS_TYPE = ResourceAttributes.OS_TYPE
OS_VERSION = ResourceAttributes.OS_VERSION
PROCESS_VPID = "process.vpid"
PROCESS_PARENT_PID = ResourceAttributes.PROCESS_PARENT_PID
PROCESS_EXECUTABLE_NAME = ResourceAttributes.PROCESS_EXECUTABLE_NAME
PROCESS_EXECUTABLE_PATH = ResourceAttributes.PROCESS_EXECUTABLE_PATH
PROCESS_COMMAND = ResourceAttributes.PROCESS_COMMAND
PROCESS_COMMAND_LINE = ResourceAttributes.PROCESS_COMMAND_LINE
PROCESS_COMMAND_ARGS = ResourceAttributes.PROCESS_COMMAND_ARGS
PROCESS_OWNER = ResourceAttributes.PROCESS_OWNER
PROCESS_RUNTIME_NAME = ResourceAttributes.PROCESS_RUNTIME_NAME
PROCESS_RUNTIME_VERSION = ResourceAttributes.PROCESS_RUNTIME_VERSION
PROCESS_RUNTIME_DESCRIPTION = ResourceAttributes.PROCESS_RUNTIME_DESCRIPTION
SERVICE_NAME = ResourceAttributes.SERVICE_NAME
SERVICE_NAMESPACE = ResourceAttributes.SERVICE_NAMESPACE
SERVICE_INSTANCE_ID = ResourceAttributes.SERVICE_INSTANCE_ID
SERVICE_VERSION = ResourceAttributes.SERVICE_VERSION
TELEMETRY_SDK_NAME = ResourceAttributes.TELEMETRY_SDK_NAME
TELEMETRY_SDK_VERSION = ResourceAttributes.TELEMETRY_SDK_VERSION
TELEMETRY_AUTO_VERSION = ResourceAttributes.TELEMETRY_AUTO_VERSION
TELEMETRY_SDK_LANGUAGE = ResourceAttributes.TELEMETRY_SDK_LANGUAGE

class ProcessResourceDetector(ResourceDetector):
    # pylint: disable=no-self-use
    def detect(self) -> "Resource":
        _runtime_version = ".".join(
            map(
                str,
                (
                    sys.version_info[:3]
                    if sys.version_info.releaselevel == "final"
                    and not sys.version_info.serial
                    else sys.version_info
                ),
            )
        )
        _process_vpid = os.getpid()
        _process_executable_name = sys.executable
        _process_executable_path = os.path.dirname(_process_executable_name)
        _process_command = sys.argv[0]
        _process_command_line = " ".join(sys.argv)
        _process_command_args = sys.argv
        resource_info = {
            PROCESS_RUNTIME_DESCRIPTION: sys.version,
            PROCESS_RUNTIME_NAME: sys.implementation.name,
            PROCESS_RUNTIME_VERSION: _runtime_version,
            PROCESS_VPID: _process_vpid,
            PROCESS_EXECUTABLE_NAME: _process_executable_name,
            PROCESS_EXECUTABLE_PATH: _process_executable_path,
            PROCESS_COMMAND: _process_command,
            PROCESS_COMMAND_LINE: _process_command_line,
            PROCESS_COMMAND_ARGS: _process_command_args,
        }
        if hasattr(os, "getppid"):
            # pypy3 does not have getppid()
            resource_info[PROCESS_PARENT_PID] = os.getppid()

        if psutil is not None:
            process: psutil_module.Process = psutil.Process()
            username = process.username()
            resource_info[PROCESS_OWNER] = username

        return Resource(resource_info)  # type: ignore
