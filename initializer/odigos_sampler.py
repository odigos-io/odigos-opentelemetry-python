from opentelemetry.sdk.trace.sampling import Sampler, Decision, SamplingResult
from threading import Lock
import random

class OdigosSampler(Sampler):
    def __init__(self):
        self._lock = Lock()
        self._config = None

    def should_sample(self, parent_context, trace_id, name, kind, attributes, links):
        with self._lock:
            print(f'attributes : {attributes}')
            print(f'name : {name}')
            print(f'kind : {kind}')     
            if self._config is None:
                print('Recording and sampling- no config has been set')       
                return SamplingResult(Decision.RECORD_AND_SAMPLE)
        
            
            rules = self._config.get('rules', [])
            global_fraction = self._config.get('fallbackFraction', 1)
            for rule in rules:
                operands = rule.get('operands', [])
                
                print(f'rule operands are: {operands}')
                
                rule_fraction = rule.get('fraction', 1)
                for operand in operands: # TODO: implement AND logic
                    key = operand.get('key')
                    value = operand.get('value')
                    print(f'Operand key : {key} and value : {value}')
                    if key in attributes:
                        print(f'key is in attributes')
                        print(f'attributes[key]: {attributes[key]}')
                        if attributes[key] == value:
                            print(f'attributes[key] == value')
                            if random.random() < rule_fraction:
                                print(f'sampling brcause the attribute {key} is {value} and the fraction is {rule_fraction}')
                                return SamplingResult(Decision.RECORD_AND_SAMPLE)
                            else:
                                print(f'dropping because the attribute {key} is {value} and the fraction is {rule_fraction}')
                                return SamplingResult(Decision.DROP)    

            if random.random() < global_fraction:
                print(f'sampling because the global fraction is {global_fraction} and no rule match')
                return SamplingResult(Decision.RECORD_AND_SAMPLE)
            else:
                print(f'dropping because the global fraction is {global_fraction} and no rule match')
                return SamplingResult(Decision.DROP)
            

    def get_description(self):
        return "OdigosSampler"
    
    def update_config(self, new_config):
        with self._lock:
            print('config is updated')
            self._config = new_config