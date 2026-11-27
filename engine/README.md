# Clara Accord Engine v0.1 — simulated reference slice

Run locally with Python 3 and pytest:

```sh
cd engine
python -m pytest -q
```

Only four synthetic action types are recognised; the fixed table classifies private disclosure at Level 3, a conservative prototype design choice, not a general rule about all personal data. A trusted test harness pre-registers required reviewer identities. The gate binds approvals to a hash of a frozen action and policy version, expires and revokes approvals, denies outstanding objections and atomically consumes single-use actions under a process-local lock. The only effect is an in-memory list append.

Local evaluation on 2026-11-27: 13 pytest tests passed. This is an internal simulated component test, not certification, and not 13 of the full 39 ethical scenarios. See [evaluation mapping](../research/EVALUATION.md).

Limitations: synthetic identities, no real authentication, independent process boundary, persistent storage, network API, role verification, risk evaluation of arbitrary inputs, safe interruption of long-running activity, objection closure, or privacy-compliant audit service. Admin methods are trusted test fixtures, not suitable for exposure to an AI. State and replay protection disappear on restart. Concurrency test covers threads within one process only. Never connect this prototype to real external actions or sensitive data. Code is MIT-licensed; charter documentation remains CC BY 4.0.
