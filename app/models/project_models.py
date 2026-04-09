from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_db import Base

class ProjectModel(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)  # معرّف المشروع
    name = Column(String(150))  # اسم المشروع
    description = Column(Text)  # وصف المشروع
    owner_id = Column(Integer, ForeignKey('users.id'))  # معرّف المالك (ربط مع User)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)