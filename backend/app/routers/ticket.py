from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class TicketAttachmentResponse(BaseModel):
    id: int
    ticket_id: int
    file_name: str
    file_path: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketHistoryResponse(BaseModel):
    id: int
    ticket_id: int
    action: str
    description: Optional[str] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketCreate(BaseModel):
    title: str
    description: Optional[str] = None
    department: str  # IT or ENG
    category: Optional[str] = None
    priority: Optional[str] = "medium"


class TicketResponse(BaseModel):
    id: int
    ticket_id: str
    title: str
    description: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    requester_id: Optional[int] = None
    requester_name: Optional[str] = None
    requester_fullname: Optional[str] = None
    team_id: Optional[str] = None
    team_desc: Optional[str] = None
    pic_id: Optional[int] = None
    pic_name: Optional[str] = None
    pic_fullname: Optional[str] = None
    pic_assigned_at: Optional[datetime] = None
    resolution: Optional[str] = None
    resolution_status: Optional[str] = None
    cancel_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    attachments: List["TicketAttachmentResponse"] = []
    history: List["TicketHistoryResponse"] = []

    class Config:
        from_attributes = True


class TicketListResponse(BaseModel):
    id: int
    ticket_id: str
    title: Optional[str] = None
    department: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    requester_name: Optional[str] = None
    requester_fullname: Optional[str] = None
    team_id: Optional[str] = None
    team_desc: Optional[str] = None
    pic_name: Optional[str] = None
    pic_fullname: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketAssignPIC(BaseModel):
    pic_id: int
    pic_name: str
    description: Optional[str] = None


class TicketFinish(BaseModel):
    resolution: str
    resolution_status: str  # "accepted" or "declined"


class TicketCancel(BaseModel):
    cancel_reason: str


class DepartmentResponse(BaseModel):
    name: str
    label: str


class TeamResponse(BaseModel):
    team_id: str
    team_desc: str


class DashboardStats(BaseModel):
    total_tickets: int
    open_tickets: int
    in_progress_tickets: int
    resolved_tickets: int
    closed_tickets: int
    cancelled_tickets: int
    new_this_month: int
    resolved_this_month: int
    closed_this_month: int
    tickets_by_priority: dict = {}
    tickets_by_department: dict = {}
