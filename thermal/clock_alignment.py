"""Use two witnessed sync marks to align an inner logger before cold-window accounting."""
from fractions import Fraction

from .cold_windows import report as windows
from .curve import checked_int
from .exposure import series


def align(doc):
    plan = doc['clock_alignment']
    (first_tick, first_second), (last_tick, last_second) = plan['sync']
    for value in (first_tick, last_tick, first_second, last_second):
        checked_int(value, 0, 604_800, 'sync_mark_index')
    if first_tick >= last_tick or first_second >= last_second:
        raise ValueError('sync_order')

    _, _, track = series({**doc, 'samples': plan['samples']})
    ratio = Fraction(last_second-first_second, last_tick-first_tick)
    transformed, unresolved = [], []
    for tick, temperature in track:
        if not first_tick <= tick <= last_tick:
            unresolved.append({'tick': tick, 'reason': 'outside_sync_marks'})
            continue
        second = first_second + (tick-first_tick)*ratio
        if second.denominator != 1:
            unresolved.append({'tick': tick, 'reason': 'fractional_second', 'second': str(second)})
        else:
            transformed.append([int(second), temperature])
    evidence = {'sync': plan['sync'], 'seconds_per_tick': str(ratio)}
    if unresolved:
        return {'state': 'unresolved_clock', **evidence, 'unresolved': unresolved}
    accounted = windows({**doc, 'inner_position_samples': transformed})
    return {'state': accounted['state'], **evidence, 'aligned_samples': transformed,
            'windows': accounted['windows']}
