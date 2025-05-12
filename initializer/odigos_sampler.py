from .sampling_operators import SamplingOperators
from opentelemetry.sdk.trace.sampling import Sampler, Decision, SamplingResult, _get_parent_trace_state
from threading import Lock
import logging

# Setup the Sampler logger
sampler_logger = logging.getLogger('odigos')

class OdigosSampler(Sampler):

    # Define the sampling operator functions used in the configuration.
    # These operations are specified in the Odigos InstrumentationConfig Kubernetes object.
    _operations = {
        SamplingOperators.EQUALS.value: lambda attr, value: attr == value,
        SamplingOperators.NOT_EQUALS.value: lambda attr, value: attr != value,
        SamplingOperators.END_WITH.value: lambda attr, value: attr.endswith(value),
        SamplingOperators.START_WITH.value: lambda attr, value: attr.startswith(value)
    }

    # For compatibility with 64 bit trace IDs, the sampler checks the 64
    # low-order bits of the trace ID to decide whether to sample a given trace.
    TRACE_ID_LIMIT = (1 << 64) - 1

    def __init__(self):
        self._lock = Lock()
        self._config = None

    def _trace_id_based_sampling(self, trace_id, fraction):
        """Mimic OpenTelemetry's trace ID-based sampling logic with 64-bit range."""
        # Calculate the bound based on the fraction using OpenTelemetry's approach
        bound = round(fraction * (self.TRACE_ID_LIMIT + 1))
        # Apply the TRACE_ID_LIMIT mask to ensure 64-bit range and compare it to the bound
        return (trace_id & self.TRACE_ID_LIMIT) < bound

    def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
        with self._lock:
            # sampler_logger.debug(f'Running Should_sample a span with the following attributes: {attributes}')

            if self._config is None:
                # sampler_logger.debug('No configuration is set, returning RECORD_AND_SAMPLE')
                return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))

            rules = self._config.get('attributesAndSamplerRules', [])
            global_fraction = self._config.get('fallbackFraction', 1) # default to 1 if not set which means always sample

            for rule in rules: # The first attribute rule that evaluates to true is used to determine the sampling decision based on its fraction.
                and_attributes_sampler_rules = rule.get('attributeConditions', [])

                # sampler_logger.debug(f'"AND" rule operands are: {and_attributes_sampler_rules}')

                and_rule_fraction = rule.get('fraction', 1) # default to 1 if not set which means always sample
                and_rule_met = True

                for and_rule in and_attributes_sampler_rules:
                    # If the "AND" rule is not met once, break the loop to avoid unnecessary checks
                    if not and_rule_met:
                        break

                    key = and_rule.get('key')
                    value = and_rule.get('val')
                    operator = and_rule.get('operator') # equals / notEquals / endWith / startWith

                    if key in attributes:

                        # Perform the corresponding operation
                        if operator in self._operations and self._operations[operator](attributes[key], value):
                            # sampler_logger.debug(f'Operator {operator} is true for the attribute {key} with value {value}')
                            pass
                        else:
                            # sampler_logger.debug(f'Operator {operator} is false, setting the "AND" rule flag to false')
                            and_rule_met = False
                    else:
                        # sampler_logger.debug(f'Attribute {key} is not present in the span attributes, setting the "AND" rule flag to false')
                        and_rule_met = False

                if and_rule_met:
                    # Perform the sampling decision
                    if self._trace_id_based_sampling(trace_id, and_rule_fraction):
                        # sampler_logger.debug(f'Trace [{trace_id}] is sampled "And rules" are met with fraction {and_rule_fraction}')
                        return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))
                    else:
                        # sampler_logger.debug(f'Trace [{trace_id}] is dropped "And rules" are met but fraction {and_rule_fraction} not met')
                        return SamplingResult(Decision.DROP)

            # Fallback to the global fraction if no rule matches
            # sampler_logger.debug(f'No rule matched, falling back to the global fraction {global_fraction}')
            if self._trace_id_based_sampling(trace_id, global_fraction):
                return SamplingResult(Decision.RECORD_AND_SAMPLE, attributes=attributes, trace_state=_get_parent_trace_state(parent_context))
            else:
                return SamplingResult(Decision.DROP)


    def get_description(self):
        return "OdigosSampler"

    def update_config(self, new_config):
        with self._lock:
            # sampler_logger.debug(f'Updating the configuration with the new configuration: {new_config}')
            self._config = new_config
