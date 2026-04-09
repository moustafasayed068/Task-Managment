from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.base_db import Base

class UserModel(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)  # معرّف فريد لكل مستخدم
    username = Column(String(50), unique=True)  # اسم المستخدم (فريد بالكامل)
    email = Column(String(255), unique=True)  # البريد (فريد بالكامل)
    password_hash = Column(String(255))  # كلمة المرور مشفرة (ما نحفظ الأصلية)
    role = Column(String(50), default='user')  # دوره (user, admin, etc)
    created_at = Column(DateTime, default=datetime.utcnow)  # تاريخ التسجيل
    updated_at = Column(DateTime, onupdate=datetime.utcnow)  # تاريخ آخر تعديل