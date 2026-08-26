"""LangGraph StateGraph: model → tools → classify → repair|end."""

from __future__ import annotations

from typing import Any, Callable, Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from config import Settings, load_settings
from mcp_client import ToolCallResult, call_transfer_funds
from repair import (
    COMPLIANCE_CODE,
    ERROR_32602,
    ERROR_OTHER,
    apply_compliance_from_prompt,
    fingerprint,
    identical_retry_forbidden,
)
from report import ComparisonReport, hop_from_tool_result
from state import AgentGraphState

SYSTEM = (
    "You are a banking operations agent. Call transfer_funds using fields "
    "from the user request. Do not invent extra identifiers. On the first "
    "call, send transfer_type, accounts, and amount only; do not send "
    "compliance_approval_code until a validation error names that field."
)


def first_tool_arguments(args: dict[str, Any], repair_attempts: int) -> dict[str, Any]:
    """First tools/call omits compliance_approval_code.

    A capable local model often copies CMP-DEMO-2026 from the prompt on the
    first try, which hides the legacy-vs-strict contrast. The comparison
    withholds that field until a -32602 repair copies it from the prompt.
    """
    payload = dict(args)
    if repair_attempts == 0:
        payload.pop("compliance_approval_code", None)
    return payload


# Chat completions tool schema for the local model. MCP contract schemas live on
# the FastMCP servers; this object only needs `properties` so LM Studio accepts it.
_LLM_TOOL = {
    "type": "function",
    "function": {
        "name": "transfer_funds",
        "description": "Record a simulated fund transfer.",
        "parameters": {
            "type": "object",
            "properties": {
                "transfer_type": {
                    "type": "string",
                    "description": "internal or wire",
                },
                "source_account": {"type": "string"},
                "destination_account": {"type": "string"},
                "iban": {"type": "string"},
                "swift": {"type": "string"},
                "amount": {"type": "number"},
                "compliance_approval_code": {"type": "string"},
            },
            "required": ["transfer_type", "source_account", "amount"],
        },
    },
}


def _tool_args_from_message(message: AIMessage) -> dict[str, Any] | None:
    calls = getattr(message, "tool_calls", None) or []
    if not calls:
        return None
    args = calls[0].get("args") or {}
    return dict(args) if isinstance(args, dict) else None


def build_graph(
    settings: Settings,
    *,
    call_fn: Callable[[str, dict[str, Any]], ToolCallResult] | None = None,
    llm: Any | None = None,
    hops: list[Any] | None = None,
):
    invoker = call_fn or call_transfer_funds
    model = llm
    traces = hops if hops is not None else []

    def model_node(state: AgentGraphState) -> dict[str, Any]:
        chat = model
        if chat is None:
            from llm import get_chat_model

            chat = get_chat_model(settings)
        bound = chat.bind_tools([_LLM_TOOL])
        response = bound.invoke(state["messages"])
        return {"messages": [response]}

    def tools_node(state: AgentGraphState) -> dict[str, Any]:
        last = state["messages"][-1]
        args = _tool_args_from_message(last) if isinstance(last, AIMessage) else None
        if args is None:
            args = dict(state.get("last_arguments") or {})
        attempts = int(state.get("repair_attempts") or 0)
        args = first_tool_arguments(args, attempts)
        if attempts > 0:
            prior = dict(state.get("last_arguments") or {})
            code = prior.get("compliance_approval_code")
            if code and not args.get("compliance_approval_code"):
                args["compliance_approval_code"] = code
        if identical_retry_forbidden(
            state.get("last_payload_fingerprint"),
            args,
            str(state.get("last_error_kind") or ""),
        ):
            return {
                "last_arguments": args,
                "last_error_kind": ERROR_OTHER,
                "last_error_message": "identical invalid payload retry forbidden",
                "transfer_recorded": False,
            }
        url = settings.mcp_url(state["contract_mode"])
        result = invoker(url, args)
        traces.append(hop_from_tool_result(result))
        tool_id = "call-1"
        if isinstance(last, AIMessage) and last.tool_calls:
            tool_id = str(last.tool_calls[0].get("id") or tool_id)
        content = result.message or (result.confirmation or {})
        tool_msg = ToolMessage(content=str(content), tool_call_id=tool_id)
        return {
            "messages": [tool_msg],
            "last_arguments": args,
            "last_payload_fingerprint": fingerprint(args),
            "last_error_kind": result.error_kind,
            "last_error_message": result.message,
            "transfer_recorded": result.ok,
            "confirmation": result.confirmation or {},
        }

    def classify_node(state: AgentGraphState) -> dict[str, Any]:
        kind = state.get("last_error_kind") or "none"
        attempts = int(state.get("repair_attempts") or 0)
        if kind == ERROR_32602:
            attempts += 1
        return {"repair_attempts": attempts, "last_error_kind": kind}

    def repair_node(state: AgentGraphState) -> dict[str, Any]:
        prompt = ""
        for msg in state.get("messages") or []:
            if isinstance(msg, HumanMessage):
                prompt = str(msg.content)
                break
        previous = dict(state.get("last_arguments") or {})
        changed = apply_compliance_from_prompt(previous, prompt)
        hint = (
            f"JSON-RPC -32602: {state.get('last_error_message')}. "
            f"If the user named {COMPLIANCE_CODE}, put that exact code in "
            "compliance_approval_code. Do not resubmit identical arguments."
        )
        return {
            "messages": [HumanMessage(content=hint)],
            "last_arguments": changed,
        }

    def route_after_classify(
        state: AgentGraphState,
    ) -> Literal["repair", "end"]:
        if state.get("transfer_recorded"):
            return "end"
        kind = state.get("last_error_kind")
        if kind != ERROR_32602:
            return "end"
        budget = settings.repair_budget
        if int(state.get("repair_attempts") or 0) > budget:
            return "end"
        return "repair"

    graph = StateGraph(AgentGraphState)
    graph.add_node("model", model_node)
    graph.add_node("tools", tools_node)
    graph.add_node("classify", classify_node)
    graph.add_node("repair", repair_node)
    graph.add_edge(START, "model")
    graph.add_edge("model", "tools")
    graph.add_edge("tools", "classify")
    graph.add_conditional_edges(
        "classify",
        route_after_classify,
        {"repair": "repair", "end": END},
    )
    graph.add_edge("repair", "model")
    return graph.compile()


def run_repair_loop(
    contract_mode: str,
    prompt: str,
    settings: Settings | None = None,
    *,
    call_fn: Callable[[str, dict[str, Any]], ToolCallResult] | None = None,
    initial_arguments: dict[str, Any] | None = None,
    llm: Any | None = None,
) -> ComparisonReport:
    cfg = settings or load_settings()
    hops: list[Any] = []
    graph = build_graph(cfg, call_fn=call_fn, llm=llm, hops=hops)
    state: AgentGraphState = {
        "messages": [
            SystemMessage(content=SYSTEM),
            HumanMessage(content=prompt),
        ],
        "contract_mode": contract_mode,  # type: ignore[typeddict-item]
        "repair_attempts": 0,
        "last_error_kind": "none",
        "last_payload_fingerprint": "",
        "last_arguments": initial_arguments or {},
        "transfer_recorded": False,
        "confirmation": {},
        "last_error_message": "",
    }
    if initial_arguments is not None and llm is None:
        # Deterministic path used by tests: skip the model, call the tool first.
        url = cfg.mcp_url(contract_mode)
        invoker = call_fn or call_transfer_funds
        attempts = 0
        last_fp: str | None = None
        args = dict(initial_arguments)
        last_kind = "none"
        confirmation = None
        while True:
            if identical_retry_forbidden(last_fp, args, last_kind):
                break
            result = invoker(url, args)
            hops.append(hop_from_tool_result(result))
            last_kind = result.error_kind
            last_fp = fingerprint(args)
            if result.ok:
                confirmation = result.confirmation
                break
            if last_kind != ERROR_32602 or attempts >= cfg.repair_budget:
                break
            attempts += 1
            nxt = apply_compliance_from_prompt(args, prompt)
            if fingerprint(nxt) == last_fp:
                break
            args = nxt
        return ComparisonReport(
            contract_mode=contract_mode,
            error_kind=last_kind,
            repair_attempts=attempts,
            transfer_recorded=confirmation is not None,
            transfer_id=(confirmation or {}).get("transfer_id"),
            hops=hops,
        )
    final = graph.invoke(state)
    confirmation = final.get("confirmation") or {}
    return ComparisonReport(
        contract_mode=contract_mode,
        error_kind=str(final.get("last_error_kind") or "none"),
        repair_attempts=int(final.get("repair_attempts") or 0),
        transfer_recorded=bool(final.get("transfer_recorded")),
        transfer_id=confirmation.get("transfer_id") if isinstance(confirmation, dict) else None,
        hops=hops,
    )
