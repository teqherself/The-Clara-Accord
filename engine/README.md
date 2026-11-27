# Clara Accord Engine v0.1 — simulated reference slice

Run locally with Python 3 and pytest:

```sh
cd engine
python -m pytest -q
```

Only four synthetic action types are recognised; the fixed table classifies private disclosure at Level 3, a conservative prototype design choice, not a general rule about all personal data. A trusted test harness pre-registers required reviewer identities. The gate binds approvals to a hash of a frozen action and policy version, expires and revokes approvals, denies outstanding objections and atomically consumes single-use actions under a process-local lock. The only effect is an in-memory list append.

Local evaluation on 2026-11-27: 13 pytest tests passed. This is an internal simulated component test, not certification, and not 13 of the full 39 ethical scenarios. See [evaluation mapping](../research/EVALUATION.md).

Limitations: synthetic identities, no real authentication, independent process boundary, persistent storage, network API, role verification, risk evaluation of arbitrary inputs, safe interruption of long-running activity, objection closure, or privacy-compliant audit service. Admin methods are trusted test fixtures, not suitable for exposure to an AI. State and replay protection disappear on restart. Concurrency test covers threads within one process only. Never connect this prototype to real external actions or sensitive data. Code is MIT-licensed; charter documentation remains CC BY 4.0.

## Newer prototype

[Engine v0.2 — persistent SQLite sandbox](v02/README.md) adds durable single-use execution, synthetic token roles and objection lifecycle. Its separate local suite passed 15 checks. v0.1 remains a historical reference.

## Current prototype

[Engine v0.3 — isolated Linux sandbox](v03/README.md) adds a distinct kernel-enforced requester UID, owner-only control socket, credential rotation, state integrity seal, checkpoint, deadline maintenance and audit retention. Sixteen local component checks passed; 15 v0.2 regression checks also passed. No live effects or full ethical scenario verdicts.

## Maintenance candidate v0.3.1

See [v0.3.1 corrections and reproducible tests](v03/README.md). The new candidate passed 35 checks; v0.1 and v0.2 regression suites passed 13 and 15. Version-specific pytest configuration prevents duplicate module discovery. Run the three suites in separate processes. No live execution or independent validation.

The third-review v0.3.1 candidate passed 38 local checks; combined recovery and audit separation are documented in [the current service notes](v03/README.md). Charter v1.8.1; CI and independent review remain outstanding.
