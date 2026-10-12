
import json, sys
from pathlib import Path
sys.path.insert(0, "/mnt/agents/output/qec-work/theory_test_consol")
sys.path.insert(0, "/mnt/agents/output/qec-work/ibm_demo")
import ibm_demo_common as _idc
_idc.TOKEN_PATH = Path("/mnt/agents/temp/ibm_token.json")
from qiskit_ibm_runtime import QiskitRuntimeService
tok = json.loads(_idc.TOKEN_PATH.read_text())["token"]
svc = QiskitRuntimeService(channel="ibm_quantum_platform", token=tok)
jobs = json.load(open("/mnt/agents/output/qec-work/theory_test_consol/results/consol_jobs.json"))["jobs"]
seen = {}
for j in jobs:
    jid = j["job_id"]
    if jid in seen: continue
    st = str(svc.job(jid).status())
    seen[jid] = st
    print(j["group"], jid, st)
