"""Paged recorder intake: durable acceptance receipts and checkpoint handover."""
import re

from thermal.paged_log import OUTSTANDING_LIMIT, check_manifest, check_page, outstanding_pages, settle

from .codec import decode, encode, sha
from .errors import Problem


def _test(value):
    if not isinstance(value, str) or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}', value) is None:
        raise Problem('test_id')
    return value


def _domain(exc):
    detail = str(exc) if type(exc) is ValueError and str(exc).isascii() and len(str(exc)) < 100 else None
    return Problem('domain_input', 422, detail)


def _pages(db, test):
    return db.execute('SELECT * FROM paged_pages WHERE test=? ORDER BY page', (test,)).fetchall()


def _manifest(db, test):
    return db.execute('SELECT * FROM paged_manifests WHERE test=?', (test,)).fetchone()


def accept_page(db, data):
    test = _test(data['test'])
    try:
        number, start, end, samples = check_page(data)
    except (TypeError, ValueError) as exc:
        raise _domain(exc) from exc
    canonical = encode([[second, temp] for second, temp in samples])
    receipt = sha(encode([test, number, start, end, canonical]))
    existing = db.execute('SELECT receipt FROM paged_pages WHERE test=? AND page=?', (test, number)).fetchone()
    if existing is not None:
        if existing['receipt'] != receipt:
            raise Problem('page_conflict', 409)
        return {'test': test, 'page': number, 'receipt': receipt, 'stored': 'duplicate'}
    clash = db.execute('SELECT page FROM paged_pages WHERE test=? AND start_second<=? AND end_second>=?',
                       (test, end, start)).fetchone()
    if clash is not None:
        raise Problem('page_range_conflict', 409)
    manifest = _manifest(db, test)
    if manifest is not None:
        lost = decode(manifest['lost'])
        if number > manifest['last_page']:
            raise Problem('page_beyond_manifest', 409)
        if any(entry['page'] == number for entry in lost):
            raise Problem('page_declared_lost', 409)
        if any(entry['range'][0] <= end and start <= entry['range'][1] for entry in lost):
            raise Problem('page_range_conflict', 409)
    db.execute('INSERT INTO paged_pages(test, page, start_second, end_second, samples, receipt) VALUES(?, ?, ?, ?, ?, ?)',
               (test, number, start, end, canonical, receipt))
    return {'test': test, 'page': number, 'receipt': receipt, 'stored': 'accepted'}


def record_manifest(db, data):
    test = _test(data['test'])
    try:
        last_page, lost = check_manifest(data)
    except (TypeError, ValueError) as exc:
        raise _domain(exc) from exc
    rows = [{'page': number, 'range': [start, end]} for number, start, end in lost]
    canonical = encode(rows)
    receipt = sha(encode([test, 'manifest', last_page, canonical]))
    existing = _manifest(db, test)
    if existing is not None:
        if existing['receipt'] != receipt:
            raise Problem('manifest_conflict', 409)
        return {'test': test, 'receipt': receipt, 'last_page': last_page, 'lost': rows, 'stored': 'duplicate'}
    lost_numbers = {number for number, _, _ in lost}
    for page in _pages(db, test):
        if (page['page'] > last_page or page['page'] in lost_numbers or
                any(start <= page['end_second'] and page['start_second'] <= end for _, start, end in lost)):
            raise Problem('manifest_pages_conflict', 409)
    db.execute('INSERT INTO paged_manifests(test, last_page, lost, receipt) VALUES(?, ?, ?, ?)',
               (test, last_page, canonical, receipt))
    return {'test': test, 'receipt': receipt, 'last_page': last_page, 'lost': rows, 'stored': 'declared'}


def _load(db, test):
    pages = _pages(db, test)
    manifest = _manifest(db, test)
    if not pages and manifest is None:
        raise Problem('test_not_found', 404)
    lost = decode(manifest['lost']) if manifest is not None else []
    last_page = manifest['last_page'] if manifest is not None else None
    return pages, manifest, lost, last_page


def status(db, data):
    test = _test(data['test'])
    pages, _, lost, last_page = _load(db, test)
    received = [row['page'] for row in pages]
    outstanding = outstanding_pages(set(received), {entry['page'] for entry in lost}, last_page)
    return {'test': test,
            'state': 'complete' if last_page is not None and not outstanding else 'open',
            'last_page': last_page,
            'received': [{'page': row['page'], 'range': [row['start_second'], row['end_second']],
                          'samples': decode(row['samples']), 'receipt': row['receipt']} for row in pages],
            'lost': lost,
            'outstanding_pages': outstanding[:OUTSTANDING_LIMIT],
            'outstanding_truncated': len(outstanding) > OUTSTANDING_LIMIT}


def handover(db, data):
    test = _test(data['test'])
    pages, manifest, lost, last_page = _load(db, test)
    doc = {'knots': data['knots'], 'max_gap_s': data['max_gap_s'],
           'inspection_seconds': data['inspection_seconds'],
           'pages': [{'page': row['page'], 'range': [row['start_second'], row['end_second']],
                      'samples': decode(row['samples'])} for row in pages],
           'lost': lost, 'last_page': last_page}
    try:
        result = settle(doc)
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError, AttributeError, IndexError) as exc:
        raise _domain(exc) from exc
    receipts = {row['page']: row['receipt'] for row in pages}
    lost_ranges = {entry['page']: entry['range'] for entry in lost}
    for checkpoint in result['checkpoints']:
        basis = checkpoint.get('basis')
        if basis is not None:
            basis['pages'] = [{'page': number, 'receipt': receipts[number]} for number in basis['pages']]
            basis['lost'] = [{'page': number, 'range': lost_ranges[number]} for number in basis['lost']]
    result['test'] = test
    if manifest is not None:
        result['manifest_receipt'] = manifest['receipt']
    return result
