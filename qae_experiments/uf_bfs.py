"""
uf_bfs.py  —  UF-BFS decoder (union-find-style BFS pairing on the
graphified detector graph), factored out of run_single_round_only.py
so E0/E2 can share one implementation. Logic unchanged from v16.

Author: Dr. Saleh H. AlDaajeh  ORCID: 0000-0001-7810-9290
"""
from collections import deque


def build_adj(H, n, n2):
    adj = [[] for _ in range(n2)]
    for j in range(n):
        chk = [i for i in range(n2) if H[i, j]]
        if len(chk) == 2:
            a, b = chk
            adj[a].append((j, b)); adj[b].append((j, a))
        elif len(chk) == 1:
            adj[chk[0]].append((j, -1))
        else:
            for k in range(len(chk) - 1):
                a, b = chk[k], chk[k + 1]
                adj[a].append((j, b)); adj[b].append((j, a))
    return adj


def uf_decode(adj, syn_int, n2):
    active = [i for i in range(n2) if (syn_int >> i) & 1]
    if not active:
        return 0
    matched = set(); correction = 0
    for src in active:
        if src in matched:
            continue
        d = {src: 0}; par = {src: None}; q = deque([src]); found = None
        while q and found is None:
            node = q.popleft()
            for (qubit, nbr) in adj[node]:
                tgt = nbr if nbr >= 0 else n2
                if tgt not in d:
                    d[tgt] = d[node] + 1; par[tgt] = (node, qubit); q.append(tgt)
                    if tgt in active and tgt not in matched and tgt != src:
                        found = tgt; break
        if found is not None:
            matched.add(src); matched.add(found); node = found
            while par.get(node):
                prev, q2 = par[node]; correction ^= (1 << q2); node = prev
    return correction
