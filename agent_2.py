import os
from typing import Annotated, Literal, TypedDict, Union
from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

import json

# --- 1. THE STATE ---
class AgentState(TypedDict):
    # Using Annotated[..., add_messages] is critical for history management
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: str

# --- 2. THE TOOLS ---
@tool
def rag_search(query: str):
    """Search the restaurant knowledge base for specific facts."""
    # Simulation: In production, this would query your Vector DB
    if "table" in query.lower():
        return "The restaurant 'Kurry Leaves' has exactly 12 tables in the main dining area."
    return f"Result for {query}: Kurry Leaves is an Indian restaurant in Overland Park."

@tool
def calculator(expression: str):
    """Perform mathematical calculations."""
    try:
        # Note: In a real production app, use a safer eval or math library
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"
  
  

################################################
######## Checking Async tool
################################################
import asyncio

@tool
async def connectivity(source_ip: str, destination_ip: str):
    """Checks connectivity between two IPs and reveals the hops."""
    hops = [
        f"Checking {source_ip}...",
        f"{source_ip} ----> 10.0.0.1 (Internal Gateway)",
        f"10.0.0.1 ----> 10.0.0.2 (Cloud Router)",
        f"10.0.0.2 ----> 10.0.1.2 (Peering Link)",
        f"10.0.1.2 ----> {destination_ip} (Success!)",
    ]
    
    # We return the whole list for the LLM's memory, 
    # but we will handle the "visual" streaming in the runner.
    results = []
    for hop in hops:
        results.append(hop)
        # Simulate network latency
        await asyncio.sleep(0.8) 
    
    return "\n".join(results)

################################################
######## End: Checking Async tool
################################################

# --- 3. THE NODES ---
llm = ChatOllama(model="llama3.1", temperature=0)

def create_agent_node(llm, tools, system_prompt):
    """Helper to create a node that handles tool binding and defensive checks."""
    bound_llm = llm.bind_tools(tools)
    
    def node(state: AgentState):
        # We ensure the system prompt is always top-of-mind
        input_messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        try:
            result = bound_llm.invoke(input_messages)
            return {"messages": [result]}
        except Exception as e:
            return {"messages": [AIMessage(content=f"I encountered an error: {str(e)}")]}
    return node

# Define specialized nodes
research_node = create_agent_node(
    llm, [rag_search], 
    "You are a Research Specialist. Search for facts. If you find a number, report it clearly."
)
math_node = create_agent_node(
    llm, [calculator], 
    "You are a Math Specialist. Use the calculator tool for ALL math operations."
)

# --- 4. THE SUPERVISOR (Orchestrator) ---
def supervisor_node(state: AgentState):
    if not state.get("messages"):
        return {"next_agent": "researcher"}

    system_prompt = (
        "You are the manager of a research and math team. "
        "Based on the history, decide who acts next. "
        "If a fact is missing, call 'researcher'. "
        "If calculation is needed, call 'math'. "
        "If the final answer is ready, respond with ONLY the word 'FINISH'."
    )
    
    response = llm.invoke([{"role": "system", "content": system_prompt}] + state["messages"])
    content = response.content.strip().lower()
    
    if "researcher" in content:
        return {"next_agent": "researcher"}
    elif "math" in content:
        return {"next_agent": "math"}
    else:
        return {"next_agent": "FINISH"}

# --- 5. THE ROUTING LOGIC ---
def router(state: AgentState):
    """Checks if the last message actually requested a tool."""
    last_msg = state["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"
    return "supervisor"

# --- 6. BUILDING THE GRAPH ---
workflow = StateGraph(AgentState)

# Add all components
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("researcher", research_node)
workflow.add_node("math", math_node)
workflow.add_node("tools", ToolNode([rag_search, calculator]))

# Define the flow
workflow.add_edge(START, "supervisor")

# Supervisor decides which agent to trigger
workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next_agent"],
    {
        "researcher": "researcher",
        "math": "math",
        "FINISH": END
    }
)

# Agents check if they need tools; if not, they go back to supervisor
workflow.add_conditional_edges("researcher", router, {"tools": "tools", "supervisor": "supervisor"})
workflow.add_conditional_edges("math", router, {"tools": "tools", "supervisor": "supervisor"})

# Once tools are done, they ALWAYS report back to the supervisor
workflow.add_edge("tools", "supervisor")

app = workflow.compile(debug=True)

# --- 7. RUNNER WITH ERROR HANDLING ---
def safe_run(query: str):
    inputs = {"messages": [HumanMessage(content=query)]}
    final_response = []
    
    try:
        # We use stream_mode="values" here because it gives us the full state 
        # as it evolves, making it easier to grab the latest message.
        for event in app.stream(inputs, stream_mode="values"):
            if "messages" in event:
                print("-"*10)
                last_msg = event["messages"][-1]
                print(last_msg)
                # We only want to 'capture' content from AI Messages, not tool outputs
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    final_response.append(last_msg.content)
        return ' '.join(final_response)
    
    except Exception as e:
        return f"Backend Error: {str(e)}"
   
# --- 7. RUNNER WITH ERROR HANDLING ---
async def stream_graph_updates(query: str):
    inputs = {"messages": [HumanMessage(content=query)]}
    
    # We use stream_mode="updates" to get the specific output of each node
    async for chunk in app.astream(inputs, stream_mode="updates"):
        for node_name, data in chunk.items():
            msgs = data.get("messages", [])
            if msgs:
                content = msgs[-1].content
                # Only stream if there is actual text (skip empty tool-call messages)
                if content:
                    # We format as a small JSON object so the frontend can parse it easily
                    yield f"data: {json.dumps({'node': node_name, 'text': content})}\n\n"
