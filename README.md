# Clearpath Support Chatbot

A simple, minimal RAG-based chatbot designed to securely parse Clearpath documentations and answer user questions.

## Features
- **Layer 1 (RAG):** Recursive Character Chunking and local vector embedding search with `FAISS`.
- **Layer 2 (Router):** Deterministic routing based on length and explicit reasoning-demanding keywords to switch between Groq's Fast 8B and Reasoning 70B models.
- **Layer 3 (Evaluator):** Detects hallucinations from missing context, API refusals, and mentions of fake features or competitors.

## Setup and Run 

### 1. Backend 
Requires Python 3.9+ 

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Embed documents:** (Do this only once, or if you update `docs/` folder)
```bash
python rag.py
```

**Run Server:**
```bash
# Ensure your .env file in the backend folder contains: GROQ_API_KEY="your-groq-api-key"
uvicorn main:app --reload
```

### 2. Frontend
You can simply open `frontend/index.html` in your web browser. 
If you want to view it via a local server to avoid CORS/file issues:
```bash
cd frontend
python -m http.server 8080
```
Then navigate to `http://localhost:8080` in your browser.

## Groq Models Used
- Simple route: `llama-3.1-8b-instant`
- Complex route: `llama-3.3-70b-versatile`

## Bonuses Attempted
Due to time constraints for this take-home, we focused only on standard requirements. But the clean architecture supports easy injection of conversational history in the `main.py` Groq API call list!

## Known Issues / Limitations
1. Does not implement streaming.
2. In-memory `faiss` index handles small chunks successfully, but if `docs/` became hundreds of thousands of files, we would want a remote Vector Database.
