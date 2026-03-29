"""Agent workflow state definition.

Uses TypedDict (not Pydantic BaseModel) for checkpoint serialization safety.
See PITFALLS.md Pitfall 11: Pydantic models cause serialization failures.
"""

from typing import Annotated

from langgraph.graph.message import add_messages
from langgraph.managed import RemainingSteps
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Agent workflow state. TypedDict for checkpoint serialization safety.

    Fields:
        messages: Message history with ID-based dedup via add_messages reducer.
        plan: Current step description (what the agent plans to do).
        scratchpad: Intermediate reasoning and context accumulation.
        remaining_steps: Managed value for proactive recursion limit handling.
    """

    messages: Annotated[list, add_messages]
    plan: str
    scratchpad: str
    remaining_steps: RemainingSteps
