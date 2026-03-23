import os
import json
import asyncio
from typing import Annotated, TypedDict, Union
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# --- 1. THE STATE ---
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    next_agent: str

# --- 2. THE TOOLS ---
@tool
async def connectivity1(source_ip: str, destination_ip: str):
    """Traces the network path between two IP addresses. Use this for network troubleshooting."""
    hops = [
        f"Initiating trace from {source_ip}...",
        f"HOP 1: 10.0.0.1 (Internal Gateway) - 2ms",
        f"HOP 2: 172.16.254.1 (ISP Edge) - 12ms",
        f"HOP 3: 192.168.100.5 (Cloud Router) - 24ms",
        f"SUCCESS: Reached {destination_ip} - Total 38ms"
    ]
    
    # We simulate real-time processing by joining them
    # In a true 'per-line' stream, we'd use custom callbacks, 
    # but for this architecture, we return the block.
    return "\n".join(hops)

from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event

@tool
async def connectivity(source_ip: str, destination_ip: str, config: RunnableConfig):
    """Traces network path with real-time per-hop updates."""
    hops = [
        f"Trace started: {source_ip}",
        "Hop 1: 10.0.0.1 - 1ms",
        "Hop 2: 172.16.0.1 - 15ms",
        "Hop 3: 192.168.1.1 - 22ms",
        f"Reached: {destination_ip}"
    ]
    
    for hop in hops:
        # Pass the config here so the dispatcher has the parent run ID
        await adispatch_custom_event(
            "hop_update", 
            {"text": hop, "node": "network_tool"},
            config=config 
        )
        await asyncio.sleep(3)
        
    return "Full trace completed."

@tool
def calculator(expression: str):
    """Perform mathematical calculations."""
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Error: {e}"

# --- 3. THE NODES ---
llm = ChatOllama(model="llama3.1", temperature=0)

def create_agent_node(llm, tools, system_prompt):
    bound_llm = llm.bind_tools(tools)
    async def node(state: AgentState):
        input_messages = [{"role": "system", "content": system_prompt}] + state["messages"]
        result = await bound_llm.ainvoke(input_messages)
        return {"messages": [result]}
    return node

network_node = create_agent_node(llm, [connectivity], "You are a Network Engineer. Trace paths when asked.")
math_node = create_agent_node(llm, [calculator], "You are a Math Specialist.")

def supervisor_node(state: AgentState):
    system_prompt = "Decide who acts next: ['network', 'math', 'FINISH']. Only say the word."
    
    system_prompt = (
        "You are a high-level network and math orchestrator. "
        "The user is asking for a network trace. You MUST assign this to the 'network' agent. "
        "Do not finish until the network agent has provided the path details. "
        "Available agents: ['network', 'math']. "
        "Respond with ONLY the name of the next agent or 'FINISH'."
    )
    
    response = llm.invoke([{"role": "system", "content": system_prompt}] + state["messages"])
    content = response.content.strip().lower()
    if "network" in content: return {"next_agent": "network"}
    if "math" in content: return {"next_agent": "math"}
    return {"next_agent": "FINISH"}

# --- 4. THE GRAPH ---
workflow = StateGraph(AgentState)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("network", network_node)
workflow.add_node("math", math_node)
workflow.add_node("tools", ToolNode([connectivity, calculator]))

workflow.add_edge(START, "supervisor")
workflow.add_conditional_edges("supervisor", lambda x: x["next_agent"], {"network": "network", "math": "math", "FINISH": END})

def router(state: AgentState):
    if state["messages"][-1].tool_calls: return "tools"
    return "supervisor"

workflow.add_conditional_edges("network", router, {"tools": "tools", "supervisor": "supervisor"})
workflow.add_conditional_edges("math", router, {"tools": "tools", "supervisor": "supervisor"})
workflow.add_edge("tools", "supervisor")

app_graph = workflow.compile(debug=True)

# --- 5. FASTAPI SETUP ---
app_api = FastAPI()
app_api.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class QueryRequest(BaseModel):
    question: str
    

async def stream_graph_updates1(query: str):
    inputs = {"messages": [HumanMessage(content=query)]}
    
    # Using astream to capture each node's output as it finishes
    async for chunk in app_graph.astream(inputs, stream_mode="updates"):
        for node_name, data in chunk.items():
            if "messages" in data:
                last_msg = data["messages"][-1]
                
                # Stream Agent Text
                if isinstance(last_msg, AIMessage) and last_msg.content:
                    yield f"data: {json.dumps({'node': node_name, 'text': last_msg.content})}\n\n"
                
                # Stream Tool Output (Pings/Traceroute)
                elif isinstance(last_msg, ToolMessage):
                    yield f"data: {json.dumps({'node': 'system_tool', 'text': last_msg.content})}\n\n"
                    

async def stream_graph_updates(query: str):
    inputs = {"messages": [HumanMessage(content=query)]}
    
    # Use astream_events to catch 'on_custom_event'
    async for event in app_graph.astream_events(inputs, version="v2"):
        kind = event["event"]
        
        # 1. Handle our custom "per-ping" events
        if kind == "on_custom_event" and event["name"] == "hop_update":
            data = event["data"]
            yield f"data: {json.dumps({'node': data['node'], 'text': data['text']})}\n\n"
            
        # 2. Handle standard Agent text (Final thoughts)
        elif kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                yield f"data: {json.dumps({'node': 'agent', 'text': content})}\n\n"
