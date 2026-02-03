# main.py
"""
Main workflow file for the Personal Clawd Bot.
This file creates the LangGraph workflow that orchestrates all agents.
"""

import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state.agent_state import AgentState
from src.orchestrator_agent import orchestrator_node
from src.filesystem_agent import filesystem_agent_node
from src.general_agent import general_node

# Load environment variables
load_dotenv()

# ============================================================================
# LANGSMITH TRACING SETUP
# ============================================================================

def setup_langsmith():
    """
    Setup LangSmith tracing for observability.
    Requires LANGCHAIN_API_KEY in .env file.
    """
    langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
    
    if langchain_api_key:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "personal-clawd-bot"
        os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
        print("\n✅ LangSmith tracing enabled")
        print(f"📊 Project: personal-clawd-bot")
        print(f"🔗 View traces at: https://smith.langchain.com/\n")
    else:
        print("\n⚠️  LangSmith tracing disabled (LANGCHAIN_API_KEY not found in .env)")
        print("💡 To enable tracing, add LANGCHAIN_API_KEY to your .env file\n")

# Setup tracing
setup_langsmith()


# ============================================================================
# BUILD THE WORKFLOW GRAPH
# ============================================================================

def create_workflow():
    """
    Create the LangGraph workflow with all agents.
    
    Workflow structure:
    START → Orchestrator → (filesystem_agent | general) → END
    
    Returns:
        Compiled workflow graph
    """
    # Initialize the graph with AgentState
    workflow = StateGraph(AgentState)
    
    # Add nodes (agents)
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("filesystem_agent", filesystem_agent_node)
    workflow.add_node("general", general_node)
    
    # Set entry point
    workflow.set_entry_point("orchestrator")
    
    # Add conditional edges from orchestrator
    workflow.add_conditional_edges(
        "orchestrator",
        # Router function: decides next node based on state
        lambda state: state["next_agent"],
        {
            "filesystem_agent": "filesystem_agent",
            "general": "general",
            "end": END
        }
    )
    
    # After filesystem_agent completes, go to END
    workflow.add_edge("filesystem_agent", END)
    
    # After general completes, go to END
    workflow.add_edge("general", END)
    
    # Compile the graph with memory checkpointing
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


# ============================================================================
# RUN THE WORKFLOW
# ============================================================================

def run_workflow(user_input: str, thread_id: str = "default"):
    """
    Run the workflow with user input.
    
    Args:
        user_input: The user's request/query
        thread_id: Unique identifier for conversation thread
        
    Returns:
        Final response from the workflow
    """
    # Create workflow
    app = create_workflow()
    
    # Initialize state
    initial_state = {
        "messages": [],
        "next_agent": "",
        "task": "",
        "user_input": user_input,
        "final_response": ""
    }
    
    # Configuration for checkpointing
    config = {
        "configurable": {
            "thread_id": thread_id
        },
        "run_name": f"Clawd Bot - {user_input[:50]}",  # Shows in LangSmith
        "tags": ["clawd-bot", "agentic-workflow"],  # Tags for LangSmith filtering
    }
    
    print("\n" + "=" * 80)
    print(f"USER INPUT: {user_input}")
    print("=" * 80)
    
    # Execute workflow
    try:
        result = app.invoke(initial_state, config)
        
        print("\n" + "=" * 80)
        print("WORKFLOW EXECUTION COMPLETE")
        print("=" * 80)
        print(f"\nFinal Response:\n{result['final_response']}")
        print("\n" + "=" * 80)
        
        return result["final_response"]
        
    except Exception as e:
        error_msg = f"Error during workflow execution: {str(e)}"
        print(f"\n❌ {error_msg}")
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        return error_msg


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Direct input from user
    user_input = input("\n🤖 Enter your request: ")
    
    # Run workflow
    run_workflow(user_input)