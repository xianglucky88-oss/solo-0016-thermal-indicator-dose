"""Allocate exact covered exposure and conservative gap bounds to report windows."""
from fractions import Fraction

from .exposure import measured


def _integral(a, b, x, y, left, right):
    slope = (y-x)/(b-a)
    return (right-left)*(2*x+slope*(left+right-2*a))/2


def account(doc):
    spans = list(measured(doc))
    cuts = doc['report_cuts_s']
    if (not isinstance(cuts, list) or len(cuts) > 50 or any(type(c) is not int for c in cuts)
            or cuts != sorted(set(cuts)) or any(not spans[0][0] < c < spans[-1][1] for c in cuts)):
        raise ValueError('report_cuts')
    edges = [spans[0][0], *cuts, spans[-1][1]]
    rows, sums = [], [Fraction(0), Fraction(0)]
    for start, end in zip(edges, edges[1:]):
        low = high = Fraction(0)
        unknown = 0
        for a, b, points, minimum, maximum in spans:
            left, right = max(a, start), min(b, end)
            if left >= right:
                continue
            if points is None:
                share = Fraction(right-left, b-a)
                low += share * minimum
                high += share * maximum
                unknown += right-left
            else:
                for (p, x), (q, y) in zip(points, points[1:]):
                    u, v = max(p, left), min(q, right)
                    if u < v:
                        dose = _integral(p, q, x, y, u, v)
                        low += dose
                        high += dose
        sums[0] += low
        sums[1] += high
        rows.append({'seconds': [start, end], 'unknown_seconds': unknown, 'dose': [str(low), str(high)]})
    return {'segments': rows, 'whole_dose': list(map(str, sums))}
