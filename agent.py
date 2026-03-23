from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from tools.rag_tool import rag_search
from tools.calculator_tool import calculator

# 1. Initialize the model 
# IMPORTANT: Remove format="json" for tool calling, 
# as LangGraph manages the format internally.
llm = ChatOllama(
    model="llama3.1",
    temperature=0
)

# 2. Your tools
tools = [rag_search, calculator]

# 3. Create the agent
# You can add a simple 'state_modifier' instead of a complex ReAct template.
# This acts as the "System Instructions".
system_instructions = (
    "You are a helpful assistant. "
    "Use the calculator for math and rag_search for knowledge. "
    "After receiving tool results, provide a clear, refined answer to the user."
)

agent_executor = create_react_agent(
    llm, 
    tools,
    prompt=system_instructions, # This is how you "prompt" LangGraph agents
    debug=True
)

def safe_run(question: str):
    print("="*30)
    print(f"User: {question}")
    try:
        # LangGraph inputs
        result = agent_executor.invoke({"messages": [("user", question)]})
        
        # In LangGraph, the result is a dict containing the 'messages' list
        # We take the content of the very last message (the assistant's refined response)
        return result["messages"][-1].content
    except Exception as e:
        print("----Error----")
        print(f"Error: {e}")
        return 
        return llm.invoke(question).content
