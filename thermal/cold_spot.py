"""Integrate the instantaneous cold spot at two distinct packaging positions."""
from bisect import bisect_right
from fractions import Fraction

from .curve import checked_int
from .exposure import series


def _track(observations, times, max_gap, start, end):
    i = bisect_right(times, start)-1
    if i < 0 or i+1 == len(times):
        return None
    a, x = observations[i]
    b, y = observations[i+1]
    if end > b or b-a > max_gap:
        return None
    return tuple(x + Fraction((t-a)*(y-x), b-a) for t in (start, end))


def _dose(response, start, end, left, right):
    points = [(t, response.rate(temp)) for t, temp in response.split(start, end, left, right)]
    return sum((b-a)*(x+y)/2 for (a, x), (b, y) in zip(points, points[1:]))


def positions(doc):
    response, gap, first = series(doc)
    _, _, second = series({**doc, 'samples': doc['inner_position_samples']})
    return response, gap, first, second


def integrate(tracks, start, end, target):
    response, gap, first, second = tracks
    outer_times, inner_times = ([t for t, _ in track] for track in (first, second))
    edges = [start, *sorted({t for t in (*outer_times, *inner_times) if start < t < end}), end]
    low = high = Fraction(0)
    rows = []

    def record(a, b, position, minimum, maximum):
        nonlocal low, high
        low += minimum
        high += maximum
        rows.append({'seconds': [str(a), str(b)], 'position': position,
                     'dose': [str(minimum), str(maximum)]})

    for a, b in zip(edges, edges[1:]):
        outer = _track(first, outer_times, gap, a, b)
        inner = _track(second, inner_times, gap, a, b)
        if outer is None or inner is None:
            known = outer if outer is not None else inner
            bound = _dose(response, a, b, *known) if known is not None else (b-a)*response.y[-1]
            status = ('inner_missing' if outer is not None
                      else 'outer_missing' if inner is not None else 'both_missing')
            record(a, b, status, (b-a)*response.y[0], bound)
            continue
        left, right = outer[0]-inner[0], outer[1]-inner[1]
        if left*right < 0:
            portion = left/(left-right)
            pivot = a+(b-a)*portion
            temp = outer[0]+portion*(outer[1]-outer[0])
            first_name, second_name = ('outer', 'inner') if left < 0 else ('inner', 'outer')
            pre = _dose(response, a, pivot, min(outer[0], inner[0]), temp)
            post = _dose(response, pivot, b, temp, min(outer[1], inner[1]))
            record(a, pivot, first_name, pre, pre)
            record(pivot, b, second_name, post, post)
        else:
            name = 'both' if left == right == 0 else ('outer' if max(left, right) <= 0 else 'inner')
            dose = _dose(response, a, b, min(outer[0], inner[0]), min(outer[1], inner[1]))
            record(a, b, name, dose, dose)
    state = 'reached' if low >= target else ('not_reached' if high < target else 'needs_review')
    return {'state': state, 'dose': [str(low), str(high)], 'target_dose': target, 'segments': rows}


def measure(doc):
    tracks = positions(doc)
    outer = tracks[2]
    target = checked_int(doc['target_dose'], 0, 1_000_000_000_000, 'target_dose')
    return integrate(tracks, outer[0][0], outer[-1][0], target)
