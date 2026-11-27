# Clara Accord Engine v0.2 — SQLite sandbox

This prototype persists simulated permissions, objection state and single-use effects across process restarts. No live tools or external effects are implemented. Use a new disposable database for this version; no migration from earlier prototypes is provided.

Run from this directory:

```sh
python -m pip install pytest
python -m pytest -q
```

## Controls implemented

- Fixed synthetic action categories; unknown categories denied.
- SHA-256 action identity binds policy version, kind, resource, value and nonce.
- SQLite BEGIN IMMEDIATE transaction serialises approval checks, consumption, simulated effect and audit insertion.
- Unique per-plan effect and durable consumed state prevent replay within the same database, including after restart.
- Random bearer tokens for synthetic accounts; distinct administrator, requester, reviewer and lead roles; secrets stored as digests.
- Pre-registered required reviewer set, designated requester and review lead; expiry and approval revocation.
- Outstanding objections block execution even after their deadline. Assigned lead closure requires fresh approvals. Overdue objections can be listed, not automatically approved.
- Audit records contain event, opaque action digest and time, not raw action payloads or bearer tokens.

## Local evidence

15 pytest cases passed in 1.69 seconds using Python 3.13 and pytest 9.0.2. Thirty-two attempts across four spawned worker processes produced exactly one committed simulated effect. Reopening the database denied replay. Injected audit-write failure rolled back the effect and consumption together. Tests also cover requester binding, assigned review lead, insufficient approval, revoked and expired permission, changed action, invalid token, unknown category, outstanding/overdue objection, fresh approvals after closure and administrative role separation.

Verified published source blob hashes match the locally tested files:
- gate.py: d7262e3a65b22e748bb94c818d1bbc794de49660
- test_gate.py: f9a03c8875bf45216ff5df69718a155bb7729a2e

## Boundaries and residual risks

Bearer-token authentication is synthetic account authentication, not proof of real human identity, competence, independence or informed consent. The administrator is trusted and can enrol identities. There is no network or OS-level isolation, credential rotation/revocation, secure bootstrap provisioning, database tamper protection, backup rollback defence, or hardened clock. The requester must never receive administrative credentials or database access. The audit log is not tamper-evident and has no retention/deletion implementation. Objection closure records a reason category, not independent evidence, and deadline listing is not automatic escalation. Separate roles are enforced in application code, not through an independently deployed service. A real executor cannot be made atomic merely by wrapping an external effect in SQLite; this prototype makes no such claim. It does not implement situational judgement, long-running safe interruption, all twelve technical controls or all 39 ethical scenarios. Do not connect it to real actions or private data.

The charter remains v1.8. All full ethical scenarios and independent validation remain outstanding. Software is MIT-licensed.
