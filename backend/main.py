from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
import time
import json
from groq import Groq
from starlette.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Internal imports
from router import route_query, log_routing_decision
from rag import load_index, retrieve
from evaluator import evaluate_response

load_dotenv()

app = FastAPI()

# Allow CORS for easy local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Groq Client
groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Ensure index exists
if not os.path.exists("faiss_index.bin"):
    print("WARNING: FAISS Index not found! Please run 'python rag.py' first.")

faiss_index, metadata = None, None
try:
    faiss_index, metadata = load_index()
    print("Successfully loaded FAISS index.")
except Exception as e:
    print(f"Failed to load index on startup. {e}")


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    response: str
    model_used: str
    tokens_input: int
    tokens_output: int
    evaluator_flags: list[str]
    is_safe: bool


@app.post("/chat")
def chat(request: QueryRequest):
    start_time = time.time()

    # 1. Router Selection
    routing_info = route_query(request.query)
    model = routing_info["model"]
    classification = routing_info["classification"]

    # 2. Retrieve Documents via RAG
    retrieved_chunks = []
    context_text = ""
    try:
        retrieved_chunks = retrieve(request.query, faiss_index, metadata, top_k=3)
        context_text = "\n\n---\n\n".join([c["text"] for c in retrieved_chunks])
    except Exception as e:
        print(f"Error in retrieval: {e}")

    context_provided = len(retrieved_chunks) > 0

    # 3. Formulate prompt
    system_prompt = (
        "You are an expert customer support agent for Clearpath, a SaaS project management tool. "
        "Answer the user's question using ONLY the context provided below. "
        "If you do not know the answer based on the context, clearly state that you do not have enough "
        "information."
    )

    user_prompt = f"Context:\n{context_text}\n\nUser Question: {request.query}"

    # 4. Call Groq with Stream
    try:
        completion = groq_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=512,
            stream=True,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM API Error: {str(e)}")

    def generate():
        full_text = ""
        tokens_input = 0
        tokens_output = 0

        for chunk in completion:
            if chunk.choices and len(chunk.choices) > 0:
                content = chunk.choices[0].delta.content
                if content:
                    full_text += content
                    yield f"data: {json.dumps({'type': 'token', 'text': content})}\n\n"

            if getattr(chunk, "usage", None) is not None:
                tokens_input = chunk.usage.prompt_tokens
                tokens_output = chunk.usage.completion_tokens

        latency_ms = int((time.time() - start_time) * 1000)

        # Log Routing Decision
        log_routing_decision(
            query=request.query,
            classification=classification,
            model_used=model,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            latency_ms=latency_ms,
        )

        # 5. Output Evaluator (Must wait until end for full stream context)
        is_safe, flags = evaluate_response(full_text, context_provided)

        meta = {
            "type": "meta",
            "model_used": model,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "evaluator_flags": flags,
            "is_safe": is_safe,
        }

        yield f"data: {json.dumps(meta)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
