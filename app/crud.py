
from sqlalchemy.orm import Session
from sqlalchemy import func
from . import models

def create_session(db: Session):
    db_session = models.Session()
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_session(db: Session, session_id: int):
    return db.query(models.Session).filter(models.Session.id == session_id).first()

def create_history(db: Session, question: str, answer: str, session_id: int):
    db_history = models.History(question=question, answer=answer, session_id=session_id)
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history

def get_history_by_session(db: Session, session_id: int):
    return db.query(models.History).filter(models.History.session_id == session_id).order_by(models.History.created_at).all()

def get_last_histories_by_session(db: Session, session_id: int, limit_pairs: int):
    """Retorna as últimas N entradas de histórico (pares pergunta/resposta), ordenadas do mais antigo para o mais recente."""
    if limit_pairs is None or limit_pairs <= 0:
        return []
    q = (
        db.query(models.History)
        .filter(models.History.session_id == session_id)
        .order_by(models.History.created_at.desc())
        .limit(limit_pairs)
        .all()
    )
    return list(reversed(q))

def prune_history(db: Session, max_rows: int):
    """Mantém no máximo max_rows registros em history (global), removendo os mais antigos."""
    if not max_rows or max_rows <= 0:
        return 0
    total = db.query(func.count(models.History.id)).scalar() or 0
    if total <= max_rows:
        return 0
    to_delete = total - max_rows
    # Seleciona os ids mais antigos para apagar
    old_ids = (
        db.query(models.History.id)
        .order_by(models.History.created_at.asc(), models.History.id.asc())
        .limit(to_delete)
        .all()
    )
    old_ids = [row[0] for row in old_ids]
    if old_ids:
        db.query(models.History).filter(models.History.id.in_(old_ids)).delete(synchronize_session=False)
        db.commit()
    return len(old_ids)

def prune_sessions(db: Session, max_sessions: int):
    """Mantém no máximo max_sessions em session (global). Remove as mais antigas e seus históricos."""
    if not max_sessions or max_sessions <= 0:
        return 0
    total = db.query(func.count(models.Session.id)).scalar() or 0
    if total <= max_sessions:
        return 0
    to_delete = total - max_sessions
    old_sessions = (
        db.query(models.Session.id)
        .order_by(models.Session.created_at.asc(), models.Session.id.asc())
        .limit(to_delete)
        .all()
    )
    old_session_ids = [row[0] for row in old_sessions]
    if not old_session_ids:
        return 0
    # Apaga históricos dessas sessões primeiro
    db.query(models.History).filter(models.History.session_id.in_(old_session_ids)).delete(synchronize_session=False)
    # Depois apaga as sessões
    db.query(models.Session).filter(models.Session.id.in_(old_session_ids)).delete(synchronize_session=False)
    db.commit()
    return len(old_session_ids)
