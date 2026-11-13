"""Comparison scopes and trial identity for the November 13, 2026 draft."""
PROTOCOL_VERSION = 'paper-2026-11-13'
METHODS = ('Random', 'EZR', 'RRP', 'BS-LLM', 'AMP-2', 'AMP-3', 'AMP-4',
           'HKMA-scout', 'HKMA-rag', 'HKMA-combined')
SENSITIVITY_METHODS = METHODS + ('SynthCore-28',)
OPTIONAL_METHODS = ('SynthCore-28', 'SynthCore', 'DAPR')
METRICS = ('chebyshev',)
QUESTIONS = {
    1: 'With only 24 labels, can domain knowledge help an LLM propose better initial configurations?',
    2: 'Does increasing the number of configuration parameters change which kinds of knowledge help?',
    3: "Does human review of the LLM's domain rules help?",
    4: 'What does checked knowledge cost?',
}


def normalize_preparation(value):
    """Normalize optional one-time effort; missing measurements remain unknown."""
    import math
    fields = ('expert_contacts', 'generation_exchanges', 'nominal_benchmark_accesses',
              'distinct_labels', 'llm_calls', 'total_tokens', 'api_cost_usd', 'calendar_days')
    if not isinstance(value, dict) or set(value) - set(fields):
        raise ValueError('preparation must contain only documented effort fields')
    result = {field: value.get(field) for field in fields}
    for field, number in result.items():
        if number is None:
            continue
        if (isinstance(number, bool) or not isinstance(number, (int, float))
                or not math.isfinite(number) or number < 0
                or (field != 'api_cost_usd' and int(number) != number)):
            raise ValueError(f'preparation.{field} must be a finite nonnegative count or null')
    contacts, exchanges = result['expert_contacts'], result['generation_exchanges']
    if contacts is not None and not 1 <= contacts <= 10:
        raise ValueError('preparation.expert_contacts must be between 1 and 10')
    if exchanges is not None:
        if exchanges > 9:
            raise ValueError('At most nine generation exchanges follow the initial contact')
        if contacts is not None and exchanges >= contacts:
            raise ValueError('Generation exchanges exclude the initial claim-review contact')
        nominal = 6 * exchanges
        if result['nominal_benchmark_accesses'] not in (None, nominal):
            raise ValueError('Nominal preparation uses six accesses per generation exchange')
        result['nominal_benchmark_accesses'] = nominal
    if (result['distinct_labels'] is not None and result['nominal_benchmark_accesses'] is not None
            and result['distinct_labels'] > result['nominal_benchmark_accesses']):
        raise ValueError('Distinct offline labels cannot exceed nominal accesses')
    return result
