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

        attributes.pop(ResourceAttributes.PROCESS_COMMAND_ARGS, None)  # Remove PROCESS_COMMAND_ARGS if exists
        
        if os.getenv("DISABLE_OPAMP_CLIENT", "false").strip().lower() == "false":
            attributes.pop(ResourceAttributes.PROCESS_PID, None)  # Remove PROCESS_PID if exists
            attributes[PROCESS_VPID] = self.pid
            
        # Fix for cases where the app is run via `python -m <module>`:
        # sys.argv[0] becomes "-m", which leads to wrong process.command attribute.
        # To get the real command, read from /proc/self/cmdline (Linux only).
        # Falls back silently if reading fails.
        # See: https://github.com/open-telemetry/opentelemetry-python/issues/4518
        process_command = attributes.get(ResourceAttributes.PROCESS_COMMAND, None)
        if process_command is not None and process_command == '-m':
            try:
                with open("/proc/self/cmdline", "rb") as command_file:
                    raw_cmdline = command_file.read()

                if raw_cmdline:
                    command_line = raw_cmdline.decode(errors="ignore").split('\0')
                    if command_line and command_line[0]:
                        attributes[ResourceAttributes.PROCESS_COMMAND] = command_line[0]
                        attributes[ResourceAttributes.PROCESS_COMMAND_LINE] = " ".join(command_line)
            
            # On failure, we retain the default behavior from the base resource detector
            except Exception:
                pass

        # Return a new Resource instance with updated attributes
        return Resource.create(attributes)