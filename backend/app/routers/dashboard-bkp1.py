from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db, get_oracle_db
from app.dependencies import get_current_user, CurrentUser
from app.models.ticket import Ticket
from app.schemas.ticket import DashboardStats

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Status constants
STATUS_NEW = "new"
STATUS_ASSIGNED = "assigned"
STATUS_IN_PROGRESS = "in_progress"
STATUS_RESOLVED = "resolved"
STATUS_CLOSED = "closed"
STATUS_CANCELLED = "cancelled"


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get dashboard statistics from PostgreSQL"""
    from sqlalchemy import or_, func, extract
    from datetime import datetime

    team = current_user.team
    requester = current_user.employee_number
    current_month = datetime.now().month
    current_year = datetime.now().year

    print(f"[DEBUG] Dashboard stats - team: {team}, requester: {requester}")

    # Base query - filter by user's access
    if team == "USER":
        base_filter = Ticket.requester_name == requester
    elif team in ["IT", "ENG"]:
        base_filter = or_(Ticket.department == team, Ticket.requester_name == requester)
    else:
        base_filter = True

    # Count by status
    open_count = db.query(Ticket).filter(base_filter, Ticket.status == STATUS_NEW).count()

    in_progress_count = db.query(Ticket).filter(
        base_filter,
        Ticket.status.in_([STATUS_ASSIGNED, STATUS_IN_PROGRESS])
    ).count()

    closed_count = db.query(Ticket).filter(
        base_filter,
        Ticket.status.in_([STATUS_RESOLVED, STATUS_CLOSED])
    ).count()

    cancelled_count = db.query(Ticket).filter(base_filter, Ticket.status == STATUS_CANCELLED).count()

    total_count = db.query(Ticket).filter(base_filter).count()

    # This month counts
    new_this_month = db.query(Ticket).filter(
        base_filter,
        extract('month', Ticket.created_at) == current_month,
        extract('year', Ticket.created_at) == current_year
    ).count()

    closed_this_month = db.query(Ticket).filter(
        base_filter,
        Ticket.status.in_([STATUS_RESOLVED, STATUS_CLOSED]),
        extract('month', Ticket.closed_at) == current_month,
        extract('year', Ticket.closed_at) == current_year
    ).count()

    # Tickets by priority
    priority_stats = db.query(Ticket.priority, func.count(Ticket.id)).filter(
        base_filter
    ).group_by(Ticket.priority).all()
    tickets_by_priority = {p or 'unset': c for p, c in priority_stats}

    # Tickets by department
    dept_stats = db.query(Ticket.department, func.count(Ticket.id)).filter(
        base_filter
    ).group_by(Ticket.department).all()
    tickets_by_department = {d or 'unset': c for d, c in dept_stats}

    print(f"[DEBUG] Stats - open: {open_count}, progress: {in_progress_count}, closed: {closed_count}, total: {total_count}")

    return DashboardStats(
        total_tickets=total_count,
        open_tickets=open_count,
        in_progress_tickets=in_progress_count,
        closed_tickets=closed_count,
        cancelled_tickets=cancelled_count,
        new_this_month=new_this_month,
        closed_this_month=closed_this_month,
        tickets_by_priority=tickets_by_priority,
        tickets_by_department=tickets_by_department,
    )


@router.get("/users")
def get_users(
    db: Session = Depends(get_oracle_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get list of users for PIC assignment from Oracle VUSER_TICKET"""
    query = text("""
        SELECT PERSON_ID, TRIM(EMPLOYEE_NUMBER) AS EMPLOYEE_NUMBER,
               TRIM(LOCAL_NAME) AS LOCAL_NAME, TRIM(DEPT) AS DEPT, TRIM(TEAM) AS TEAM
        FROM VUSER_TICKET
        WHERE PERSON_ID IS NOT NULL AND TEAM IN ('IT', 'ENG', 'ADM')
    """)
    result = db.execute(query)

    users = []
    for row in result:
        users.append({
            "person_id": row[0],
            "employee_number": row[1],
            "full_name": row[2],
            "department": row[3],
            "team": row[4],
        })
    return users


@router.get("/recent")
def get_recent_tickets(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """Get recent tickets for dashboard"""
    team = current_user.team
    requester = current_user.employee_number

    query = db.query(Ticket)

    if team == "USER":
        query = query.filter(Ticket.requester_name == requester)
    elif team in ["IT", "ENG"]:
        query = query.filter(
            (Ticket.department == team) | (Ticket.requester_name == requester)
        )

    tickets = query.order_by(Ticket.created_at.desc()).limit(limit).all()

    return [
        {
            "id": t.id,
            "ticket_id": t.ticket_id,
            "title": t.title,
            "department": t.department,
            "status": t.status,
            "priority": t.priority,
            "requester_name": t.requester_name,
            "pic_name": t.pic_name,
            "created_at": t.created_at,
        }
        for t in tickets
    ]
