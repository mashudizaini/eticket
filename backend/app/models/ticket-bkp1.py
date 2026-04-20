from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Ticket(Base):
    """Mapping ke tabel tickets di PostgreSQL"""
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    department = Column(String(50))
    category = Column(String(50))
    priority = Column(String(20))
    status = Column(String(20), default="new")
    requester_id = Column(Integer)  # Oracle person_id, no FK constraint
    requester_name = Column(String(100))
    pic_id = Column(Integer)  # Oracle person_id, no FK constraint
    pic_name = Column(String(100))
    pic_assigned_at = Column(DateTime(timezone=True))
    resolution = Column(Text)
    resolution_status = Column(String(20))
    cancel_reason = Column(Text)
    cancelled_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    closed_at = Column(DateTime(timezone=True))

    # Relationships
    attachments = relationship("TicketAttachment", back_populates="ticket", lazy="joined")
    history = relationship("TicketHistory", back_populates="ticket", order_by="TicketHistory.created_at", lazy="joined")


class TicketAttachment(Base):
    """Mapping ke tabel ticket_attachments di PostgreSQL"""
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    ticket = relationship("Ticket", back_populates="attachments")


class TicketHistory(Base):
    """Mapping ke tabel ticket_history di PostgreSQL"""
    __tablename__ = "ticket_history"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    action = Column(String(50), nullable=False)
    description = Column(Text)
    old_status = Column(String(20))
    new_status = Column(String(20))
    actor_id = Column(Integer)  # Oracle person_id, no FK constraint
    actor_name = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    ticket = relationship("Ticket", back_populates="history")


class User(Base):
    """Mapping ke tabel users di PostgreSQL (untuk referensi lokal)"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100))
    department = Column(String(50))
    role = Column(String(20))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
