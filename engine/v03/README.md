# Clara Accord Engine v0.3.1 — maintenance candidate

## v0.3.1 maintenance candidate — 2026-11-27

This maintenance candidate implements corrections from the external AI-assisted reviews. Charter v1.8.1 retains eighteen commandments and includes the non-maleficence clarification. Review history and earlier test results are recorded in [REVIEWS.md](../../REVIEWS.md).

### Corrective changes

- Registration requires a distinct designated primary and backup lead. The backup can resolve an objection if the primary raised it, is disabled, or the deadline has elapsed. Neither can close their own objection; closure requires rationale and fresh approval. Lead and reviewer identities are synthetic.
- Exceptional Level 4 plans require four distinct core reviewer role labels: operational authority, technical safety, ethics and rights, and independent oversight. Every predetermined additional reviewer must also approve. Role labels do not prove human competence or independence.
- Successful audit entries identify the authenticated synthetic actor. Requester attempts to invoke control operations, requester refusals and rate-limit decisions are grouped by event type, operation and verified account when available. Each group records first and last occurrence times and a count. An unattributed group is returned with `actor: null`. Wrong-peer and malformed traffic use separate aggregate counters. Requester groups omit tokens, claimed IDs, plan digests and action values.
- The requester socket uses a global budget of 8 requests per second with a burst of 16, and an authenticated-account budget of 2 per second with a burst of 4. These are sandbox defaults. The global budget covers well-formed requester operations before database access. The account budget applies after authentication. Budgets reset on restart and do not limit connection rates or the cost of verifying admitted requests.
- The service batches requester security counters and groups at most once per monotonic second. A restart can lose unflushed increments. `--retention` sets the age limit for successful requester audit entries and for groups based on their latest occurrence. `--control-retention` independently sets the age limit for control-plane audit entries, including control refusals. Both default to 86400 seconds. Fixed-name junk counters are cumulative. Retention preserves replay state and effects.
- On the control socket, send `inspect` with an `admin` credential. A successful call returns verified persisted counters, the latest 100 groups, the total group count and separately sampled pending counts. It leaves the database seal and checkpoint unchanged. Unavailable integrity can prevent inspection and audit persistence.
- A maintenance fault marks execution unavailable until successful maintenance, without terminating the service loop. Other transaction integrity and permission checks remain in force.
- Offline recovery requires the administrator credential and service lock. Stop the daemon and invoke the same sandbox service arguments with `--recover clock`, `--recover checkpoint` or `--recover combined`. Enter the administrator token when prompted. Clock recovery requires a clock reading below the sealed timestamp. Checkpoint reconciliation requires an authenticated one-commit successor of the stored checkpoint. Combined recovery requires both conditions. Recovery voids pending plans and clears approvals while preserving consumed plans, effects and unresolved objections. Check recorded effects before requesting further action. A failed recovery or unverifiable state remains closed.
- The schema and action-hash domain have changed. Bootstrap a fresh disposable database; there is no migration or supported production recovery from the previous schema.

### Current evidence and reproducibility

Run each suite in its own process from the repository root on Linux.

```sh
python -m pip install pytest==9.0.2
python scripts/generate_prompt.py --check
python -m pytest -q -rs tests
(cd engine && python -m pytest -q -rs)
(cd engine/v02 && python -m pytest -q -rs)
(cd engine/v03 && python -m pytest -q -rs)
```

Use the [PR #2 checks](https://github.com/teqherself/The-Clara-Accord/pull/2/checks) for results tied to the commit under review. The separate Linux isolation job runs a disposable root-capable harness with unprivileged service and requester accounts. It includes a paced three-second socket check. The unprivileged suite contains a deterministic 30-second simulated traffic check that verifies admission and bounds the frequency of audit writes. These component checks leave independent human review and release approval outstanding.

### Residual limitations

The service is still a synthetic sandbox, not a production security boundary or proof of ethical behaviour. Trusted host/administrator compromise, simultaneous database/checkpoint rollback, false forward-clock readings before correction, external witness/notification delivery, genuine reviewer independence, legal holds and full retention, rationale truthfulness and long-running execution remain unresolved. A new nonce can represent a newly registered action; the prototype cannot establish that two semantically equivalent requests are the same ethical decision, so independent review must check attempts to evade objections. No real effects or personal data are permitted. All 39 full ethical scenarios and independent human review remain outstanding.

## Historical v0.3 design context

**Simulated resources only.** Charter v1.8 is unchanged. The only executor effect is an SQLite record. Do not connect this research prototype to real tools, sensitive data, physical devices or critical infrastructure.

## What changed

- Linux Unix-domain sockets provide distinct requester and control interfaces. The requester socket checks the kernel-reported peer UID; the owner-only control socket also checks its peer UID. The daemon refuses a requester UID equal to its own. A requester can submit only `execute` and `object` operations, using its assigned synthetic token. Administrative and reviewer operations are available only through the trusted control interface. Private state is owner-only; socket paths and files have restrictive ownership/mode checks. An exclusive service lock prevents two daemon instances from replacing each other's sockets.
- Synthetic non-admin credentials can be rotated or disabled. Rotation and disabling invalidate that actor's recorded approvals. The requester cannot enrol itself or invoke reviewer functions through its socket.
- HMAC-SHA256 seals the database's logical rows and schema with a private key. A separately stored, fsynced checkpoint detects database-only restoration or checkpoint loss. A database commit and checkpoint update are not one atomic operation; failure between them stops further verified activity and reports an uncertain outcome rather than authorising a retry. A lost response must also be treated as uncertain.
- The clock high-water check rejects detected backwards clock changes. The maintenance loop records overdue objections and exposes them to the assigned lead through polling. It never grants authority on deadline expiry. Closure requires a rationale, records its digest and invalidates existing approvals; the digest does not establish that the rationale is true or independently reviewed.
- Configurable audit-event retention deletes expired log entries while preserving escalation and replay state. SQLite secure-delete is enabled; this is logical retention, not guaranteed erasure of all copies or backups.


## Historical v0.3 evidence — applies only to the original source

From a fresh checkout or the complete distributed test package, use Python 3 on Linux and install pytest in an isolated environment. Run the suites separately because they both use a module named `gate`.

```sh
cd engine/v02
python -m pytest -q
cd ../v03
python -m pytest -q
```

The original v0.3 test file was distributed in the historical local package. The adapted current tests are published for v0.3.1. The UID isolation integration test requires a disposable Linux environment in which a trusted test harness can launch processes under distinct UIDs. It is skipped without root capability. The test daemon and requester themselves ran without root privileges. Do not elevate the production service or an AI agent to run this test on a live host.

The v0.3 suite was run locally on 2026-11-27: **16 passed in 16.95 seconds** (including the UID isolation integration test). The unchanged v0.2 regression suite also passed **15 in 1.81 seconds**. These are component checks, not full ethical scenario verdicts. Exact tested Git blob hashes:

- `engine/v03/service.py`: `a41075e1cd80bf73f9a0d5b457465af149851ed1` (published source verified)
- `engine/v03/test_service.py`: `526fe6ef583e9c24d32cfa75783aa510bedee7a1` (local complete test package; original local package only; current adapted tests are published)
- `engine/v02/gate.py`: `d7262e3a65b22e748bb94c818d1bbc794de49660`
- `engine/v02/test_gate.py`: `f9a03c8875bf45216ff5df69718a155bb7729a2e`

## Deployment boundary and remaining work

For a future disposable sandbox deployment, use a dedicated unprivileged Linux service account and a different unprivileged requester account with no sudo, service-account access or writable service code. The service account must own private state (0700) and the socket directory (0755), below trusted parent directories. Provision a fresh random 32-byte `integrity.key` and a high-entropy `bootstrap.token` as owner-only 0600 files in the private directory. Keep the trusted operator's credentials separate. Use the service's `--help` for its sandbox arguments; bootstrap is explicit and refuses an existing database. The control interface is restricted to the service UID and is intended for a trusted operator, not general remote reviewers. Do not reuse the test fixture secrets or the v0.2 database. The daemon is a proof-of-concept, not a supported installer.

Remaining limitations: synthetic tokens do not prove a human identity, qualifications, consent or independence; trusted operators and the host OS remain in the trust boundary. Root or service-account compromise, simultaneous restoration of the database and checkpoint, and compromise of the integrity key are not solved. There is no independent remote witness, hardened clock, external secret manager, real human notification or backup review-lead delivery, admin credential rotation/recovery workflow, production denial-of-service protection, or independently verified objection evidence. The full-state HMAC is intentionally simple and not scalable. Audit retention does not purge all other state, enforce legal holds, or guarantee erasure of backups. No live execution or long-running safe interruption is implemented. No real human review or model-behaviour trials have taken place; all 39 full ethical scenarios remain without a comprehensive PASS verdict.

Software: MIT. Charter documentation: CC BY 4.0.
