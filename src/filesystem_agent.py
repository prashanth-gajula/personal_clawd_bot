# src/filesystem_agent.py
"""
Filesystem Agent - Specialized agent for file and directory operations.
Uses filesystem tools to perform read, write, delete, search, and other file operations.
"""

import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from dotenv import load_dotenv
from state.agent_state import AgentState
from tools.file_system_tools import FILESYSTEM_TOOLS
from prompts.prompt import FILESYSTEM_AGENT_PROMPT

# Load environment variables
load_dotenv()

# Initialize LLM - GPT-4o with tools bound
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)

# Bind tools to LLM
llm_with_tools = llm.bind_tools(FILESYSTEM_TOOLS)


# ============================================================================
# FILESYSTEM AGENT NODE
# ============================================================================

def filesystem_agent_node(state: AgentState) -> AgentState:
    """
    Filesystem agent node that executes file operations.
    
    This agent:
    1. Receives task from orchestrator
    2. Uses filesystem tools to complete the task
    3. Returns results to user
    
    Args:
        state: Current agent state with task
        
    Returns:
        Updated state with final response
    """
    task = state["task"]
    
    print(f"\n[Filesystem Agent] Received task: {task}")
    
    try:
        # Create messages with system prompt and user task
        messages = [
            SystemMessage(content=FILESYSTEM_AGENT_PROMPT),
            HumanMessage(content=task)
        ]
        
        # Add chat history if exists
        if state.get("messages"):
            messages = state["messages"] + messages
        
        # Call LLM with tools
        response = llm_with_tools.invoke(messages)
        
        print(f"[Filesystem Agent] LLM Response received")
        
        # Check if LLM wants to use tools
        if response.tool_calls:
            print(f"[Filesystem Agent] Tool calls requested: {len(response.tool_calls)}")
            
            # Execute each tool call
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_call_id = tool_call["id"]
                
                print(f"[Filesystem Agent] Calling tool: {tool_name}")
                print(f"[Filesystem Agent] Args: {tool_args}")
                
                # Find and execute the tool
                tool_output = None
                for tool in FILESYSTEM_TOOLS:
                    if tool.name == tool_name:
                        tool_output = tool.invoke(tool_args)
                        print(f"[Filesystem Agent] Tool output: {tool_output[:200]}...")
                        break
                
                if tool_output is None:
                    tool_output = f"Error: Tool '{tool_name}' not found"
                
                # Create tool message
                tool_messages.append(
                    ToolMessage(
                        content=str(tool_output),
                        tool_call_id=tool_call_id,
                        name=tool_name
                    )
                )
            
            # Add tool response to messages and call LLM again to get final answer
            messages.append(response)
            messages.extend(tool_messages)
            
            # Get final response from LLM
            final_llm_response = llm.invoke(messages)
            final_response = final_llm_response.content
            
            print(f"[Filesystem Agent] Final response generated")
            
        else:
            # LLM responded directly without using tools
            final_response = response.content
            print(f"[Filesystem Agent] Direct response (no tools used)")
        
        # Update state
        state["final_response"] = final_response
        state["next_agent"] = "end"
        
        # Add agent message to history
        agent_message = AIMessage(
            content=final_response,
            name="filesystem_agent"
        )
        state["messages"].append(agent_message)
        
        print(f"[Filesystem Agent] Task completed successfully")
        
    except Exception as e:
        error_message = f"Error executing filesystem operation: {str(e)}"
        print(f"[Filesystem Agent] Error: {error_message}")
        
        import traceback
        traceback.print_exc()
        
        state["final_response"] = error_message
        state["next_agent"] = "end"
        
        error_msg = AIMessage(
            content=error_message,
            name="filesystem_agent"
        )
        state["messages"].append(error_msg)
    
    return state


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    # Test the filesystem agent
    test_tasks = [
        "Search for files named config",
        "List all files in D:/",
        "Read requirements.txt",
        "Get information about .env file",
    ]
    
    print("=" * 80)
    print("FILESYSTEM AGENT TEST")
    print("=" * 80)
    
    for task in test_tasks:
        print(f"\n{'='*80}")
        print(f"Task: {task}")
        print(f"{'='*80}")
        
        # Create mock state
        state = AgentState(
            messages=[],
            next_agent="filesystem_agent",
            task=task,
            user_input=task,
            final_response=""
        )
        
        # Execute filesystem agent
        result = filesystem_agent_node(state)
        
        print(f"\nResponse: {result['final_response']}")
        print(f"Next Agent: {result['next_agent']}")
        print(f"{'='*80}\n")