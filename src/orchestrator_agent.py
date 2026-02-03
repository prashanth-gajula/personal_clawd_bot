# agents/orchestrator_agent.py
"""
Orchestrator Agent - Routes user requests to specialized agents.
Uses function-based approach for LangGraph integration.
"""

import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from state.agent_state import AgentState
from prompts.prompt import ORCHESTRATOR_SYSTEM_PROMPT

# Load environment variables
load_dotenv()

# Initialize LLM - GPT-4o
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)


def analyze_request(user_input: str) -> str:
    """
    Analyze user request and determine which agent to route to.
    
    Args:
        user_input: The user's request
        
    Returns:
        Agent name to route to ("filesystem_agent", "google_agent", or "general")
    """
    messages = [
        SystemMessage(content=ORCHESTRATOR_SYSTEM_PROMPT),
        HumanMessage(content=f"User request: {user_input}")
    ]
    
    response = llm.invoke(messages)
    agent_name = response.content.strip().lower()
    
    # Validate agent name
    valid_agents = ["filesystem_agent", "google_agent", "general"]
    if agent_name not in valid_agents:
        # Default to general if unclear
        return "general"
    
    return agent_name


def orchestrator_node(state: AgentState) -> AgentState:
    """
    Orchestrator node that analyzes and routes user requests.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with next_agent set
    """
    user_input = state["user_input"]
    
    # Analyze and determine next agent
    next_agent = analyze_request(user_input)
    
    # Update state
    state["next_agent"] = next_agent
    state["task"] = user_input
    
    # Add orchestrator message
    orchestrator_message = AIMessage(
        content=f"[Orchestrator] Routing request to {next_agent}...",
        name="orchestrator"
    )
    state["messages"].append(orchestrator_message)
    
    print(f"[Orchestrator] User: {user_input}")
    print(f"[Orchestrator] Routing to: {next_agent}")
    
    return state


# ============================================================================
# TESTING
# ============================================================================
"""
if __name__ == "__main__":
    # Test the orchestrator
    test_requests = [
        "Read config.json",
        "Search for Python tutorials online",
        "Hello! How are you?",
        "Create a new folder called Projects on D: drive",
        "What's the weather today?",
        "Delete old log files",
    ]
    
    print("=" * 80)
    print("ORCHESTRATOR AGENT TEST")
    print("=" * 80)
    
    for request in test_requests:
        agent = analyze_request(request)
        print(f"\nUser: {request}")
        print(f"→ Routed to: {agent}")
    
    print("\n" + "=" * 80)
"""