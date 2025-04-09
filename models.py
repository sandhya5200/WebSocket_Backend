from database import Base  
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql import func


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=False, nullable=False)

    messages_sent = relationship("ChatMessages", foreign_keys="[ChatMessages.from_user_id]", back_populates="sender")
    messages_received = relationship("ChatMessages", foreign_keys="[ChatMessages.to_user_id]", back_populates="receiver")

class ChatMessages(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=func.now())
    message = Column(String, nullable=True)         # Text message
    image = Column(LargeBinary, nullable=True)      # Binary image
    from_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    group_id = Column(Integer, ForeignKey("groups.group_id"), nullable=True)
    type = Column(String, nullable=False)

    sender = relationship("User", foreign_keys=[from_user_id])
    receiver = relationship("User", foreign_keys=[to_user_id])
    group = relationship("Group", back_populates="messages")

class Group(Base):
    __tablename__ = "groups"

    group_id = Column(Integer, primary_key=True, index=True)
    group_name = Column(String, unique=False, nullable=False)
    user_ids = Column(ARRAY(Integer), nullable=False)  

    messages = relationship("ChatMessages", back_populates="group")

