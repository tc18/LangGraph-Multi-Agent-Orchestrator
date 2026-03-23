from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from models import Query
# from agent import safe_run
# from agent_2 import safe_run, stream_graph_updates
from agent_3 import stream_graph_updates

app = FastAPI()

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# @app.post("/ask")
# def ask_ai(query: Query):

#     answer = safe_run(query.question)
    

#     # answer = result["messages"][-1].content

#     return {
#         "answer": answer
#     }

@app.get("/ask-stream")
async def ask_stream(query: str):
    return StreamingResponse(stream_graph_updates(query.question), media_type="text/event-stream")

###############################
#### Async POST API calls
###############################
from pydantic import BaseModel

# 1. Define the request structure
class ChatRequest(BaseModel):
    question: str
    
@app.post("/ask-stream")
async def ask_stream(request: ChatRequest):
    # Pass the question from the validated request body
    return StreamingResponse(
        stream_graph_updates(request.question), 
        media_type="text/event-stream"
    )