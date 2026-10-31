"""Workflow topology (D-001). See docs/project.md §3.2 for the diagram."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.deps import Deps
from app.agent.nodes import (
    Nodes,
    route_decision,
    route_edits,
    route_guardrail,
    route_intent,
    route_validation,
)
from app.agent.state import AgentState


def build_graph(deps: Deps, checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    n = Nodes(deps)
    g = StateGraph(AgentState)

    for name in (
        "ingest", "guardrail", "reject_draft", "intent", "extract", "validate", "clarify_draft",
        "reply_draft", "cancel_handler", "price", "render_pdf", "submit_for_review", "hitl_pause",
        "apply_edits", "mark_rejected", "dispatch",
    ):  # fmt: skip
        g.add_node(name, getattr(n, name))

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "guardrail")
    g.add_conditional_edges(
        "guardrail", route_guardrail, {"ok": "intent", "flagged": "reject_draft"}
    )
    g.add_conditional_edges(
        "intent",
        route_intent,
        {"new_quote": "extract", "cancel": "cancel_handler", "other": "reply_draft"},
    )
    g.add_edge("extract", "validate")
    g.add_conditional_edges(
        "validate", route_validation, {"complete": "price", "incomplete": "clarify_draft"}
    )
    g.add_edge("price", "render_pdf")
    g.add_edge("render_pdf", "submit_for_review")
    g.add_edge("submit_for_review", "hitl_pause")
    g.add_conditional_edges(
        "hitl_pause",
        route_decision,
        {"approve": "dispatch", "edit": "apply_edits", "reject": "mark_rejected"},
    )
    # D-009: edits are re-priced and re-rendered; invalid edits go back to the owner with errors.
    g.add_conditional_edges("apply_edits", route_edits, {"ok": "price", "invalid": "hitl_pause"})
    terminals = ("reject_draft", "clarify_draft", "reply_draft", "cancel_handler", "mark_rejected",
                 "dispatch")  # fmt: skip
    for terminal in terminals:
        g.add_edge(terminal, END)

    return g.compile(checkpointer=checkpointer)
