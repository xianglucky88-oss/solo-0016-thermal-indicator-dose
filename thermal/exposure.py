"""Integrate response on covered spans and keep missing time explicit."""
from fractions import Fraction
from .curve import Response, checked_int


def series(doc):
    response = Response(doc['knots'])
    max_gap = checked_int(doc['max_gap_s'], 1, 86_400, 'max_gap_s')
    samples = doc['samples']
    if not isinstance(samples, list) or not 2 <= len(samples) <= 500:
        raise ValueError('sample_count')
    observations = []
    for t, temp in samples:
        checked_int(t, 0, 604_800, 'second_index')
        checked_int(temp, response.x[0], response.x[-1], 'temperature_outside_response')
        if observations and t <= observations[-1][0]:
            raise ValueError('timestamps_not_strict')
        observations.append((t,temp))
    return response, max_gap, observations


def measured(doc):
    response, max_gap, observations = series(doc)
    for (a, v), (b, w) in zip(observations, observations[1:]):
        if b-a > max_gap:
            yield a, b, None, (b-a)*response.y[0], (b-a)*response.y[-1]
        else:
            points = tuple((t, response.rate(temp)) for t,temp in response.split(a,b,v,w))
            dose = sum((t1-t0)*(r0+r1)/2 for (t0,r0),(t1,r1) in zip(points, points[1:]))
            yield a, b, points, dose, dose


def doses(doc):
    low = high = Fraction(0)
    spans = []
    for a,b,points,x,y in measured(doc):
        low += x
        high += y
        spans.append({'seconds':[a,b], 'state':'covered' if points else 'gap', 'dose':[str(x),str(y)]})
    return {'dose':[str(low),str(high)], 'spans':spans}
