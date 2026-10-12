# QAE V16 Refurbishment Notes

V16 is a synchronization and claim-discipline patch over V15. No numerical CSV values were changed except deterministic regeneration of analytic/certificate files by their own verification scripts.

## Main changes

1. Added `Dockerfile` and `Makefile` for cleaner reproduction.
2. Added `reproduce_fast.py` for deterministic fast validation.
3. Added `validate_seed_consistency.py` to verify SHA-256 seed policy across archived CSVs.
4. Added `validate_table_shapes.py` to verify row counts and full SHA-256 matrix hashes.
5. Rebuilt `README_REPRODUCE.md` with correct command order and clearer scope boundaries.
6. Rebuilt `verify_hashes.py` to use exact manifest paths rather than basename fallbacks.
7. Revised manuscript language:
   - DOI is treated as reserved/prepared, not active until public record resolution.
   - UF-BFS is described as a graphified baseline, not hyperedge-aware.
   - MWPM/UF claims are limited to tested graphified baselines.
   - Hardware results are hardware-noise-model sensitivity evidence, not compiled-circuit or real-device causality.
   - Claim-to-evidence map was reformatted to remove page overlap.
8. Updated QEC Emulator metadata/docs to v1.2.4 with numerical algorithms unchanged relative to the submitted V15 data.
