"""
gen_manifest.py  —  Build sha256_manifest.json over the v17 tree.

B9 fix: the manifest tracks INPUTS only — code, input/reference data, and
hand-written documentation. Generated reports and build artifacts are
excluded:
  - data/bb72_certificate_report.json  (rewritten by verify_certificate.py)
  - figures/*                          (rendered artifacts)
  - __pycache__, logs
The Monte-Carlo CSVs ARE tracked: they are the archive's primary evidence
and regenerate deterministically (verified byte-identical in the v16 audit).

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
import hashlib, json
from pathlib import Path

# v24: manifest scope widened from qae_experiments/ to the whole archive/
# tree so the comparator (WSC), theory_test_consol (stochastic reanalysis),
# and active_provenance evidence are pinned by the same manifest.
ROOT = Path(__file__).resolve().parents[1]

EXCLUDE = {
    'sha256_manifest.json',
    'qae_experiments/data/bb72_certificate_report.json',  # B9: generated report
}
EXCLUDE_DIRS = {'__pycache__', 'figures', 'logs'}

manifest = {}
for p in sorted(ROOT.rglob('*')):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if rel in EXCLUDE:
        continue
    if any(part in EXCLUDE_DIRS for part in p.relative_to(ROOT).parts):
        continue
    manifest[rel] = {
        'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
        'bytes': p.stat().st_size,
    }

with open(ROOT / 'sha256_manifest.json', 'w') as f:
    json.dump(manifest, f, indent=2, sort_keys=True)
print(f"manifest written: {len(manifest)} files")
for k in manifest:
    print(f"  {k}")
