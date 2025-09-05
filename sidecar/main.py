import os
import json
import logging
from typing import List, Optional
from fastapi import FastAPI
from pydantic import BaseModel, Field

from agentscope import Agent, Hub, Model

logger = logging.getLogger(__name__)

PROVIDER = os.getenv("AS_PROVIDER", "ollama").lower()
MODEL_NAME = os.getenv("AS_MODEL", "llama3.1:8b")
TEMP = float(os.getenv("AS_TEMP", "0.3"))

llm = Model(MODEL_NAME, provider=PROVIDER, temperature=TEMP)

class ProposalContext(BaseModel):
    title: str
    department: str
    audience: Optional[str] = None
    date: Optional[str] = None
    venue: Optional[str] = None
    description: Optional[str] = None
    objectives_hint: Optional[str] = None
    outcomes_hint: Optional[str] = None
    pso_list: List[str] = Field(default_factory=list)
    po_list: List[str] = Field(default_factory=list)
    sdg_list: List[str] = Field(default_factory=list)
    budget_items: Optional[List[dict]] = None
    participants: Optional[List[dict]] = None

class ObjectiveItem(BaseModel):
    title: str
    detail: str
    measurable_metric: str

class OutcomeItem(BaseModel):
    statement: str
    measurement: str
    mapped: dict

class NeedAnalysisResp(BaseModel):
    need_analysis: str

class ObjectivesResp(BaseModel):
    objectives: List[ObjectiveItem]

class OutcomesResp(BaseModel):
    outcomes: List[OutcomeItem]

class ReportResp(BaseModel):
    report_markdown: str
    tables: dict = Field(default_factory=dict)

summarizer = Agent("Summarizer", llm)
mapper = Agent("Mapper", llm)
formatter = Agent("Formatter", llm)
guard = Agent("Guard", llm)

hub = Hub([summarizer, mapper, formatter, guard])

app = FastAPI(title="IQAC AgentScope Sidecar", version="0.1")

COMMON_SYS = (
    "You are an academic writing assistant for a university IQAC system. "
    "Be factual, formal, and concise. If data is missing, write 'TBD'. "
    "Never invent statistics or approvals."
)

@app.post("/generate/need_analysis", response_model=NeedAnalysisResp)
async def gen_need_analysis(ctx: ProposalContext):
    prompt = f"""
{COMMON_SYS}
Task: Draft a Need Analysis for the event.
Context: {ctx.model_dump_json()}
Output: 1–2 paragraphs under heading 'Need Analysis'.
"""
    logger.debug("Generating need analysis with context: %s", ctx)
    text = hub.run({"role": "user", "content": prompt})
    return NeedAnalysisResp(need_analysis=str(text))

@app.post("/generate/objectives", response_model=ObjectivesResp)
async def gen_objectives(ctx: ProposalContext):
    prompt = f"""
{COMMON_SYS}
Task: Produce 3–6 SMART objectives for the event.
Context: {ctx.model_dump_json()}
Return JSON list with: title, detail, measurable_metric.
"""
    logger.debug("Generating objectives with context: %s", ctx)
    raw = hub.run({"role": "user", "content": prompt})
    try:
        data = json.loads(str(raw))
        items = [ObjectiveItem(**o) for o in data]
    except Exception:
        logger.exception("Failed to parse objectives JSON; returning fallback")
        items = [ObjectiveItem(title="TBD Objective", detail=str(raw)[:500], measurable_metric="TBD")]
    return ObjectivesResp(objectives=items)

@app.post("/generate/outcomes", response_model=OutcomesResp)
async def gen_outcomes(ctx: ProposalContext):
    prompt = f"""
{COMMON_SYS}
Task: Propose measurable outcomes and map each to PSO/PO/SDG from the provided lists.
Context: {ctx.model_dump_json()}
Return JSON list of objects: {{statement, measurement, mapped: {{PSO:[], PO:[], SDG:[]}}}}
Rules: Only use IDs given in lists; if unsure → empty array.
"""
    logger.debug("Generating outcomes with context: %s", ctx)
    raw = hub.run({"role": "user", "content": prompt})
    try:
        data = json.loads(str(raw))
        items = [OutcomeItem(**o) for o in data]
    except Exception:
        logger.exception("Failed to parse outcomes JSON; returning fallback")
        items = [OutcomeItem(statement="TBD", measurement="TBD", mapped={"PSO": [], "PO": [], "SDG": []})]
    return OutcomesResp(outcomes=items)

@app.post("/generate/report", response_model=ReportResp)
async def gen_report(ctx: ProposalContext):
    prompt = f"""
{COMMON_SYS}
Task: Write a full event report in Markdown with these sections:
## Title
## Need Analysis
## Objectives
## Outcomes and Measurement
## PSO/PO/SDG Mapping
## Conduct and Timeline
## Participation Summary
## Budget Summary
## Conclusion

Constraints:
- If ctx.participants or ctx.budget_items exist, create simple Markdown tables.
- Keep formal tone, avoid claims not present in context.
Context JSON: {ctx.model_dump_json()}
"""
    logger.debug("Generating report with context: %s", ctx)
    text = hub.run({"role": "user", "content": prompt})
    tables = {"participants": ctx.participants or [], "budget": ctx.budget_items or []}
    return ReportResp(report_markdown=str(text), tables=tables)
