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
import psutil
from opentelemetry.sdk.resources import Resource, ProcessResourceDetector
from opentelemetry.semconv.resource import ResourceAttributes

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

# ProcessResourceDetector
class OdigosProcessResourceDetector(ProcessResourceDetector):
    def __init__(self, pid):
        self.pid = pid
        super().__init__()  # Initialize parent class

    def detect(self):
        # Call the parent class's detect method to get the initial resource info
        resource_info = super().detect()

        # Extract attributes as a dictionary (resource_info is a Resource object)
        attributes = dict(resource_info.attributes)
        
        if os.getenv("DISABLE_OPAMP_CLIENT", "false").strip().lower() == "false":
            attributes.pop(ResourceAttributes.PROCESS_PID, None)  # Remove PROCESS_PID if exists
            attributes[PROCESS_VPID] = self.pid
            attributes.pop(ResourceAttributes.PROCESS_COMMAND_ARGS, None)  # Remove PROCESS_COMMAND_ARGS if exists

        # This condition handles the case where the Python application is run as a module using:
        #   python -m <module_name>
        # In such cases, Python internally sets up the module execution and `sys.argv[0]` may appear as "-m".
        # This is a rare edge case, but we include this check to attempt to detect and extract the true
        # command-line invocation (including the module name) using psutil for more accurate telemetry data.
        if sys.argv and sys.argv[0] == "-m":
            try:
                p = psutil.Process()
                command_line = p.cmdline()         
                if command_line:
                    attributes[ResourceAttributes.PROCESS_COMMAND] = command_line[0]
                    attributes[ResourceAttributes.PROCESS_COMMAND_LINE] = " ".join(command_line)
            except Exception:
                pass
        # Return a new Resource instance with updated attributes
        return Resource.create(attributes)