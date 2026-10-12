#!/usr/bin/env python3
"""package_v18.py — build the v18 deliverable bundles:
  QAE_v18_manuscript_FINAL.zip  (v18 tex/bib/bbl/pdf + figures + cover letter)
  QAE_v18_archive_FINAL.zip     (v17 archive + theory_test/ + v18-theory/ + EVALUATION)
Idempotent."""
import os, zipfile, hashlib, json, datetime
HERE = os.path.abspath(os.path.dirname(__file__))            # comparator/
ROOT = os.path.dirname(HERE)                                  # qec-work/
M    = os.path.join(ROOT, 'v17-manuscript')
OUT  = '/mnt/agents/output'

def sha256(p):
    h = hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

# --- manuscript zip ---
mzip = os.path.join(OUT, 'QAE_v18_manuscript_FINAL.zip')
with zipfile.ZipFile(mzip,'w',zipfile.ZIP_DEFLATED) as z:
    for fn in ('main_v18.tex','references.bib','main_v18.bbl','main_v18.pdf',
               'cover_letter_npjQI.tex','cover_letter_npjQI.pdf'):
        z.write(os.path.join(M,fn), fn)
    for fn in sorted(os.listdir(os.path.join(M,'figures'))):
        z.write(os.path.join(M,'figures',fn), f'figures/{fn}')
print('manuscript zip:', mzip)

# --- archive zip: v17 archive + theory test + formalization + evaluation ---
azip = os.path.join(OUT, 'QAE_v18_archive_FINAL.zip')
v17 = os.path.join(OUT, 'QAE_v17_archive_FINAL.zip')
manifest = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'base': 'QAE_v17_archive_FINAL.zip (206 files, unchanged)',
            'additions': [], 'sha256': {}}
with zipfile.ZipFile(azip,'w',zipfile.ZIP_DEFLATED) as z:
    with zipfile.ZipFile(v17) as z17:
        for item in z17.namelist():
            z.writestr(item, z17.read(item))
    def add(path, arc):
        z.write(path, arc)
        manifest['additions'].append(arc)
        manifest['sha256'][arc] = sha256(path)
    # theory test campaign
    tt = os.path.join(ROOT, 'theory_test')
    for sub in ('','predictions','results','counts','circuits','backend_snapshots'):
        d = os.path.join(tt, sub)
        if not os.path.isdir(d): continue
        for fn in sorted(os.listdir(d)):
            p = os.path.join(d, fn)
            if os.path.isfile(p) and not fn.endswith('.log'):
                add(p, f'archive/theory_test/{sub}/{fn}' if sub else f'archive/theory_test/{fn}')
    # formalization fragment + evaluation
    add(os.path.join(ROOT,'v18-theory','theory_injection_game.tex'),
        'archive/v18-theory/theory_injection_game.tex')
    add(os.path.join(ROOT,'EVALUATION_v17.md'), 'archive/EVALUATION_v17.md')
    z.writestr('archive/v18_additions_manifest.json', json.dumps(manifest, indent=1))
print('archive zip:', azip, '| additions:', len(manifest['additions']))
print('manuscript sha256:', sha256(mzip))
print('archive    sha256:', sha256(azip))
