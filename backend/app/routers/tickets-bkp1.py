from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
import os
import uuid

from app.database import get_db
from app.config import get_settings
from app.dependencies import get_current_user, CurrentUser
from app.models.ticket import Ticket, TicketAttachment, TicketHistory
from app.schemas.ticket import (
    TicketCreate,
    TicketResponse,
    TicketListResponse,
    TicketAssignPIC,
    TicketFinish,
    TicketCancel,
    TicketHistoryResponse,
    TicketAttachmentResponse,
    DepartmentResponse,
)

router = APIRouter(prefix="/tickets", tags=["Tickets"])
settings = get_settings()

# Status constants
STATUS_NEW = "new"
STATUS_ASSIGNED = "assigned"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
STATUS_CANCELLED = "cancelled"

# Department list
DEPARTMENTS = [
    {"name": "IT", "label": "IT Department"},
    {"name": "ENG", "label": "Engineering"},
]


def generate_ticket_id() -> str:
    """Generate unique ticket ID with format: TKT-YYYYMMDD-XXXX"""
    date_part = datetime.now().strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:4].upper()
    return f"TKT-{date_part}-{unique_part}"


def find_ticket(db: Session, ticket_id: str) -> Optional[Ticket]:
    """Find ticket by numeric id or string ticket_id"""
    if ticket_id.isdigit():
        return db.query(Ticket).filter(Ticket.id == int(ticket_id)).first()
    return db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()


@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments():
    """Get list of departments"""
    return DEPARTMENTS


@router.get("/", response_model=List[TicketListResponse])
def get_all_tickets(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get all tickets"""
    team = current_user.team
    requester = current_user.employee_number

    query = db.query(Ticket)

    if team == "USER":
        query = query.filter(Ticket.requester_name == requester)
    elif team in ["IT", "ENG"]:
        query = query.filter(
            (Ticket.department == team) | (Ticket.requester_name == requester)
        )
    # ADM sees all tickets

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@router.get("/open", response_model=List[TicketListResponse])
def get_open_tickets(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get open tickets (status: new, assigned, in_progress)"""
    team = current_user.team
    requester = current_user.employee_number

    query = db.query(Ticket).filter(
        Ticket.status.in_([STATUS_NEW, STATUS_ASSIGNED, STATUS_IN_PROGRESS])
    )

    if team == "USER":
        query = query.filter(Ticket.requester_name == requester)
    elif team in ["IT", "ENG"]:
        query = query.filter(
            (Ticket.department == team) | (Ticket.requester_name == requester)
        )
    # ADM sees all tickets

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@router.get("/closed", response_model=List[TicketListResponse])
def get_closed_tickets(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get closed tickets (status: resolved, closed, cancelled)"""
    team = current_user.team
    requester = current_user.employee_number

    query = db.query(Ticket).filter(
        Ticket.status.in_([STATUS_RESOLVED, STATUS_CLOSED, STATUS_CANCELLED])
    )

    if team == "USER":
        query = query.filter(Ticket.requester_name == requester)
    elif team in ["IT", "ENG"]:
        query = query.filter(
            (Ticket.department == team) | (Ticket.requester_name == requester)
        )
    # ADM sees all tickets

    tickets = query.order_by(Ticket.closed_at.desc().nullsfirst()).all()
    return tickets


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get ticket detail by ticket_id or numeric id"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/{ticket_id}/history", response_model=List[TicketHistoryResponse])
def get_ticket_history(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get ticket history/timeline"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    history = (
        db.query(TicketHistory)
        .filter(TicketHistory.ticket_id == ticket.id)
        .order_by(TicketHistory.created_at.asc())
        .all()
    )
    return history


# Alias for timeline (frontend uses /timeline, backend has /history)
@router.get("/{ticket_id}/timeline", response_model=List[TicketHistoryResponse])
def get_ticket_timeline(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get ticket timeline (alias for history)"""
    return get_ticket_history(ticket_id, db, current_user)


@router.get("/{ticket_id}/attachments", response_model=List[TicketAttachmentResponse])
def get_ticket_attachments(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get ticket attachments"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    attachments = (
        db.query(TicketAttachment)
        .filter(TicketAttachment.ticket_id == ticket.id)
        .all()
    )
    return attachments


@router.post("/", response_model=TicketResponse)
async def create_ticket(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    department: str = Form(...),
    category: Optional[str] = Form(None),
    priority: Optional[str] = Form("medium"),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create new ticket"""
    requester_name = current_user.employee_number
    requester_username = current_user.username

    # Generate unique ticket_id
    ticket_id = generate_ticket_id()

    # Create ticket
    ticket = Ticket(
        ticket_id=ticket_id,
        title=title,
        description=description,
        department=department,
        category=category,
        priority=priority,
        status=STATUS_NEW,
        requester_name=requester_name,
    )
    db.add(ticket)
    db.flush()  # Get the ticket.id

    # Handle file uploads
    if files:
        upload_dir = os.path.join(settings.UPLOAD_DIR, ticket_id)
        os.makedirs(upload_dir, exist_ok=True)

        for file in files[:5]:  # Max 5 files
            if file.filename:
                ext = file.filename.split(".")[-1].lower()
                if ext not in settings.ALLOWED_EXTENSIONS:
                    continue

                content = await file.read()
                if len(content) > settings.MAX_FILE_SIZE:
                    continue

                # Save file
                safe_name = f"{uuid.uuid4().hex[:8]}_{file.filename}".replace(" ", "_")
                file_path = os.path.join(upload_dir, safe_name)

                with open(file_path, "wb") as f:
                    f.write(content)

                # Create attachment record
                attachment = TicketAttachment(
                    ticket_id=ticket.id,
                    file_name=file.filename,
                    file_path=file_path,
                    file_type=ext,
                    file_size=len(content),
                )
                db.add(attachment)

    # Create history entry
    history = TicketHistory(
        ticket_id=ticket.id,
        action="CREATE",
        description=f"Ticket created by {requester_username}",
        new_status=STATUS_NEW,
        actor_name=requester_name,
    )
    db.add(history)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.patch("/{ticket_id}/assign")
def assign_pic(
    ticket_id: str,
    data: TicketAssignPIC,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Assign PIC to ticket"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status

    # Update ticket
    ticket.pic_id = data.pic_id
    ticket.pic_name = data.pic_name
    ticket.pic_assigned_at = datetime.now()
    ticket.status = STATUS_ASSIGNED
    ticket.updated_at = datetime.now()

    # Create history entry
    history = TicketHistory(
        ticket_id=ticket.id,
        action="ASSIGN",
        description=data.description or f"Assigned to {data.pic_name}",
        old_status=old_status,
        new_status=STATUS_ASSIGNED,
        actor_name=current_user.employee_number,
    )
    db.add(history)

    db.commit()
    return {"message": "PIC assigned successfully", "ticket_id": ticket_id}


@router.patch("/{ticket_id}/progress")
def update_progress(
    ticket_id: str,
    description: str = Form(...),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Update ticket progress"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status
    ticket.status = STATUS_IN_PROGRESS
    ticket.updated_at = datetime.now()

    # Create history entry
    history = TicketHistory(
        ticket_id=ticket.id,
        action="UPDATE",
        description=description,
        old_status=old_status,
        new_status=STATUS_IN_PROGRESS,
        actor_name=current_user.employee_number,
    )
    db.add(history)

    db.commit()
    return {"message": "Progress updated", "ticket_id": ticket_id}


@router.patch("/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: str,
    data: TicketFinish,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Resolve/finish ticket"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status
    ticket.resolution = data.resolution
    ticket.resolution_status = data.resolution_status
    ticket.status = STATUS_RESOLVED
    ticket.updated_at = datetime.now()
    ticket.closed_at = datetime.now()

    # Create history entry
    action = "ACCEPTED" if data.resolution_status == "accepted" else "DECLINED"
    history = TicketHistory(
        ticket_id=ticket.id,
        action=action,
        description=data.resolution,
        old_status=old_status,
        new_status=STATUS_RESOLVED,
        actor_name=current_user.employee_number,
    )
    db.add(history)

    db.commit()
    return {"message": f"Ticket {action.lower()}", "ticket_id": ticket_id}


@router.patch("/{ticket_id}/cancel")
def cancel_ticket(
    ticket_id: str,
    data: TicketCancel,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Cancel ticket"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status
    ticket.cancel_reason = data.cancel_reason
    ticket.status = STATUS_CANCELLED
    ticket.cancelled_at = datetime.now()
    ticket.updated_at = datetime.now()

    # Create history entry
    history = TicketHistory(
        ticket_id=ticket.id,
        action="CANCEL",
        description=data.cancel_reason,
        old_status=old_status,
        new_status=STATUS_CANCELLED,
        actor_name=current_user.employee_number,
    )
    db.add(history)

    db.commit()
    return {"message": "Ticket cancelled", "ticket_id": ticket_id}
