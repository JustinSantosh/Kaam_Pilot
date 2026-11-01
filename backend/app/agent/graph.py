"""Workflow topology (D-001). See docs/project.md §3.2 for the diagram."""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from app.agent.deps import Deps
from app.agent.nodes import Nodes, route_guardrail, route_intent, route_validation
from app.agent.state import AgentState


def build_graph(deps: Deps, checkpointer: BaseCheckpointSaver | None = None) -> CompiledStateGraph:
    n = Nodes(deps)
    g = StateGraph(AgentState)

    g.add_node("ingest", n.ingest)
    g.add_node("guardrail", n.guardrail)
    g.add_node("intent", n.intent)
    g.add_node("extract", n.extract)
    g.add_node("validate", n.validate)
    g.add_node("clarify_draft", n.clarify_draft)
    g.add_node("reply_draft", n.reply_draft)
    g.add_node("cancel_handler", n.cancel_handler)
    g.add_node("price", n.price)
    g.add_node("render_pdf", n.render_pdf)

    g.add_edge(START, "ingest")
    g.add_edge("ingest", "guardrail")
    g.add_conditional_edges("guardrail", route_guardrail, {"ok": "intent", "flagged": END})
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
    g.add_edge("render_pdf", END)
    for terminal in ("clarify_draft", "reply_draft", "cancel_handler"):
        g.add_edge(terminal, END)

    return g.compile(checkpointer=checkpointer)
