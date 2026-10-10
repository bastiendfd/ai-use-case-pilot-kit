# AI Use-Case Pilot Kit

![Portfolio overview: six fictional AI use cases ranked by weighted score, with the decision, AI Act screening category, 3-year NPV range and review-gate outcomes of each](outputs/portfolio_overview.png)

*The kit in one picture: six fictional use cases, scored, screened against the
EU AI Act, costed, and decided. Rebuilt by `python -m scoring.build_examples`.*

A method, templates and scripts to identify, triage, prioritise, build the
business case for, and track the value of AI use cases in a regulated
industry.

> All examples in this repository are **fictional**. The AI Act triage is a
> structured screening aid, **not legal advice**; final classification needs
> legal or compliance review.

<!-- The full README (what the kit does, quickstart, worked example, repository map, limitations, references, licences) is completed in a later step. -->

## Why I built this

<!-- Bastien writes this section -->

## Open questions

Points of the EU AI Act triage that could not be fully verified against
EUR-Lex or official Commission pages. Each one is marked **TO VERIFY** where
it appears in [`triage/ai_act_triage.md`](triage/ai_act_triage.md).

**Last checked: 2026-10-10**

| # | Open question | Where | Why it matters |
|---|---|---|---|
| 1 | Does a pilot that handles live operational work count as "putting into service" (Article 3(11)), so that the research and testing exclusion of Article 2(8) no longer applies? | Triage, step 2 | Decides whether a pilot already carries AI Act duties. |
| 2 | How broad is the "safety reasons" exception to the ban on inferring emotions in the workplace (Article 5(1)(f)), for example for operator fatigue detection? | Triage, step 3 | The difference between a prohibited practice and an allowed safety tool. |
| 3 | How far does Annex I, Section B, point 20 (Regulation (EU) 2018/1139) reach for manned aircraft products and parts, and which EASA acts will carry the AI Act requirements, and when? | Triage, step 4a | Sets the high-risk route for AI in aviation products. |
| 4 | Have the Commission's guidelines on high-risk classification (draft of 19 May 2026) been finalised, and how do they read the third-party conformity assessment condition of Article 6(1)(b)? | Triage, step 4a | A broad reading would bring more AI in regulated products into high-risk. |
| 5 | At what point does fine-tuning or modifying a general-purpose AI model make a company the provider of a general-purpose AI model (Chapter V)? | Triage, step 7 | Decides whether Article 53 duties apply to the company itself. |
