"""Re-evaluate the same observed temperatures under alternate response tables."""
from .decision import classify


def review(doc):
    alternatives = doc['alternate_knots']
    if not isinstance(alternatives, dict) or not 1 <= len(alternatives) <= 8 or 'original' in alternatives:
        raise ValueError('alternate_calibrations')
    baseline = classify(doc)
    trials = {'original': {'state': baseline['state'], 'dose': baseline['dose']}}
    for label, knots in sorted(alternatives.items()):
        if not label.strip() or len(label) > 80:
            raise ValueError('calibration_label')
        try:
            result = classify({**doc, 'knots': knots})
        except ValueError as exc:
            if str(exc) != 'temperature_outside_response':
                raise
            trials[label] = {'state': 'out_of_range', 'dose': None}
        else:
            trials[label] = {'state': result['state'], 'dose': result['dose']}
    states = {row['state'] for row in trials.values()}
    return {'state': baseline['state'] if len(states) == 1 else 'calibration_dependent',
            'alternatives': [{'id': k, **v} for k, v in trials.items()]}
