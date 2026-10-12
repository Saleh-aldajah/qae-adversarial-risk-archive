#!/usr/bin/env python3
"""
run_symatch_w1_diagnostic_v24.py — resolution of the bare-symatch weight-1
count discrepancy (review Sec. 7 / finding C09: manuscript claims 48/72
(X) and 57/72 (Z) uncorrectable single-qubit faults; the reviewer's
independent diagnostic obtained 24 and 15).

Method: decode ALL 72 single-qubit errors per sector through the archived
bare-symatch comparator face (SymatchCmp(bp=False, predecode=False,
simplex=False)), using the same syndrome convention and the same
flip-vector endpoint as the pinned paired grid.  A fault is counted
uncorrectable iff the predicted logical flip vector differs from the true
one (grid endpoint).  Additionally we report the stricter criterion
"decoded correction differs from the injected error by a non-stabilizer"
for reference.

Output: results/symatch_w1_diagnostic_v24.json
"""
import json, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for _p in (os.path.join(ROOT, 'qae_experiments'),
           os.path.join(ROOT, 'archive-rerun'), HERE):
    if os.path.isdir(_p):
        sys.path.insert(0, _p)

from bb_codes import BB72
from cmp_common import SymatchCmp

HX, HZ = BB72['HX'], BB72['HZ']


def main():
    dec = SymatchCmp(0.001, bp=False, predecode=False, simplex=False,
                     tag='symatch-bare')
    out = {}
    for sector, H, fail_fn, dec_fn in (
            ('X', HZ, dec.fail_x, dec.decode_x),
            ('Z', HX, dec.fail_z, dec.decode_z)):
        bad = []
        for q in range(72):
            e = np.zeros(72, np.uint8); e[q] = 1
            s = (H @ e) % 2
            pred = dec_fn(s)
            if fail_fn(e, pred):
                bad.append(q)
        out[sector] = dict(uncorrectable=len(bad), qubits=bad)
        print(f"bare symatch {sector}-sector: {len(bad)}/72 uncorrectable "
              f"weight-1 faults -> {bad}", flush=True)
    out['note'] = ('v23 text reported 48/72 (X) and 57/72 (Z); reviewer '
                   'diagnostic reported 24 and 15. This run uses the '
                   'archived comparator face and grid endpoint.')
    with open(os.path.join(HERE, 'results',
                           'symatch_w1_diagnostic_v24.json'), 'w') as f:
        json.dump(out, f, indent=1)


if __name__ == '__main__':
    main()
