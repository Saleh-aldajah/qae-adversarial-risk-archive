# wsc_circuit_v23_reversed_extraction_INVALID.csv — WITHDRAWN

Review finding C01 (QAE v23 Scientific Review, Sec. 3 and App. C): the v23
`wsc_circuit_point.py` built both extraction layers with reversed CNOT
directions (X-checks used data->ancilla, Z-checks ancilla->data), so the
detector error model did not represent BB72 syndrome extraction. Every row
in the renamed CSV is INVALID for its intended interpretation and is retained
only as the reviewed v23 record. The two-qubit parity diagnostic reproducing
the defect is implemented in `comparator/wsc_verify.py` (T1: reversed
primitives return input-independent 0).

Corrected circuit: `comparator/wsc_circuit_point.py` circuit_rev =
'v24-corrected-extraction', verified by `wsc_verify.py` (report:
`results/wsc_verify_report.json`, all four test groups PASS); replacement
data: `results/wsc_circuit.csv` (exp label `wsc_circuit_v24`).
