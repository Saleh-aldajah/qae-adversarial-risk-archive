"""
verify_hashes.py - exact SHA-256 archive verification.
Exits 1 on any missing file, extra path error, or SHA-256 mismatch.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

# v24: manifest lives at the archive root and covers the whole archive/ tree.
ROOT = Path(__file__).resolve().parents[1]
manifest_path = ROOT / "sha256_manifest.json"
manifest = json.load(open(manifest_path))
ok = 0
fails = 0

for rel, info in manifest.items():
    p = (ROOT / rel).resolve()
    try:
        p.relative_to(ROOT.resolve())
    except ValueError:
        print(f"  INVALID PATH OUTSIDE ROOT: {rel}")
        fails += 1
        continue
    if not p.exists():
        print(f"  MISSING: {rel}")
        fails += 1
        continue
    if not p.is_file():
        print(f"  NOT A FILE: {rel}")
        fails += 1
        continue
    actual = hashlib.sha256(p.read_bytes()).hexdigest()
    expected = info["sha256"]
    if actual == expected:
        ok += 1
    else:
        print(f"  HASH MISMATCH: {rel}")
        print(f"    expected: {expected}")
        print(f"    actual:   {actual}")
        fails += 1

print(f"\n{ok} files verified OK, {fails} failures")
if fails:
    print("VERIFICATION FAILED - archive is not reproducible")
    sys.exit(1)
print("All files verified - archive integrity confirmed")
sys.exit(0)
