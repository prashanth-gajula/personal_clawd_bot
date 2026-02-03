# state/agent_state.py
"""
Shared state definition for all agents in the workflow.
This state is passed between all agents in the LangGraph workflow.
"""

from typing import TypedDict, Annotated, List


class AgentState(TypedDict):
    """State that will be passed between agents in the workflow"""
    
    messages: Annotated[List, "The messages in the conversation"]
    next_agent: Annotated[str, "The next agent to route to"]
    task: Annotated[str, "The current task to be performed"]
    user_input: Annotated[str, "Original user input"]
    final_response: Annotated[str, "Final response to user"]