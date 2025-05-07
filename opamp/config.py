import re
from dataclasses import dataclass, fields, field
from typing import Any, Dict, Type, TypeVar, get_type_hints

T = TypeVar("T")

###             Configuration structs           ###
class DefaultNoneMixin:
    #__getattr__ is only invoked when the normal attribute lookup (__dict__, class attributes, etc.) fails.
    # Prevent raising a ValueError when accessing a non existing key
    # It'll save us multiple try catch blocks in the future
    def __getattr__(self, name: str):
        return None

@dataclass
class CodeAttributes(DefaultNoneMixin):
    column:      bool = False
    file_path:   bool = False
    function:    bool = False
    line_number: bool = False
    namespace:   bool = False
    stack_trace: bool = False

@dataclass
class Config(DefaultNoneMixin):
    code_attributes: CodeAttributes = field(default_factory=CodeAttributes)

###             Helpers             ###

def camel_to_snake(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return s1.lower()

def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
    """
    Instantiate the dataclass `cls` from `data`:
      - Converts JSON camelCase keys to snake_case field names
      - Ignores unknown keys
      - Uses defaults for any missing fields
      - Recurses if a field’s type is itself a dataclass
    """
    hints = get_type_hints(cls)
    field_names = {f.name for f in fields(cls)}
    init_args: Dict[str, Any] = {}
    for raw_key, raw_val in data.items():
        key = camel_to_snake(raw_key)
        if key not in field_names:
            continue

        field_type = hints.get(key)
        # If the field type is another dataclass, recurse
        if hasattr(field_type, "__dataclass_fields__") and isinstance(raw_val, dict):
            init_args[key] = from_dict(field_type, raw_val)
        else:
            init_args[key] = raw_val

    return cls(**init_args)
