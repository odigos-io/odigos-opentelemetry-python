from enum import Enum

class SamplingOperators(str, Enum):
    EQUALS = "equals"
    NOT_EQUALS = "notEquals"
    END_WITH = "endWith"
    START_WITH = "startWith"