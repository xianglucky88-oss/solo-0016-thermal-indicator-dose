from copy import deepcopy

from thermal.clock_alignment import align
from thermal.cold_windows import report


OPERATION = 'clock-alignment'
OPTIONAL_FIELD = 'clock_alignment'


def perturb(doc):
    doc['clock_alignment']['sync'][1][1] = 29


def verify(before, after):
    assert before['seconds_per_tick'] == '1/2'
    assert before['aligned_samples'][1] == [6, 0]
    assert before['windows']['entry']['dose'] == ['8/5', '8/5']
    assert after['state'] == 'unresolved_clock' and 'windows' not in after
    assert {'tick': 12, 'second': '29/5', 'reason': 'fractional_second'} in after['unresolved']


def edge_cases(doc):
    assert align(doc)['windows'] == report(doc)['windows']
    a = deepcopy(doc)
    a['clock_alignment']['sync'] = [[12, 6], [60, 30]]
    assert align(a)['unresolved'] == [{'tick': 0, 'reason': 'outside_sync_marks'}]
    a['clock_alignment'] = {'sync': [[0, 0], [20, 20]], 'samples': [[0, 16000], [10, 16000], [20, 16000]]}
    assert align(a)['windows']['entry']['state'] == 'reached'
    a['clock_alignment']['sync'][1][1] = 40
    assert align(a)['windows']['entry']['state'] == 'needs_review'
