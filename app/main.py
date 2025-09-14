from fastapi import FastAPI, Depends, HTTPException
import logging
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from . import schemas, crud
from .database import SessionLocal
from app.ai.pipeline import ChatPipeline
import os

app = FastAPI()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Auth via Bearer Token
security = HTTPBearer(auto_error=False)
ASK_BEARER_TOKEN = os.getenv("ASK_BEARER_TOKEN")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not ASK_BEARER_TOKEN:
        raise HTTPException(status_code=500, detail="Server misconfigured: missing ASK_BEARER_TOKEN")
    if credentials is None or (credentials.scheme or '').lower() != 'bearer':
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    if credentials.credentials != ASK_BEARER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    return True


@app.post("/ask")
def ask_question(question: schemas.Question, auth: bool = Depends(verify_token), db: Session = Depends(get_db)):
    # Le limites configuráveis
    max_history_rows = int(os.getenv("MAX_HISTORY_ROWS", "500"))
    max_sessions = int(os.getenv("MAX_SESSIONS", "100"))
    keep_last_pairs = int(os.getenv("HISTORY_KEEP_LAST_PAIRS", "5"))
    # Gerencia sessão
    session_id = question.session_id
    if session_id:
        session = crud.get_session(db, session_id)
        if not session:
            session = crud.create_session(db)
    else:
        session = crud.create_session(db)
    # Pruning global (histórico e sessões)
    try:
        crud.prune_sessions(db, max_sessions)
        crud.prune_history(db, max_history_rows)
    except Exception:
        pass
    # Busca histórico da sessão
    history_objs = crud.get_last_histories_by_session(db, session.id, keep_last_pairs)
    history_msgs = []
    for h in history_objs:
        history_msgs.append({"role": "user", "content": h.question})
        history_msgs.append({"role": "assistant", "content": h.answer})
    # Pipeline com histórico
    try:
        pipeline = ChatPipeline()
        answer, sql, result, clarification = pipeline.ask(question.question, history_msgs)
    except Exception as e:
        logging.getLogger(__name__).exception("Erro inesperado no endpoint /ask")
        raise HTTPException(status_code=500, detail="Não foi possível processar sua solicitação no momento.")
    # Salva histórico da pergunta e resposta final
    history = crud.create_history(db, question=question.question, answer=answer, session_id=session.id)
    return {
        "answer": answer,
        "sql": sql,
        "result": result,
        "clarification": clarification,
        "session_id": session.id,
        "history_id": history.id
    }
