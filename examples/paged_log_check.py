"""Exercise paged recorder intake, durable receipts and checkpoint handover across a restart."""
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sqlite3
import sys
from tempfile import TemporaryDirectory
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from workbench import profile
from workbench.db import initialize
from workbench.http import Endpoint
from workbench.service import Service

# Synthetic record: response rate is linear in temperature, so with a linear
# temperature path the rate at second t is t (0 at page 1's second 0, 10 at
# page 2's second 10); the 10 s span allows direct connection (max_gap_s=10).
SETTLEMENT = {'knots': [[0, 0], [20000, 10]], 'max_gap_s': 10, 'inspection_seconds': [5]}


class QuietEndpoint(Endpoint):
    def log_message(self, *args):
        pass


def caller(port):
    def call(route, data=None, *, fault=None):
        kwargs = {} if data is None else {'data': json.dumps(data).encode(),
                                          'headers': {'Content-Type': 'application/json'}}
        request = Request(f'http://127.0.0.1:{port}{route}', **kwargs)
        try:
            with urlopen(request, timeout=10) as response:
                assert fault is None, (route, fault)
                return json.loads(response.read())
        except HTTPError as exc:
            with exc:
                assert (exc.code, json.load(exc)['error']) == fault, (route, exc.code, fault)
    return call


def serve(db_path):
    server = ThreadingHTTPServer(('127.0.0.1', 0), QuietEndpoint)
    server.service = Service(db_path, profile)
    worker = Thread(target=server.serve_forever)
    worker.start()
    return server, worker


def stop(server, worker):
    server.shutdown()
    worker.join()
    server.server_close()


def phase_one(call):
    assert [op['id'] for op in call('/api/meta')['operations']] == list(profile.OPERATIONS)
    trial = 'pkg-trial-a'
    page2 = {'test': trial, 'page': 2, 'range': [5, 10], 'samples': [[10, 20000]]}
    call('/api/paged/status', {'test': trial}, fault=(404, 'test_not_found'))
    call('/api/paged/handover', {'test': trial, **SETTLEMENT}, fault=(404, 'test_not_found'))
    call('/api/paged/page', {'test': trial, 'page': 2, 'range': [5, 10]}, fault=(400, 'required_field'))
    call('/api/paged/page', {'test': trial, 'page': 2, 'range': [5, 10], 'samples': [[11, 0]]},
         fault=(422, 'domain_input'))
    # Page 2 arrives before page 1; acceptance is acknowledged at once, durably.
    second = call('/api/paged/page', page2)
    assert second['stored'] == 'accepted' and second['page'] == 2
    status = call('/api/paged/status', {'test': trial})
    assert status['state'] == 'open' and status['outstanding_pages'] == [1]
    assert [row['page'] for row in status['received']] == [2]
    assert status['received'][0]['receipt'] == second['receipt']
    # Accepted is not yet settleable: second 5 stays pending while page 1 is missing.
    pending = call('/api/paged/handover', {'test': trial, **SETTLEMENT})
    assert pending['state'] == 'open' and pending['outstanding_pages'] == [1]
    assert pending['checkpoints'] == [{'second': 5, 'state': 'pending', 'reason': 'awaiting_samples',
                                       'missing_ranges': [[0, 4]]}]
    return second['receipt'], pending


def phase_two(call, receipt2, pending):
    trial = 'pkg-trial-a'
    page1 = {'test': trial, 'page': 1, 'range': [0, 4], 'samples': [[0, 0]]}
    page2 = {'test': trial, 'page': 2, 'range': [5, 10], 'samples': [[10, 20000]]}
    # After the restart the receipt for page 2 is still on file: it is not requested again.
    status = call('/api/paged/status', {'test': trial})
    assert status['outstanding_pages'] == [1]
    assert status['received'][0]['receipt'] == receipt2
    assert call('/api/paged/page', page2) == {'test': trial, 'page': 2, 'receipt': receipt2,
                                              'stored': 'duplicate'}
    call('/api/paged/page', {**page2, 'samples': [[10, 10000]]}, fault=(409, 'page_conflict'))
    assert call('/api/paged/handover', {'test': trial, **SETTLEMENT}) == pending
    first = call('/api/paged/page', page1)
    assert first['stored'] == 'accepted'
    receipt1 = first['receipt']
    assert call('/api/paged/status', {'test': trial})['outstanding_pages'] == []
    # Both pages in: the page boundary is no interruption and second 5 settles exactly.
    delivered = call('/api/paged/handover', {'test': trial, **SETTLEMENT})
    checkpoint, = delivered['checkpoints']
    assert delivered['received_pages'] == [1, 2] and delivered['outstanding_pages'] == []
    assert checkpoint['second'] == 5 and checkpoint['state'] == 'exact'
    assert checkpoint['dose'] == ['25/2', '25/2'] and checkpoint['unknown_seconds'] == 0
    assert checkpoint['basis'] == {'pages': [{'page': 1, 'receipt': receipt1},
                                             {'page': 2, 'receipt': receipt2}], 'lost': []}
    # Resending a stored page changes nothing and never double-counts.
    assert call('/api/paged/page', page1)['stored'] == 'duplicate'
    assert call('/api/paged/handover', {'test': trial, **SETTLEMENT}) == delivered
    call('/api/paged/page', {'test': trial, 'page': 3, 'range': [4, 8], 'samples': []},
         fault=(409, 'page_range_conflict'))

    # Contrast from the start of the trial: page 2 is confirmed lost and covers second 5.
    other = 'pkg-trial-b'
    call('/api/paged/page', {'test': other, 'page': 1, 'range': [0, 4], 'samples': [[0, 0]]})
    call('/api/paged/page', {'test': other, 'page': 3, 'range': [10, 10], 'samples': [[10, 20000]]})
    pending = call('/api/paged/handover', {'test': other, **SETTLEMENT})
    assert pending['checkpoints'] == [{'second': 5, 'state': 'pending', 'reason': 'awaiting_pages',
                                       'missing_ranges': [[5, 9]]}]
    manifest = {'test': other, 'last_page': 3, 'lost': [{'page': 2, 'range': [5, 9]}]}
    declared = call('/api/paged/manifest', manifest)
    assert declared['stored'] == 'declared'
    # With the loss credential the checkpoint delivers a traceable interval, not an exact value.
    bounded = call('/api/paged/handover', {'test': other, **SETTLEMENT})
    checkpoint, = bounded['checkpoints']
    assert bounded['state'] == 'complete' and bounded['manifest_receipt'] == declared['receipt']
    assert checkpoint['state'] == 'bounded' and checkpoint['dose'] == ['0', '50']
    assert checkpoint['unknown_seconds'] == 5
    assert checkpoint['basis']['pages'] == [{'page': p['page'], 'receipt': p['receipt']}
                                            for p in call('/api/paged/status', {'test': other})['received']]
    assert checkpoint['basis']['lost'] == [{'page': 2, 'range': [5, 9]}]
    assert call('/api/paged/manifest', manifest)['stored'] == 'duplicate'
    call('/api/paged/manifest', {**manifest, 'last_page': 4}, fault=(409, 'manifest_conflict'))
    call('/api/paged/page', {'test': other, 'page': 2, 'range': [5, 9], 'samples': [[5, 0]]},
         fault=(409, 'page_declared_lost'))
    call('/api/paged/page', {'test': other, 'page': 4, 'range': [11, 12], 'samples': []},
         fault=(409, 'page_beyond_manifest'))
    clash = 'pkg-trial-c'
    call('/api/paged/page', {'test': clash, 'page': 1, 'range': [0, 4], 'samples': [[0, 0]]})
    call('/api/paged/manifest', {'test': clash, 'last_page': 2, 'lost': [{'page': 2, 'range': [2, 6]}]},
         fault=(409, 'manifest_pages_conflict'))


def check_migration(tmp):
    legacy = Path(tmp) / 'legacy.sqlite3'
    initialize(legacy, profile.PRODUCT)
    with sqlite3.connect(legacy) as db:
        db.execute('PRAGMA user_version=2')
        db.execute('DROP TABLE paged_pages')
        db.execute('DROP TABLE paged_manifests')
    initialize(legacy, profile.PRODUCT)
    with sqlite3.connect(legacy) as db:
        assert db.execute('PRAGMA user_version').fetchone()[0] == 3
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name='paged_pages'").fetchone()
        assert db.execute("SELECT 1 FROM sqlite_master WHERE name='reviews'").fetchone()


def main():
    with TemporaryDirectory() as tmp:
        db = Path(tmp) / 'paged.sqlite3'
        initialize(db, profile.PRODUCT)
        with sqlite3.connect(db) as handle:
            assert handle.execute('PRAGMA user_version').fetchone()[0] == 3
        server, worker = serve(db)
        try:
            receipt2, pending = phase_one(caller(server.server_port))
        finally:
            stop(server, worker)
        # The workbench restarts on the same database file.
        server, worker = serve(db)
        try:
            phase_two(caller(server.server_port), receipt2, pending)
        finally:
            stop(server, worker)
        check_migration(tmp)
    print(f'{profile.PRODUCT}: paged intake, restart and handover checks passed')


if __name__ == '__main__':
    main()
