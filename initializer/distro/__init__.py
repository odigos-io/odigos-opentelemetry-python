# To ensure user dependencies take precedence over those of the Odigos agent, we need to reorder the Python path accordingly.
# This is crucial because users might rely on different versions of libraries that overlap with those used by the agent. By prioritizing their dependencies, we reduce the risk of introducing compatibility issues or breaking changes in the user's application.
from ..lib_handling import reorder_python_path
reorder_python_path()
