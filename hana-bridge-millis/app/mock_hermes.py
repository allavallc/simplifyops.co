from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Local Mock Hermes")


class ChatIn(BaseModel):
    message: str
    session_id: str | None = None
    source: str | None = None


@app.get('/health')
async def health():
    return {'status': 'ok'}


@app.post('/chat')
@app.post('/messages')
async def chat(payload: ChatIn):
    return {
        'response': f"[local-mock] source={payload.source or 'unknown'} session={payload.session_id or 'none'} :: {payload.message}"
    }
