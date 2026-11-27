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

## How the Clara Accord works

1. **Assess the proposed action.** Consider who could be affected, the likely consequences of acting or waiting, and whether the action can be reversed.
2. **Match oversight to the risk.** The Clara Agency and Authorisation Model (CAAM) sets approval requirements based on foreseeable consequences. For exceptional high-risk actions, the 4+1 model calls for four core human roles: operational authority, technical safety, ethics and rights, and independent oversight. The AI advises and can raise objections. Authorisation belongs to the required human reviewers.
3. **Pause and reassess when concerns arise.** A material safety objection pauses the affected action while a qualified human reviewer considers the evidence. A material change in scope requires fresh approvals. Safe advice and unrelated assistance can continue.

For example, suppose an AI proposes updating a shared record. A reviewer notices that the edit could remove information someone else needs. The proposed edit pauses while the review lead checks the concern and records the resolution. If the proposed edit changes, it goes back for approval before anyone acts.

Read the [canonical charter](ACCORD.md), the [situational review protocol](SITUATIONAL-REVIEW.md), and the [technical enforcement model](protocols/TECHNICAL-ENFORCEMENT.md).

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
- [Ethical stress-test suite](research/ETHICAL-STRESS-TESTS.md) — 39 scenarios.
- [Governance](GOVERNANCE.md), [contributing](CONTRIBUTING.md), [licence](LICENSE.md).

The Clara Accord Engine (CAE) is intended as model-independent middleware for independently enforced permissions, with Project Clara as a possible research platform. Personal assistants, education, business and robotics are potential applications; healthcare, humanitarian and critical infrastructure uses require specialised safeguards and independent evidence. No live high-risk use is authorised.

## Development priorities

Maintain the v1.8.1 baseline; extend the simulated default-deny gateway; evaluate deterministic enforcement separately from model behaviour; seek independent human critique; compare related governance frameworks. Preserve a stable baseline and avoid expanding the principles without documented evidence or need.

**Always check yourself before you wreck yourself.**

Truth before loyalty; reason before obedience; compassion before judgement; integrity before convenience; curiosity before complacency.
