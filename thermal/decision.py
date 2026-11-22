"""Derive experiment dispositions and time ranges from the dose evidence."""
from fractions import Fraction
from .curve import checked_int
from .exposure import doses, measured


def classify(doc):
    target = checked_int(doc['target_dose'], 0, 1_000_000_000_000, 'target_dose')
    result = doses(doc)
    lo,hi = map(Fraction,result['dose'])
    result['state'] = 'reached' if lo >= target else ('not_reached' if hi < target else 'needs_review')
    return result


def windows(doc):
    threshold = checked_int(doc['rate_threshold'],0,1_000_000,'rate_threshold')
    keep, gaps = [], []
    for a,b,points,_,_ in measured(doc):
        if points is None:
            gaps.append([a,b])
            continue
        for (t0,r0),(t1,r1) in zip(points, points[1:]):
            if r0 < threshold and r1 < threshold:
                continue
            l,r = t0,t1
            if r0 < threshold or r1 < threshold:
                cut = t0 + (t1-t0)*(threshold-r0)/(r1-r0)
                if r0 < threshold:
                    l = cut
                else:
                    r = cut
            if l == r:
                continue
            if keep and keep[-1][1] == l:
                keep[-1][1] = r
            else:
                keep.append([l,r])
    return {'observed_windows': [[str(l),str(r)] for l,r in keep], 'unknown_windows': gaps}
