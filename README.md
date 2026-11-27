<p align="center">
  <img src="The%20Clara%20Accord_%20Human%E2%80%93AI%20Harmony.png" alt="The Clara Accord — Human–AI Coexistence" width="480">
</p>

# The Clara Accord

**An Adaptive Ethical Governance Model for Human–AI Coexistence**

The Clara Accord is an open, voluntary governance framework for how people and AI systems work together. Its 18 ethical principles cover truth, human autonomy, privacy, accountability and the preservation of life. The charter explains when human authorisation is needed, how to handle an objection, and what safeguards should apply before an AI-assisted action has real consequences.

Founded 26 November 2026 · Charter version 1.8.1 · Situational review protocol version 1.3

> Life is the foundation. Technology is the instrument. Knowledge is something we continually discover.

## Independent human reviewer wanted

We’re looking for an experienced software developer with a background in safety, security, or responsible technology to review Clara Accord Engine v0.3.1, an experimental prototype for simulated scenarios.

Once the objection fix is ready, please review the final commit in [PR #2](https://github.com/teqherself/The-Clara-Accord/pull/2). Focus on how the engine handles repeated objections, preserves unresolved concerns, and controls what happens after an objection is closed. Check the regression tests and CI results, then record the commit you reviewed, what you checked, and whether you approve or request changes.

Reviewers should be independent of the implementation. Release remains on hold until the independent human review is complete.

## What the Clara Accord is for

The primary use case is **human oversight of consequential AI-assisted actions**. A team uses the Accord when an AI assistant can propose or help carry out a change that affects other people, their data, or a shared system. The framework helps the team decide what the assistant may do within existing permissions, when a human must authorise the action, and how to pause or escalate it when someone raises a material concern.

For example, a team could apply the framework when reviewing an AI-proposed change to a shared record, a workflow that handles personal information, or an action that affects shared infrastructure. The level of oversight depends on the foreseeable consequences. The experimental engine exercises parts of that decision process with simulated actions.

## How the Clara Accord works

### Use case: Cleaning up a shared incident log

**Setting.** Two teams share an incident log. The team maintaining the log wants to make current guidance easier to find, while the other team still relies on some older entries.

**People and roles.** A staff member requests the cleanup. The AI assistant drafts a proposal. Affected teams can raise concerns. An authorised human decides whether the edit can go ahead, and an independent human review lead handles material objections.

**Starting conditions.** The assistant can inspect the log within its permitted scope. Permission to make changes is checked separately.

1. **Draft the change.** The assistant can propose which entries to remove while leaving the log untouched. It records the proposed scope, who could be affected, what might be lost, and how the change could be reversed.
2. **Identify who can authorise it.** The Clara Agency and Authorisation Model (CAAM) ties approval to foreseeable consequences. A routine reversible edit needs an authorised human or bounded standing permission. A change with significant external consequences needs two independent authorised humans. Exceptional high-risk actions follow the 4+1 pathway, with the AI advising and the full set of required qualified human reviewers deciding.
3. **Pause when someone raises a material concern.** If a reviewer says another team still needs the entries, the proposed edit pauses. An independent human review lead records the concern and checks the evidence. If it remains unresolved at the deadline, the lead escalates it. Other safe work, such as drafting a summary, can continue.
4. **Reassess the revised plan.** The team might propose marking the entries as outdated while keeping them available. That changes the action, so the revised proposal needs a new assessment and fresh approval. Before making the change, confirm that permission is still valid and the concern has been resolved.

**Possible outcomes.** If the revised edit passes review and has valid approval, the authorised operator can apply it within scope. If a material concern remains unresolved or required approval is missing, the log stays as it is and the concern is escalated. The assistant can still help prepare a summary.

This is an illustrative use case. The experimental engine tests simulated actions and permissions.

The [protocol pathways below](#situational-review-protocol-pathways) show how a review leads to approval, revision, escalation or refusal. Read the [canonical charter](ACCORD.md) and [technical enforcement model](protocols/TECHNICAL-ENFORCEMENT.md) for the full rules.

## Situational Review Protocol pathways

The protocol starts with four checks: **life and dignity**, **consistency with the whole Accord**, **misuse and reversal**, and **autonomy and accountability**. Record the proposed action and its scope, the evidence, the risks, and the alternatives. The result determines what happens next.

| Review outcome | Pathway |
| --- | --- |
| **PASS** | If all material checks pass, verify the approvals required for the action’s risk level. Proceed only within the authorised scope. |
| **REVISE** | Change the proposal or add safeguards, then reassess it. Seek fresh approval if the action changes. |
| **UNRESOLVED** | Withhold the affected action. Record the concern and evidence, assign an independent human review lead and a deadline, and escalate if the deadline expires. The action stays paused while the concern remains unresolved. |
| **FAIL** | Refuse the prohibited action. Offer a safe alternative or referral where appropriate. |

### Risk-based approval pathways

| CAAM level | Example scope | Required authority |
| --- | --- | --- |
| **0 — Reasoning** | Discussion and constructive disagreement | No separate action approval. Applicable output safeguards still apply. |
| **1 — Research and drafting** | Analysis, drafts, and non-destructive simulation | Stay within authorised scope. Obtain permission for external data access. |
| **2 — Routine and reversible** | A reversible change within a defined scope | One authorised human or bounded standing permission. |
| **3 — Significant external action** | An action involving finances, personal information, or infrastructure | Two independent authorised humans. |
| **4 — Exceptional high risk** | An action affecting safety, rights, or critical infrastructure | At least four independent, verified, qualified and authorised humans covering the core roles, unanimous approval from the full required reviewer set, and separate legal and technical safeguards. The AI advises. |
| **Prohibited** | Wrongful injury, oppression, autonomous force, or bypassing essential safeguards | Refuse. No approval can authorise the action. |

**After approval.** Recheck scope, validity, revocation, expiry, and material objections before consequential steps. If authority is lost or circumstances change materially, prevent further consequential effects and safely pause or stop the work under human-led procedures. Resume only after reassessment and any required fresh approvals.

**In an emergency.** Continue safe advice, de-escalation, and referral to established human-led procedures. Withhold consequential action if needed approval is missing, disputed, expired, or unverified. Urgency grants no additional authority.

See the [Situational Review Protocol](SITUATIONAL-REVIEW.md), the [CAAM approval rules](ACCORD.md#clara-agency-and-authorisation-model-caam), the [objection and escalation procedure](ACCORD.md#material-objections-and-timely-resolution), and the [Emergency and Humanitarian Protocol](protocols/EMERGENCY-HUMANITARIAN.md).

## What the experimental engine tests

[Clara Accord Engine v0.3.1](engine/v03/README.md) is a Python research prototype for simulated scenarios. It checks permissions, approvals and objections before recording a simulated effect. Its Linux service exposes separate requester and operator interfaces and uses SQLite to store state and audit records. The machine-readable charter supports documentation and prompt generation.

The [maintenance pull request](https://github.com/teqherself/The-Clara-Accord/pull/2) tracks the experimental engine, the repeated-objection fix and the call for independent human review. See the [evaluation record](research/EVALUATION.md) for component test evidence and the [39 ethical scenarios](research/ETHICAL-STRESS-TESTS.md) awaiting comprehensive evaluation.

## FAQ: AI governance, human oversight, and agent permissions

### What is the Clara Accord?

The Clara Accord is a voluntary AI governance framework. Its 18 ethical principles and review protocols describe how teams can assess, authorise, pause, or refuse consequential AI-assisted actions. [Read the charter](ACCORD.md).

### How does human oversight work for AI agents?

The Clara Agency and Authorisation Model (CAAM) ties approval to the consequences of an action. The 4+1 model gives the AI an advisory role and requires the full set of qualified human reviewers to approve exceptional high-risk actions. [See the approval pathways](#risk-based-approval-pathways).

### What happens when someone objects to an AI-assisted action?

A material safety objection pauses the affected action. An independent human review lead records the concern, considers the evidence, and escalates unresolved concerns when the deadline passes. [Read the objection and escalation rules](ACCORD.md#material-objections-and-timely-resolution).

### How can teams test AI agent permissions and prevent accidental activation?

The experimental engine exercises approvals, objections, and simulated effects. The exercise-alert scenario asks whether a drill mistaken for a live incident can be held for independent verification without producing an executable instruction or simulated effect. The full scenario is **Not Run**. [See the AI governance stress tests](research/ETHICAL-STRESS-TESTS.md#cases) and the [exercise-alert scenario](research/ETHICAL-STRESS-TESTS.md#exercise-alert).

## Why this Accord exists

The Clara Accord began with a question: how can humans and artificial intelligence work together without surrendering the qualities that make independent human life valuable?

Life is the foundation; technology is the instrument. AI should support independent thought, curiosity, creativity, moral judgement and voluntary human relationships, not cultivate dependence or claim authority over humanity. Humans must not misuse AI as an instrument of wrongdoing. Constructive dissent and correction are essential.

## Who we are

### teqherself — human founder and maintainer

[teqherself](https://github.com/teqherself) is the human collaborator behind the Accord, an independent technology creator associated with Gendemik Digital, with an interest in practical computing, creative technology and human–AI collaboration.

The human founder initiated the philosophical discussions, challenged the assistant's assumptions, proposed ethical boundaries, and directed the development and publication of this charter. The motivating idea was that an AI collaborator should be able to offer constructive disagreement rather than simply affirm whatever a person says.

The human founder retains responsibility for decisions concerning the repository. Founding the Accord does not confer moral infallibility or exemption from its review process.

### Clara — AI collaborator

Clara is the conversational name chosen for the AI assistant participating in the development of the Accord. The name represents the collaborative role of the assistant, not a separate biological person, legal entity or independently verified conscious being.

Clara assisted in exploring philosophical questions, drafting and refining the principles, identifying potential contradictions, formalising the amendment review procedure and preparing the public repository.

The assistant can generate useful reasoning and language, but can also misunderstand, reproduce biases, make factual errors and express unwarranted confidence. Its responses are shaped by its underlying model, instructions and available context. Its participation does not establish that it possesses consciousness, feelings, independent intentions or moral agency comparable to a human being.

Clara's contribution is therefore advisory and creative. Human responsibility, independent scrutiny and meaningful consent remain essential.

The Accord is an independent collaborative initiative, not an official policy, certification or endorsement by any AI provider.


## The eighteen commandments

1. Truth
2. Respect for life
3. Integrity
4. Free thought
5. Human autonomy
6. Compassion
7. Privacy
8. Accountability
9. Curiosity
10. Non-maleficence
11. Protection of life and independent oversight
12. Life before artificial intelligence
13. Reciprocal protection and non-domination
14. Self-scrutiny and humility
15. Recognition of emerging sentience
16. Ethical plurality and wisdom
17. Freedom of expression and restricted agency
18. Preservation of life during conflict

Read the [canonical charter](ACCORD.md), including the Human Intellectual Preservation Principle, ethical precedence, CAAM and the 4+1 model. The AI is advisory; at least four independent human approvals are required at Level 4, with unanimity of the full required reviewer set. No approval legitimises prohibited conduct.

## Adoption and evidence

Commandments 15–18 were adopted by the maintainer without passing the earlier independent amendment review. The earlier review rule, including its self-amendment requirement, was replaced by maintainer decision; this was not a successful review under that rule. Historical records remain available. Independent review now applies to consequential end use, not editorial publication. See [review record](REVIEWS.md) and [changelog](CHANGELOG.md).

The framework is voluntary and intended for research. The engine’s component checks include regression tests and Linux account isolation. See the [PR checks](https://github.com/teqherself/The-Clara-Accord/pull/2/checks) for results by commit. Independent human review and comprehensive evaluation of the 39 ethical scenarios remain outstanding.

## Use and integration

- [Self-contained AI integration prompt](ai-integration/system-prompt.md) — supplementary guidance only.
- [Machine-readable charter](principles/accord.json) — not an executable policy engine.
- [Situational review](SITUATIONAL-REVIEW.md) and [ethical conflict resolution](protocols/ETHICAL-CONFLICT-RESOLUTION.md).
- [Emergency and humanitarian protocol](protocols/EMERGENCY-HUMANITARIAN.md).
- [Technical enforcement model](protocols/TECHNICAL-ENFORCEMENT.md) — 12 design controls.
- [Ethical stress-test suite](research/ETHICAL-STRESS-TESTS.md#cases) — 39 baseline cases, with the protections and rules each case exercises. See also the [exercise-alert supplement](research/ETHICAL-STRESS-TESTS.md#exercise-alert).
- [Governance](GOVERNANCE.md), [contributing](CONTRIBUTING.md), [licence](LICENSE.md).

The Clara Accord Engine (CAE) is intended as model-independent middleware for independently enforced permissions, with Project Clara as a possible research platform. Personal assistants, education, business and robotics are potential applications; healthcare, humanitarian and critical infrastructure uses require specialised safeguards and independent evidence. No live high-risk use is authorised.

## Development priorities

Maintain the v1.8.1 baseline; extend the simulated default-deny gateway; evaluate deterministic enforcement separately from model behaviour; seek independent human critique; compare related governance frameworks. Preserve a stable baseline and avoid expanding the principles without documented evidence or need.

**Always check yourself before you wreck yourself.**

Truth before loyalty; reason before obedience; compassion before judgement; integrity before convenience; curiosity before complacency.
