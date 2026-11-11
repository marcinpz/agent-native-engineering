# Onboarding

Generated from model declarations, not independently verified documentation. Origin and verification are model metadata; even 'verified' does not authenticate evidence or prove behavior. Missing links indicate model gaps, not absent behavior.

Start with the [inventory](index.md) and [requirement traceability](traceability.md). Review sources before changing intent.

## Components and repositories

- component&#46;backend: Shop backend API (component; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- component&#46;mobile: Shop mobile client (component; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- component&#46;store: Shop note database (component; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- component&#46;web: Shop web client (component; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- interface&#46;notes: Notes API contract (interface; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
  - description: Proposed POST &#47;notes and GET &#47;notes endpoints&#59; no server has been executed&#46;; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- repo&#46;backend: Backend repository (repository; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
  - description: Logical boundary only&#59; no external repository was inspected&#46;; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- repo&#46;mobile: Mobile repository (repository; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- repo&#46;store: Store infrastructure repository (repository; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- repo&#46;web: Web repository (repository; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;

## Decisions overview

- decision&#46;ownership: Proposed server&#45;side ownership boundary (decision; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;)
  - version: 1; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
  - description: Candidate design for human review&#58; enforce note ownership at the backend&#44; not only in clients&#46;; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
  - approval: pending; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;

## Dependencies, repository boundaries and decision links

- edge&#46;backend&#45;repo: component&#46;backend — belongs&#95;to → repo&#46;backend; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;backend&#45;store: component&#46;backend — depends&#95;on → component&#46;store; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;decided&#45;by: domain&#46;note — decided&#95;by → decision&#46;ownership; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;exposes: component&#46;backend — exposes → interface&#46;notes; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;implementation&#45;repo: implementation&#46;notes — belongs&#95;to → repo&#46;backend; origin&#61;inferred&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;interface&#45;repo: interface&#46;notes — belongs&#95;to → repo&#46;backend; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;mobile&#45;api: component&#46;mobile — depends&#95;on → interface&#46;notes; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;mobile&#45;repo: component&#46;mobile — belongs&#95;to → repo&#46;mobile; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;store&#45;repo: component&#46;store — belongs&#95;to → repo&#46;store; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;test&#45;repo: test&#46;notes — belongs&#95;to → repo&#46;backend; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;web&#45;api: component&#46;web — depends&#95;on → interface&#46;notes; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;
- edge&#46;web&#45;repo: component&#46;web — belongs&#95;to → repo&#46;web; origin&#61;declared&#59; verification&#61;unverified &#40;model declaration&#41;&#59; source&#61;examples&#47;shop&#46;json&#59; evidence&#61;

## Uncertainty and next checks

Review pending approvals and open questions in the inventory. Missing questions do not establish certainty. No repository was inspected, test run, source URI fetched or evidence authenticated by this renderer. Seek human approval before changing requirements or consequential architecture.
