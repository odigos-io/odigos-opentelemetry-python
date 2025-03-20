import sys
import importlib
import os

def reorder_python_path():
    # Moves '/var/odigos/' [k8s] and '/etc/odigos-vmagent/' [vmagent] paths to end of sys.path
    # to prioritize user dependencies over odigos ones
    paths_to_move = [path for path in sys.path if path.startswith(('/var/odigos/', '/etc/odigos-vmagent/'))]
    
    for path in paths_to_move:
        sys.path.remove(path)
        sys.path.append(path)
    
    
def reload_distro_modules() -> None:
    # Delete distro modules and their sub-modules, as they have been imported before the path was reordered.
    # The distro modules will be re-imported from the new path.
    needed_module_prefixes = [
        'requests',
        'charset_normalizer',
        'certifi',
        'asgiref',
        'idna',
        'deprecated',
        'importlib_metadata',
        'packaging',
        'psutil',
        'zipp',
        'urllib3',
        'uuid_extensions.uuid7',
        'typing_extensions',
    ]
    
    excluded_modules = [
        'urllib3_odigos',
        'requests_odigos'
    ]
    
    for module in list(sys.modules):
        # Check if the module starts with any of the needed prefixes, but not with any of the excluded prefixes.
        if any(module.startswith(prefix) for prefix in excluded_modules):
            continue
        
        if any(module.startswith(prefix) for prefix in needed_module_prefixes):
            module_file = getattr(sys.modules[module], '__file__', None)  # Safely get __file__
            if module_file and ('/etc/odigos-vmagent/' in module_file or '/var/odigos/' in module_file):
                del sys.modules[module]



### Django

# Disables Django instrumentation if DJANGO_SETTINGS_MODULE is unset and adds the current directory to sys.path for proper Django instrumentation.
# These changes address this issue: https://github.com/open-telemetry/opentelemetry-python-contrib/issues/2495.
# TODO: Remove once the bug is fixed.
def handle_django_instrumentation():
    # Get the DJANGO_SETTINGS_MODULE environment variable value.
    django_settings_module = os.getenv('DJANGO_SETTINGS_MODULE', None)
    
    if django_settings_module is None:
        os.environ.setdefault("OTEL_PYTHON_DJANGO_INSTRUMENT", 'False')
        
    else:
        cwd_path = os.getcwd()
        if cwd_path not in sys.path:
            sys.path.insert(0, cwd_path)    
        
        # As an additional safeguard, we're ensuring that DJANGO_SETTINGS_MODULE is importable.
        # This is done to prevent instrumentation from being enabled if the Django settings module cannot be imported.
        try:
            importlib.import_module(django_settings_module) 
        except:
            os.environ.setdefault("OTEL_PYTHON_DJANGO_INSTRUMENT", 'False')
        

def handle_eventlet_instrumentation():
    """Checks if eventlet is importable and applies eventlet.monkey_patch if available."""
    # Apply monkey_patch early to enable Eventlet's green threads for non-blocking I/O.
    # Per Eventlet docs, it must run before imports or class definitions that use patched modules (e.g., socket).
    # https://eventlet.readthedocs.io/en/v0.35.1/patching.html#monkey-patch
    
    # Currently should run only if no OPAMP client is running, as tested only for the VM agent.
    if os.getenv('DISABLE_OPAMP_CLIENT', 'false').strip().lower() == 'true':
        try:
            eventlet = importlib.import_module("eventlet")
            if not getattr(eventlet, "_opamp_patched", False):  # Avoid multiple patches
                eventlet.monkey_patch()
                eventlet._opamp_patched = True
        except ImportError:
            pass            
            