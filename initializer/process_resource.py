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
from types import ModuleType
from typing import Optional
from opentelemetry.sdk.resources import Resource, ProcessResourceDetector
from opentelemetry.semconv.resource import ResourceAttributes

psutil: Optional[ModuleType] = None

try:
    import psutil as psutil_module
    psutil = psutil_module
except ImportError:
    pass

PROCESS_VPID = "process.vpid"
_process_id = os.getpid()

# Custom implementation of ProcessResourceDetector.
# 
# This detector is based on OpenTelemetry's resource detection logic but has been 
# implemented separately because the standard OpenTelemetry detector does not support 
# the "process.vpid" attribute. This attribute is necessary for our use case to track 
# process-specific information that is not covered by OpenTelemetry’s built-in attributes.
#
# By extending the OpenTelemetry approach, we ensure compatibility while adding the 
# additional attribute we require.

# ProcessResourceDetector
class OdigosProcessResourceDetector(ProcessResourceDetector):
    def __init__(self):
        super().__init__()  # Initialize parent class

    def detect(self):
        # Call the parent class's detect method to get the initial resource info
        resource_info = super().detect()

        if os.getenv("DISABLE_OPAMP_CLIENT", "false").strip().lower() == "false":
            resource_info.pop(ResourceAttributes.PROCESS_PID, None)  # Remove PROCESS_PID if exists
            resource_info[PROCESS_VPID] = _process_id # No matching OTel attribute


        return Resource(resource_info)
