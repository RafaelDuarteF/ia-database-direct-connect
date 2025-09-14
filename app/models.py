
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Session(Base):
    __tablename__ = "session"
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    histories = relationship("History", back_populates="session")

class History(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("session.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="histories")
