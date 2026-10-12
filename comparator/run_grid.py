"""
run_grid.py — pinned BB72 comparator grid: modern decoders vs BP+OSD control.

Usage:
  python run_grid.py --decoders bposd relay ... --ps 0.001 ... --trials 10000 \
      --out results/comparator_grid.csv --failbits results/failbits

Each (decoder, p) task: TRIALS paired trials (identical error instances across
decoders via the COMPARE stream), both sectors per trial, fail if either
sector logical-fails. Wilson 95% CIs. Per-trial fail bits saved for McNemar.
"""
import os, sys, csv, json, time, hashlib, argparse
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cmp_common as C


def run_task(task):
    dec_label, p, trials, failbits_dir = task
    import cmp_common as C2  # fresh import in worker
    dec = C2.DECODER_SPECS[dec_label](p)
    ez, ex, seed = C2.trial_errors(p, trials)
    HX, HZ = C2.BB72['HX'], C2.BB72['HZ']
    fails = np.zeros(trials, dtype=np.uint8)
    t0 = time.time()
    for t in range(trials):
        sx = (HZ @ ex[t]) % 2
        sz = (HX @ ez[t]) % 2
        px_ = dec.decode_x(sx)
        pz_ = dec.decode_z(sz)
        fx = dec.fail_x(ex[t], px_)
        fz = dec.fail_z(ez[t], pz_)
        fails[t] = 1 if (fx or fz) else 0
    dt = time.time() - t0
    k = int(fails.sum())
    lo, hi = C2.wilson95(k, trials)
    row = dict(exp='comparator_grid', code='BB72', decoder=dec.name,
               decoder_key=dec_label, rounds=1, p=p, trials=trials, failures=k,
               ler=round(k / trials, 6), ci_lo=round(lo, 6), ci_hi=round(hi, 6),
               seed=seed, stream='COMPARE', sec=round(dt, 2),
               hx_sha256=C2.BB72['hx_sha'], hz_sha256=C2.BB72['hz_sha'])
    if failbits_dir:
        os.makedirs(failbits_dir, exist_ok=True)
        np.save(os.path.join(failbits_dir, f'{dec_label}_{p}.npy'), fails)
    print(f"  {dec.name:26s} p={p:.3f}: {k:5d}/{trials} "
          f"[{lo:.5f},{hi:.5f}] ({dt:.0f}s)", flush=True)
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--decoders', nargs='+', default=list(C.DECODER_SPECS))
    ap.add_argument('--ps', nargs='+', type=float, default=C.PS_STD)
    ap.add_argument('--trials', type=int, default=C.TRIALS)
    ap.add_argument('--out', default=os.path.join(HERE, 'results', 'comparator_grid.csv'))
    ap.add_argument('--failbits', default=os.path.join(HERE, 'results', 'failbits'))
    ap.add_argument('--procs', type=int, default=3)
    args = ap.parse_args()

    # slow decoders first for better packing
    order = {k: i for i, k in enumerate(
        ['sym_simplex', 'sym_pre_simplex', 'sym_bare', 'sym_bp_simplex',
         'sym_bp_pre_simplex', 'bposd', 'relay'])}
    tasks = [(d, p, args.trials, args.failbits)
             for d in sorted(args.decoders, key=lambda k: order.get(k, 99))
             for p in args.ps]

    t0 = time.time()
    if args.procs > 1 and len(tasks) > 1:
        with Pool(args.procs) as pool:
            rows = pool.map(run_task, tasks)
    else:
        rows = [run_task(t) for t in tasks]

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    os.makedirs(os.path.join(HERE, 'results'), exist_ok=True)
    exists = os.path.exists(args.out)
    with open(args.out, 'a', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if not exists:
            w.writeheader()
        for r in rows:
            w.writerow(r)

    rec = dict(ts=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               decoders=args.decoders, ps=args.ps, trials=args.trials,
               wall_sec=round(time.time() - t0, 1),
               csv_sha256=hashlib.sha256(open(args.out, 'rb').read()).hexdigest(),
               equiv_cert='active_provenance/results/bb72_symatch_equiv_cert.json')
    with open(os.path.join(HERE, 'results', 'run_record_grid.json'), 'w') as f:
        json.dump(rec, f, indent=1)
    print(f"grid done in {time.time()-t0:.0f}s -> {args.out}")


if __name__ == '__main__':
    main()
