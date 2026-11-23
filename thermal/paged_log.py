"""Settle cumulative dose from paged recorder transmissions with explicit loss evidence."""
from bisect import bisect_right
from fractions import Fraction

from .curve import Response, checked_int

MAX_SECOND = 604_800
MAX_PAGE = 1_000_000
OUTSTANDING_LIMIT = 200


def check_page(page):
    """Validate one transmitted page and return (number, start, end, samples)."""
    number = checked_int(page['page'], 1, MAX_PAGE, 'page_number')
    span = page['range']
    if not isinstance(span, list) or len(span) != 2:
        raise ValueError('page_range')
    start = checked_int(span[0], 0, MAX_SECOND, 'page_range')
    end = checked_int(span[1], start, MAX_SECOND, 'page_range')
    if end - start > 86_400:
        raise ValueError('page_range')
    samples = page['samples']
    if not isinstance(samples, list) or len(samples) > 500:
        raise ValueError('page_samples')
    rows = []
    for row in samples:
        if not isinstance(row, list) or len(row) != 2:
            raise ValueError('page_samples')
        second = checked_int(row[0], start, end, 'page_sample_second')
        checked_int(row[1], -100_000, 150_000, 'temperature_mc')
        if rows and second <= rows[-1][0]:
            raise ValueError('timestamps_not_strict')
        rows.append((second, row[1]))
    return number, start, end, rows


def check_lost(entries):
    """Validate confirmed-lost declarations and return rows sorted by page number."""
    if not isinstance(entries, list) or len(entries) > 1000:
        raise ValueError('lost_pages')
    rows = []
    for entry in entries:
        number = checked_int(entry['page'], 1, MAX_PAGE, 'lost_page')
        span = entry['range']
        if not isinstance(span, list) or len(span) != 2:
            raise ValueError('lost_range')
        start = checked_int(span[0], 0, MAX_SECOND, 'lost_range')
        end = checked_int(span[1], start, MAX_SECOND, 'lost_range')
        if end - start > 86_400:
            raise ValueError('lost_range')
        rows.append((number, start, end))
    if len({number for number, _, _ in rows}) != len(rows):
        raise ValueError('lost_page_duplicate')
    by_start = sorted((start, end) for _, start, end in rows)
    for (prev_end, _), (start, _) in zip(by_start, by_start[1:]):
        if start <= prev_end:
            raise ValueError('lost_range_overlap')
    return sorted(rows)


def check_manifest(doc):
    """Validate a shutdown manifest and return (last_page, lost rows)."""
    last_page = checked_int(doc['last_page'], 1, MAX_PAGE, 'last_page')
    rows = check_lost(doc['lost'])
    if rows and rows[-1][0] > last_page:
        raise ValueError('lost_page_beyond_manifest')
    return last_page, rows


def outstanding_pages(received, lost, last_page):
    """Page numbers the recorder still has to hold or retransmit."""
    horizon = last_page if last_page is not None else (max(received) if received else 0)
    return [number for number in range(1, horizon + 1) if number not in received and number not in lost]


def _integral(a, b, x, y, left, right):
    slope = (y - x) / (b - a)
    return (right - left) * (2 * x + slope * (left + right - 2 * a)) / 2


def _gaps(declared, lo, hi):
    """Inclusive-second spans inside [lo, hi] covered by no declared page range."""
    missing = []
    cursor = lo
    for start, end in declared:
        if end < lo or start > hi:
            continue
        if start > cursor:
            missing.append([cursor, min(start - 1, hi)])
        cursor = max(cursor, end + 1)
        if cursor > hi:
            break
    if cursor <= hi:
        missing.append([cursor, hi])
    return missing


def settle(doc):
    """Compute checkpoint handover for one test from received pages and loss evidence."""
    response = Response(doc['knots'])
    max_gap = checked_int(doc['max_gap_s'], 1, 86_400, 'max_gap_s')
    points = doc['inspection_seconds']
    if (not isinstance(points, list) or not 1 <= len(points) <= 50
            or any(type(t) is not int or not 0 <= t <= MAX_SECOND for t in points)
            or points != sorted(set(points))):
        raise ValueError('inspection_seconds')
    pages = {}
    for raw in doc['pages']:
        number, start, end, samples = check_page(raw)
        if number in pages:
            raise ValueError('page_duplicate')
        pages[number] = (start, end, samples)
    lost = {number: (start, end) for number, start, end in check_lost(doc['lost'])}
    last_page = doc['last_page']
    if last_page is not None:
        checked_int(last_page, 1, MAX_PAGE, 'last_page')
        if any(number > last_page for number in (*pages, *lost)):
            raise ValueError('page_beyond_manifest')
    if set(pages) & set(lost):
        raise ValueError('page_also_lost')
    declared = sorted([*(span[:2] for span in pages.values()), *lost.values()])
    for (prev_end, _), (start, _) in zip(declared, declared[1:]):
        if start <= prev_end:
            raise ValueError('declared_overlap')
    samples = sorted(sample for _, _, rows in pages.values() for sample in rows)
    for _, temp in samples:
        checked_int(temp, response.x[0], response.x[-1], 'temperature_outside_response')
    times = [second for second, _ in samples]
    outstanding = outstanding_pages(set(pages), set(lost), last_page)
    closed = last_page is not None and not outstanding
    low_rate, high_rate = response.y[0], response.y[-1]
    rows = []
    for t in points:
        i = bisect_right(times, t)
        if i == 0:
            rows.append({'second': t, 'state': 'pending', 'reason': 'awaiting_samples',
                         'missing_ranges': _gaps(declared, 0, t)})
            continue
        anchor = times[0]
        previous = times[i - 1]
        following = times[i] if i < len(times) else None
        # A checkpoint strictly inside a sample span also depends on time up to the next sample.
        horizon = following - 1 if following is not None and previous < t else t
        missing = _gaps(declared, anchor, horizon)
        if missing:
            rows.append({'second': t, 'state': 'pending', 'reason': 'awaiting_pages',
                         'missing_ranges': missing})
            continue
        if following is None and previous < t and not closed:
            rows.append({'second': t, 'state': 'pending', 'reason': 'awaiting_manifest',
                         'missing_ranges': []})
            continue
        low = high = Fraction(0)
        unknown = 0
        for (a, v), (b, w) in zip(samples, samples[1:]):
            if a >= t:
                break
            right = min(b, t)
            if b - a > max_gap or any(start < b and a < end + 1 for start, end in lost.values()):
                low += (right - a) * low_rate
                high += (right - a) * high_rate
                unknown += right - a
            else:
                rates = [(moment, response.rate(temp)) for moment, temp in response.split(a, b, v, w)]
                for (p, x), (q, y) in zip(rates, rates[1:]):
                    lo_t, hi_t = max(p, Fraction(a)), min(q, Fraction(right))
                    if lo_t < hi_t:
                        dose = _integral(p, q, x, y, lo_t, hi_t)
                        low += dose
                        high += dose
        if t > times[-1]:
            low += (t - times[-1]) * low_rate
            high += (t - times[-1]) * high_rate
            unknown += t - times[-1]
        sample_limit = (following if following is not None else previous) if previous < t else t
        basis_pages = [number for number in sorted(pages)
                       if (pages[number][0] <= horizon and pages[number][1] >= anchor)
                       or any(second <= sample_limit for second, _ in pages[number][2])]
        basis_lost = [number for number in sorted(lost)
                      if lost[number][0] <= horizon and lost[number][1] >= anchor]
        rows.append({'second': t, 'state': 'exact' if low == high else 'bounded',
                     'dose': [str(low), str(high)], 'unknown_seconds': unknown,
                     'basis': {'pages': basis_pages, 'lost': basis_lost}})
    return {'state': 'complete' if closed else 'open', 'last_page': last_page,
            'received_pages': sorted(pages), 'lost_pages': sorted(lost),
            'outstanding_pages': outstanding[:OUTSTANDING_LIMIT],
            'outstanding_truncated': len(outstanding) > OUTSTANDING_LIMIT,
            'checkpoints': rows}
