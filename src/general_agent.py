import os
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from state.agent_state import AgentState
# Load environment variables
load_dotenv()

# Initialize LLM - GPT-4o
llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.1,
    openai_api_key=os.getenv("OPENAI_API_KEY")
)



def general_node(state: AgentState) -> AgentState:
    """
    Handle general conversation (greetings, unclear requests, etc.)
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with response
    """
    user_input = state["user_input"]
    
    general_prompt = """You are a helpful AI assistant. 
    
Respond naturally to the user's message. If they're greeting you, greet them back.
If their request is unclear, politely ask for clarification.
If they seem to want to perform a task but it's not clear what, help them clarify.

Be friendly, concise, and helpful."""
    
    messages = [
        SystemMessage(content=general_prompt),
        HumanMessage(content=user_input)
    ]
    
    response = llm.invoke(messages)
    
    # Update state
    state["final_response"] = response.content
    state["next_agent"] = "end"
    
    general_message = AIMessage(
        content=response.content,
        name="general"
    )
    state["messages"].append(general_message)
    
    print(f"[General] Response: {response.content}")
    
    return state