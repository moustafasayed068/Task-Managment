from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_db import Base

class TaskModel(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(200))  # عنوان المهمة
    description = Column(Text)  # وصف المهمة
    status = Column(String(50), default='todo')  # الحالة (todo, in_progress, done)
    priority = Column(String(50), default='medium')  # الأولوية (low, medium, high)
    project_id = Column(Integer, ForeignKey('projects.id'))  # أي مشروع فيها؟
    assignee_id = Column(Integer, ForeignKey('users.id'))  # مين المسؤول عنها؟
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)