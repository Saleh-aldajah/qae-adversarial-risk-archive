#!/usr/bin/env python3
"""package_v17.py — build the v17 deliverable bundle:
  QAE_v17_manuscript_FINAL.zip  (tex, bib, bbl, pdf, figures/)
  QAE_v17_archive_FINAL.zip     (v16 archive + comparator/ + active_provenance/ + manifests)
Run after WS-C lands. Idempotent."""
import os, zipfile, hashlib, json, datetime, shutil, subprocess
HERE = os.path.abspath(os.path.dirname(__file__))            # comparator/
ROOT = os.path.dirname(HERE)                                  # qec-work/
M    = os.path.join(ROOT, 'v17-manuscript')
OUT  = '/mnt/agents/output'

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

# --- compile manuscript fresh ---
r = subprocess.run(['tectonic','main_v17.tex'], cwd=M, capture_output=True, text=True)
assert os.path.exists(os.path.join(M,'main_v17.pdf')), r.stdout[-2000:]

# --- manuscript zip ---
mzip = os.path.join(OUT, 'QAE_v17_manuscript_FINAL.zip')
with zipfile.ZipFile(mzip,'w',zipfile.ZIP_DEFLATED) as z:
    for fn in ('main_v17.tex','references.bib','main_v17.bbl','main_v17.pdf'):
        z.write(os.path.join(M,fn), fn)
    for fn in sorted(os.listdir(os.path.join(M,'figures'))):
        z.write(os.path.join(M,'figures',fn), f'figures/{fn}')
print('manuscript zip:', mzip)

# --- archive zip: v16 contents + new workstreams ---
azip = os.path.join(OUT, 'QAE_v17_archive_FINAL.zip')
v16 = os.path.join(ROOT, 'QAE_v16_archive_FINAL.zip')
manifest = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'base': 'QAE_v16_archive_FINAL.zip (48 files, unchanged)',
            'additions': [], 'sha256': {}}
with zipfile.ZipFile(azip,'w',zipfile.ZIP_DEFLATED) as z:
    with zipfile.ZipFile(v16) as z16:
        for item in z16.namelist():
            z.writestr(item, z16.read(item))
    def add(path, arc):
        z.write(path, arc)
        manifest['additions'].append(arc)
        manifest['sha256'][arc] = sha256(path)
    # comparator: code + results + figures
    for fn in ('cmp_common.py','run_grid.py','rescue_simplex.py','assemble_grid.py',
               'analyze_grid.py','comparator_timing.py','kunlun_cmp.py','kunlun_figure.py',
               'wsc_circuit_point.py','wsc_figure.py','landscape_2026.md',
               'ELEVATION_MEMO.md'):
        p = os.path.join(HERE, fn)
        if os.path.exists(p): add(p, f'archive/comparator/{fn}')
    for sub in ('results','figures'):
        d = os.path.join(HERE, sub)
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if os.path.isfile(p) and not fn.endswith('.log'):
                add(p, f'archive/comparator/{sub}/{fn}')
    fb = os.path.join(HERE,'results','failbits')
    for fn in sorted(os.listdir(fb)):
        add(os.path.join(fb,fn), f'archive/comparator/results/failbits/{fn}')
    # active provenance
    ap = os.path.join(ROOT,'active_provenance')
    for sub in ('','results','counts','circuits','backend_snapshots','figures'):
        d = os.path.join(ap,sub)
        if not os.path.isdir(d): continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d,fn)
            if os.path.isfile(p):
                add(p, f'archive/active_provenance/{sub}/{fn}' if sub else f'archive/active_provenance/{fn}')
    # concordance
    add(os.path.join(ROOT,'qa_elevation_concordance.md'), 'archive/qa_elevation_concordance.md')
    z.writestr('archive/v17_additions_manifest.json', json.dumps(manifest, indent=1))
print('archive zip:', azip, '| additions:', len(manifest['additions']))
print('manuscript sha256:', sha256(mzip))
print('archive    sha256:', sha256(azip))
