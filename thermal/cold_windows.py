"""Report cold-spot evidence separately for each declared exposure window."""
from .cold_spot import integrate, positions
from .curve import checked_int


def report(doc):
    plans = doc['cold_windows']
    if not isinstance(plans, dict) or not 1 <= len(plans) <= 24 or any(not key.strip() for key in plans):
        raise ValueError('cold_window_ids')
    tracks = positions(doc)
    outer = tracks[2]
    earliest, latest = outer[0][0], outer[-1][0]
    windows = {}
    for name, (start, end, target) in sorted(plans.items()):
        checked_int(start, earliest, latest-1, 'cold_window_start')
        checked_int(end, start+1, latest, 'cold_window_end')
        checked_int(target, 0, 1_000_000_000_000, 'cold_window_target')
        windows[name] = {'seconds': [start, end], **integrate(tracks, start, end, target)}
    states = {row['state'] for row in windows.values()}
    state = 'not_reached' if 'not_reached' in states else 'needs_review' if 'needs_review' in states else 'reached'
    return {'state': state, 'windows': windows}
