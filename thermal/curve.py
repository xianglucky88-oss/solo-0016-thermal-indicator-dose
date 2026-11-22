"""Piecewise-linear synthetic indicator response, with no extrapolation."""
from bisect import bisect_right
from fractions import Fraction


def checked_int(value, lo, hi, label):
    if type(value) is not int or not lo <= value <= hi:
        raise ValueError(label)
    return value


class Response:
    def __init__(self, rows):
        if not isinstance(rows, list) or not 2 <= len(rows) <= 30:
            raise ValueError('response_count')
        self.x = tuple(checked_int(t, -100_000, 150_000, 'temperature_mc') for t, _ in rows)
        self.y = tuple(checked_int(rate, 0, 1_000_000, 'response_rate') for _, rate in rows)
        if self.x != tuple(sorted(set(self.x))) or self.y != tuple(sorted(self.y)):
            raise ValueError('response_order')

    def rate(self, temp):
        if not self.x[0] <= temp <= self.x[-1]:
            raise ValueError('temperature_outside_response')
        i = bisect_right(self.x, temp) - 1
        if i == len(self.x) - 1:
            return Fraction(self.y[-1])
        return self.y[i] + Fraction(temp - self.x[i], self.x[i+1] - self.x[i]) * (self.y[i+1] - self.y[i])

    def split(self, t0, t1, a, b):
        points = [(Fraction(t0), a), (Fraction(t1), b)]
        if a != b:
            points.extend((t0 + Fraction(x-a, b-a) * (t1-t0), x) for x in self.x if min(a,b) < x < max(a,b))
        return sorted(points)
