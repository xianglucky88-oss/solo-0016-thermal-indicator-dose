"""Report cumulative exposure evidence at scheduled inspection instants."""
from fractions import Fraction

from .curve import checked_int
from .exposure import series
from .interval_accounts import account


def inspect(doc):
    _, _, observations = series(doc)
    start, end = observations[0][0], observations[-1][0]
    points = doc['inspection_seconds']
    if (not isinstance(points, list) or not 1 <= len(points) <= 50
            or any(type(t) is not int or not start <= t <= end for t in points)
            or points != sorted(set(points))):
        raise ValueError('inspection_seconds')
    target = checked_int(doc['target_dose'], 0, 1_000_000_000_000, 'target_dose')
    accounts = account({**doc, 'report_cuts_s': [t for t in points if start < t < end]})
    low = high = Fraction(0)
    unknown = 0

    def snapshot(second):
        state = 'reached' if low >= target else ('not_reached' if high < target else 'needs_review')
        return {'second': second, 'dose': [str(low), str(high)], 'unknown_seconds': unknown, 'state': state}

    rows = [snapshot(start)] if start in points else []
    for segment in accounts['segments']:
        a, b = map(Fraction, segment['dose'])
        low, high = low + a, high + b
        unknown += segment['unknown_seconds']
        second = segment['seconds'][1]
        if second in points:
            rows.append(snapshot(second))
    return {'target_dose': target, 'checkpoints': rows}
