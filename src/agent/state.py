"""LangGraph agent state."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages


class AgentGraphState(TypedDict, total=False):
    messages: Annotated[list[Any], add_messages]
    contract_mode: Literal["legacy", "strict"]
    repair_attempts: int
    last_error_kind: str
    last_payload_fingerprint: str
    last_arguments: dict[str, Any]
    transfer_recorded: bool
    confirmation: dict[str, Any]
    last_error_message: str
