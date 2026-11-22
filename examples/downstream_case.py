OPERATION = 'cold-windows'
OPTIONAL_FIELD = 'cold_windows'


def perturb(doc):
    doc['inner_position_samples'] = [[0, 20000], [30, 0]]


def verify(before, after):
    entry, handover = (before['windows'][name] for name in ('entry', 'handover'))
    assert entry['state'] == 'reached' and entry['dose'] == ['8/5', '8/5']
    assert handover['state'] == 'needs_review' and handover['dose'] == ['0', '68/9']
    assert after['windows']['entry']['dose'] == ['0', '8/5']
    assert after['windows']['entry']['state'] == 'needs_review'
    assert after['windows']['handover']['dose'] == ['0', '20']
