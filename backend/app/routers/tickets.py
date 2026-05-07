from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import datetime
import os
import uuid
import random

from app.database import get_db, get_oracle_db
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
    TicketPostpone,
    TicketHistoryResponse,
    TicketAttachmentResponse,
    DepartmentResponse,
    TeamResponse,
)
from app.services.oracle_lookup import get_employee_info, get_employee_name, get_team_list, get_employee_team_id, get_team_description

router = APIRouter(prefix="/tickets", tags=["Tickets"])
settings = get_settings()

# Status constants
STATUS_NEW = "new"
STATUS_ASSIGNED = "assigned"
STATUS_IN_PROGRESS = "in_progress"
STATUS_PENDING = "pending"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
STATUS_CANCELLED = "cancelled"

# Solver users who can see all tickets (by username)
ADMIN_USERS = ["system", "itsupport", "itsupport@ckd-otto.com", "mashudi@ckd-otto.com", "usep@ckd-otto.com"]

# Solver employees: can see all tickets and resolve/postpone/cancel (by employee_number)
# MASHUDI (A24010), HARDRYAN PRASETYO UTOMO (A24010), USEP HERMAWAN FAJAR (A20001)
SOLVER_EMPLOYEES = ["A25002", "A24010", "A20001"]

# Teams allowed to resolve tickets
RESOLVE_TEAMS = ["IT", "PLANT"]

# Department list
DEPARTMENTS = [
    {"name": "IT", "label": "IT Department"},
    {"name": "ENG", "label": "Engineering"},
]


def generate_ticket_id() -> str:
    """Generate unique ticket ID: YYYYMMDDHHMMSS + 6 random digits"""
    dt_part = datetime.now().strftime("%Y%m%d%H%M%S")
    rand_part = str(random.randint(100000, 999999))
    return f"{dt_part}{rand_part}"


def find_ticket(db: Session, ticket_id: str) -> Optional[Ticket]:
    """Find ticket by string ticket_id (new format: 20-digit) or legacy numeric DB id"""
    # New format ticket_id is 20 chars (YYYYMMDDHHMMSS + 6 digits)
    # Legacy numeric id (DB primary key) is typically short (< 10 digits)
    if ticket_id.isdigit() and len(ticket_id) <= 10:
        return db.query(Ticket).filter(Ticket.id == int(ticket_id)).first()
    return db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()


def auto_close_stale_resolved_tickets(db: Session):
    """Auto-close resolved tickets that have been unacted on for 3+ days"""
    from datetime import timedelta
    cutoff = datetime.now() - timedelta(days=3)

    stale = db.query(Ticket).filter(
        Ticket.status == STATUS_RESOLVED,
        Ticket.closed_at != None,
        Ticket.closed_at <= cutoff,
    ).all()

    for ticket in stale:
        old_status = ticket.status
        ticket.status = STATUS_CLOSED
        ticket.closed_at = datetime.now()
        ticket.updated_at = datetime.now()
        db.add(TicketHistory(
            ticket_id=ticket.id,
            action="AUTO_CLOSE",
            description="Automatically closed after 3 days in resolved status",
            old_status=old_status,
            new_status=STATUS_CLOSED,
            actor_name="system",
        ))

    if stale:
        db.commit()


def apply_ticket_visibility_filter(query, current_user: CurrentUser, oracle_db: Session) -> any:
    """Apply authorization filter berdasarkan user role/team.

    Rules:
    - Admin users & solver employees: lihat semua tickets
    - IT/ENG/PLANT teams: lihat semua tickets (support team)
    - User biasa: lihat hanya tickets yang mereka buat
    """
    team = current_user.team
    requester = current_user.employee_number

    is_admin = (
        current_user.username.lower() in ADMIN_USERS
        or requester.lower() in ADMIN_USERS
        or requester in SOLVER_EMPLOYEES
    )

    if not is_admin:
        if team == "USER":
            # Regular user: hanya lihat tickets yang mereka buat
            query = query.filter(Ticket.requester_name == requester)
        # IT/ENG/PLANT teams: lihat semua tickets (no additional filter)

    return query


@router.get("/departments", response_model=List[DepartmentResponse])
def get_departments():
    """Get list of departments (legacy)"""
    return DEPARTMENTS


@router.get("/teams", response_model=List[TeamResponse])
def get_teams(
    oracle_db: Session = Depends(get_oracle_db),
):
    """Get list of teams from Oracle"""
    try:
        teams = get_team_list(oracle_db)
        return teams
    except Exception as e:
        print(f"Error fetching teams from Oracle: {e}")
        return []


@router.get("/my-team", response_model=TeamResponse)
def get_my_team(
    oracle_db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get the Oracle team_id for the currently logged-in user (from PER_ALL_ASSIGNMENTS_F)"""
    try:
        team_id = get_employee_team_id(oracle_db, current_user.employee_number)
        team_desc = get_team_description(oracle_db, team_id) if team_id else None
        return {"team_id": team_id or "", "team_desc": team_desc or ""}
    except Exception as e:
        print(f"Error fetching my-team from Oracle: {e}")
        return {"team_id": "", "team_desc": ""}


@router.get("/", response_model=List[TicketListResponse])
def get_all_tickets(
    db: Session = Depends(get_db),
    oracle_db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get all tickets"""
    auto_close_stale_resolved_tickets(db)

    query = db.query(Ticket)
    query = apply_ticket_visibility_filter(query, current_user, oracle_db)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@router.get("/open", response_model=List[TicketListResponse])
def get_open_tickets(
    db: Session = Depends(get_db),
    oracle_db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get open tickets (status: new, assigned, in_progress)"""
    query = db.query(Ticket).filter(
        Ticket.status.in_([STATUS_NEW, STATUS_ASSIGNED, STATUS_IN_PROGRESS, STATUS_PENDING])
    )

    query = apply_ticket_visibility_filter(query, current_user, oracle_db)

    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@router.get("/closed", response_model=List[TicketListResponse])
def get_closed_tickets(
    db: Session = Depends(get_db),
    oracle_db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get closed tickets (status: resolved, closed, cancelled)"""
    query = db.query(Ticket).filter(
        Ticket.status.in_([STATUS_RESOLVED, STATUS_CLOSED, STATUS_CANCELLED])
    )

    query = apply_ticket_visibility_filter(query, current_user, oracle_db)

    tickets = query.order_by(Ticket.closed_at.desc().nullsfirst()).all()
    return tickets


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get ticket detail by ticket_id or numeric id"""
    auto_close_stale_resolved_tickets(db)
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
    description: str = Form(...),
    department: str = Form(...),
    category: str = Form(...),
    priority: Optional[str] = Form("medium"),
    files: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    oracle_db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Create new ticket"""
    requester_name = current_user.employee_number
    requester_username = current_user.username

    # Enrich with Oracle data
    # requester_fullname from requester's employee record
    # team_id/team_desc from destination team (department form field = Oracle flex_value)
    requester_fullname = None
    team_desc = None
    try:
        requester_fullname = get_employee_name(oracle_db, requester_name)
        team_desc = get_team_description(oracle_db, department)
    except Exception as e:
        print(f"Warning: Could not fetch Oracle employee info: {e}")

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
        requester_fullname=requester_fullname,
        team_id=department,
        team_desc=team_desc,
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
    oracle_db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Assign PIC to ticket"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    old_status = ticket.status

    # Enrich PIC fullname from Oracle
    pic_fullname = None
    try:
        pic_fullname = get_employee_name(oracle_db, data.pic_name)
    except Exception as e:
        print(f"Warning: Could not fetch PIC name from Oracle: {e}")

    # Update ticket
    ticket.pic_id = data.pic_id
    ticket.pic_name = data.pic_name
    ticket.pic_fullname = pic_fullname
    ticket.pic_assigned_at = datetime.now()
    ticket.status = STATUS_IN_PROGRESS
    ticket.updated_at = datetime.now()

    # Create history entry
    display_name = pic_fullname or data.pic_name
    history = TicketHistory(
        ticket_id=ticket.id,
        action="ASSIGN",
        description=data.description or f"Assigned to {display_name}",
        old_status=old_status,
        new_status=STATUS_IN_PROGRESS,
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
    """Resolve/finish ticket - only IT and PLANT teams, or solver employees"""
    if current_user.team not in RESOLVE_TEAMS and current_user.employee_number not in SOLVER_EMPLOYEES:
        raise HTTPException(
            status_code=403,
            detail="Only IT and PLANT teams can resolve tickets"
        )

    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status not in [STATUS_IN_PROGRESS, STATUS_PENDING]:
        raise HTTPException(
            status_code=400,
            detail="Only in_progress or pending tickets can be resolved"
        )

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


@router.patch("/{ticket_id}/postpone")
def postpone_ticket(
    ticket_id: str,
    data: TicketPostpone,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Postpone ticket - set status to pending. Only IT and PLANT teams, or solver employees."""
    if current_user.team not in RESOLVE_TEAMS and current_user.employee_number not in SOLVER_EMPLOYEES:
        raise HTTPException(
            status_code=403,
            detail="Only IT and PLANT teams can postpone tickets"
        )

    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status not in [STATUS_IN_PROGRESS, STATUS_PENDING]:
        raise HTTPException(
            status_code=400,
            detail="Only in_progress or pending tickets can be postponed"
        )

    old_status = ticket.status
    ticket.status = STATUS_PENDING
    ticket.updated_at = datetime.now()

    history = TicketHistory(
        ticket_id=ticket.id,
        action="POSTPONE",
        description=data.description or "Ticket postponed",
        old_status=old_status,
        new_status=STATUS_PENDING,
        actor_name=current_user.employee_number,
    )
    db.add(history)

    db.commit()
    return {"message": "Ticket postponed", "ticket_id": ticket_id}


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


@router.patch("/{ticket_id}/close")
def close_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Close a resolved ticket - only the requester can close"""
    ticket = find_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.status != STATUS_RESOLVED:
        raise HTTPException(
            status_code=400,
            detail="Ticket must be in resolved status before closing"
        )

    if ticket.requester_name != current_user.employee_number:
        raise HTTPException(
            status_code=403,
            detail="Only the requester can close a resolved ticket"
        )

    old_status = ticket.status
    ticket.status = STATUS_CLOSED
    ticket.closed_at = datetime.now()
    ticket.updated_at = datetime.now()

    history = TicketHistory(
        ticket_id=ticket.id,
        action="CLOSE",
        description="Ticket closed by requester",
        old_status=old_status,
        new_status=STATUS_CLOSED,
        actor_name=current_user.employee_number,
    )
    db.add(history)

    db.commit()
    return {"message": "Ticket closed", "ticket_id": ticket_id}
