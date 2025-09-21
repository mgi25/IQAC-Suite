# AI Text Generation Field Map

This guide lists every text area that currently exposes an “Generate with AI” control in the Submit Proposal and Event Report flows. For each field the table captures the DOM identifier, the intended backend endpoint, and the proposal/report data that should be sent to the model when composing the prompt. The field requirements are taken from the existing `suite/field_config` JSON definitions and from the data payloads exported to the frontend.

## Submit Proposal – “Why this event?” section

The modern proposal dashboard renders three AI-enabled textareas inside the *Why this event?* step of the wizard: **Need Analysis**, **Objectives**, and **Expected Learning Outcomes**.【F:emt/static/emt/js/proposal_dashboard.js†L1786-L1817】 The `suite` app already exposes helpers that describe which proposal facts must be supplied to each AI task.【F:suite/field_config/why_event.json†L1-L13】【F:suite/field_config/need_analysis.json†L1-L9】【F:suite/field_config/objectives.json†L1-L8】【F:suite/field_config/learning_outcomes.json†L1-L10】 All form values referenced below are collected through `collect_basic_facts`, which normalises organization, schedule, audience, POS/PSO and SDG selections from the proposal form submission.【F:suite/facts.py†L5-L58】

| UI Field (ID) | Endpoint | Required context fields |
| --- | --- | --- |
| Need Analysis (`need-analysis-modern`) | `suite:generate_why_event` (primary) or `suite:generate_need_analysis` fallback | Organization type, department, target audience, event focus type, SDG goals/value mapping, event title, collaborating committees, POS/PSO notes, number of activities. |
| Objectives (`objectives-modern`) | `suite:generate_why_event` (objectives branch) or `suite:generate_objectives` fallback | Event title, focus type, collaborating committees, POS/PSO notes, SDG value mapping. |
| Expected Learning Outcomes (`outcomes-modern`) | `suite:generate_why_event` (learning outcomes branch) or `suite:generate_learning_outcomes` fallback | Event title, target audience, POS/PSO notes, SDG goals/value mapping, number of activities. |

## Event Report form

The event report builder ships multiple AI buttons across the Event Summary, Outcomes, Reflection and Relevance sections.【F:emt/static/emt/js/submit_event_report.js†L1110-L1358】 Context for these prompts should be assembled from the proposal data (`window.PROPOSAL_DATA` and attendance metadata injected into the template) so that the model receives real event details alongside any report fields that already hold user input.【F:emt/templates/emt/submit_event_report.html†L366-L409】 Where `suite/field_config` JSONs exist they define the minimal fact set that should be passed to the backend generator.

| UI Field (ID) | Suggested endpoint | Required context fields |
| --- | --- | --- |
| Summary of Overall Event (`event-summary-modern`) | Future `suite:generate_event_summary` (not yet implemented) | Full proposal metadata (title, department, venue, academic year, focus), event schedule, attendance counts, activities list, speakers, and any saved summary/beneficiary text so the narrative covers flow and participation. |
| Learning Outcomes Achieved (`learning-outcomes-modern`) | `suite:generate_learning_outcomes_achieved` | Event title, target audience, POS/PSO mapping, SDG goals/value mapping, number of activities.【F:suite/field_config/learning_outcomes_achieved.json†L1-L10】 |
| Participant Feedback (`participant-feedback-modern`) | `suite:generate_student_engagement` | Event title, target audience, number of activities, student coordinators, faculty in-charges, SDG value mapping to ground the engagement summary.【F:suite/field_config/student_engagement.json†L1-L10】 |
| Measurable Outcomes (`measurable-outcomes-modern`) | `suite:generate_measurable_outcomes` | Event title, target audience, number of activities, student coordinators, faculty in-charges, additional context notes, SDG value mapping.【F:suite/field_config/measurable_outcomes.json†L1-L11】 |
| Impact Assessment (`impact-assessment-modern`) | `suite:generate_impact_assessment` | Event title, target audience, focus type, SDG goals/value mapping, POS/PSO notes, additional context (e.g., qualitative observations).【F:suite/field_config/impact_assessment.json†L1-L11】 |
| Objective Achievement (`objective-achievement-modern`) | `suite:generate_objective_achievement` | Event title, target audience, focus type, SDG goals/value mapping, POS/PSO notes, number of activities.【F:suite/field_config/objective_achievement.json†L1-L11】 |
| Strengths Analysis (`strengths-analysis-modern`) | `suite:generate_strengths_analysis` | Event title, target audience, focus type, SDG goals/value mapping, POS/PSO notes, number of activities.【F:suite/field_config/strengths_analysis.json†L1-L11】 |
| Challenges Analysis (`challenges-analysis-modern`) | `suite:generate_challenges_analysis` | Event title, target audience, focus type, SDG goals/value mapping, POS/PSO notes, number of activities.【F:suite/field_config/challenges_analysis.json†L1-L11】 |
| Effectiveness Analysis (`effectiveness-analysis-modern`) | `suite:generate_effectiveness_analysis` | Event title, target audience, focus type, SDG goals/value mapping, POS/PSO notes, number of activities.【F:suite/field_config/effectiveness_analysis.json†L1-L11】 |
| Lessons Learned (`lessons-learned-modern`) | `suite:generate_lessons_learned` | Event title, target audience, focus type, SDG goals/value mapping, POS/PSO notes, number of activities.【F:suite/field_config/lessons_learned.json†L1-L11】 |
| PO’s and PSO’s Management (`pos-pso-modern`) | `suite:generate_pos_pso` | Event title, target audience, focus type, POS/PSO management text, SDG goals/value mapping, number of activities.【F:suite/field_config/pos_pso.json†L1-L11】 |
| Contemporary Requirements (`contemporary-requirements-modern`) | `suite:generate_contemporary_requirements` | Event title, target audience, focus type, POS/PSO notes, SDG goals/value mapping, number of activities.【F:suite/field_config/contemporary_requirements.json†L1-L11】 |
| SDG Implementation (`sdg-implementation-modern`) | Same payload as Contemporary Requirements plus explicit SDG selections | Event title, target audience, focus type, POS/PSO notes, SDG goals/value mapping, number of activities.【F:suite/field_config/contemporary_requirements.json†L1-L11】 |

> **Note:** `docs/event_report_ai_fields.json` already documents the narrative intent for several of these report fields; this table clarifies the underlying data dependencies so the frontend can post the right payload to each AI endpoint.【F:docs/event_report_ai_fields.json†L1-L14】

## AI Report Generator (one-click report)

The standalone AI Report Generator view sends the `reportData` payload—comprising proposal metadata and any saved report sections—to the `generate_ai_report` view, which constructs a structured prompt for the model.【F:emt/templates/emt/ai_generate_report.html†L24-L78】【F:emt/views.py†L3234-L3299】 When wiring additional AI helpers, reuse these same base fields so the generated narrative stays consistent across the progress, preview, and final report experiences.
