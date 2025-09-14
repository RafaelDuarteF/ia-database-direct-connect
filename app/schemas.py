from pydantic import BaseModel
from datetime import datetime

class Question(BaseModel):
    question: str
    session_id: int | None = None

class History(BaseModel):
    id: int
    session_id: int
    question: str
    answer: str
    created_at: datetime

    class Config:
        from_attributes = True

class Session(BaseModel):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True
