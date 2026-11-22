"""Produce review work items ordered by uncertain dose, not by time alone."""
from .exposure import measured


def register(doc):
    gaps = [(high-low, a, b, low, high) for a, b, points, low, high in measured(doc) if points is None]
    ordered = sorted(gaps, key=lambda row: (-row[0], row[1]))
    return {'gap_count': len(gaps), 'missing_seconds': sum(b-a for _, a, b, _, _ in gaps),
            'rows': [{'seconds': [a, b], 'dose_bounds': [str(low), str(high)], 'uncertainty': str(width)}
                     for width, a, b, low, high in ordered]}
