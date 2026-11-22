OPERATION = 'cold-spot'
OPTIONAL_FIELD = 'inner_position_samples'


def perturb(doc):
    doc[OPTIONAL_FIELD] = [[0, 20000], [30, 0]]


def verify(before, after):
    assert before['state'] == 'not_reached' and before['dose'] == ['47/6', '407/6']
    assert before['segments'][0] == {'seconds': ['0', '15/4'], 'position': 'outer', 'dose': ['45/16', '45/16']}
    assert before['segments'][1] == {'seconds': ['15/4', '6'], 'position': 'inner', 'dose': ['27/16', '27/16']}
    assert before['segments'][4]['dose'] == ['0', '54']
    assert after['state'] == 'needs_review' and after['dose'] == ['0', '190']
    assert [row['position'] for row in after['segments']] == ['inner_missing', 'both_missing', 'inner_missing']


def edge_cases(doc):
    from thermal.cold_spot import measure

    crossing = {**doc, 'samples': [[0, 0], [10, 20000]],
                'inner_position_samples': [[0, 20000], [10, 10000]], 'target_dose': 24}
    output = measure(crossing)
    # At 5 s the rate is 2, at the crossing it is 14/3, and at 10 s it is 2.
    assert output['dose'] == ['65/3', '65/3'] and output['state'] == 'not_reached'
    assert [row['seconds'] for row in output['segments']] == [['0', '20/3'], ['20/3', '10']]
    refined = {**crossing, 'samples': [[0, 0], [5, 10000], [10, 20000]]}
    assert measure(refined)['dose'] == output['dose']
