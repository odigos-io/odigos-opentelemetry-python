# This file contains code inspired by OpenTelemetry's resource detection mechanisms 
# (https://opentelemetry.io/). It adapts and extends the logic to include additional 
# attributes required for our use case.
#
# OpenTelemetry is licensed under the Apache License, Version 2.0. This adaptation respects 
# the original licensing terms and acknowledges OpenTelemetry as a source of reference.
#
# For OpenTelemetry’s original implementation, see:
# https://github.com/open-telemetry/opentelemetry-python

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

PROCESS_VPID = "process.vpid"

# Custom implementation of ProcessResourceDetector.
# 
# This detector is based on OpenTelemetry's resource detection logic but has been 
# implemented separately because the standard OpenTelemetry detector does not support 
# the "process.vpid" attribute. This attribute is necessary for our use case to track 
# process-specific information that is not covered by OpenTelemetry’s built-in attributes.
#
# By extending the OpenTelemetry approach, we ensure compatibility while adding the 
# additional attribute we require.
class OdigosProcessResourceDetector(ResourceDetector):
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
        _process_id = os.getpid()
        _process_executable_name = sys.executable
        _process_executable_path = os.path.dirname(_process_executable_name)
        _process_command = sys.argv[0]
        _process_command_line = " ".join(sys.argv)
        _process_command_args = sys.argv

        resource_info = {
            ResourceAttributes.PROCESS_RUNTIME_DESCRIPTION: sys.version,
            ResourceAttributes.PROCESS_RUNTIME_NAME: sys.implementation.name,
            ResourceAttributes.PROCESS_RUNTIME_VERSION: _runtime_version,
            ResourceAttributes.PROCESS_EXECUTABLE_NAME: _process_executable_name,
            ResourceAttributes.PROCESS_EXECUTABLE_PATH: _process_executable_path,
            ResourceAttributes.PROCESS_COMMAND: _process_command,
            ResourceAttributes.PROCESS_COMMAND_LINE: _process_command_line,
            ResourceAttributes.PROCESS_COMMAND_ARGS: _process_command_args,
        }

        if os.getenv("DISABLE_OPAMP_CLIENT", "false").strip().lower() == "true":
            resource_info[PROCESS_VPID] = _process_id # No matching OTel attribute
        else:
            resource_info[ResourceAttributes.PROCESS_PID] = _process_id
        
        if hasattr(os, "getppid"):
            resource_info[ResourceAttributes.PROCESS_PARENT_PID] = os.getppid()

        if psutil is not None:
            process: psutil_module.Process = psutil.Process()
            resource_info[ResourceAttributes.PROCESS_OWNER] = process.username()

        return Resource(resource_info)  # type: ignore
