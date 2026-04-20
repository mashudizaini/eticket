"""
Oracle lookup service for enriching ticket data with employee/team information.
Queries Oracle EBS tables: per_people_f, PER_ALL_ASSIGNMENTS_F, fnd_flex_values_vl
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict


def get_employee_name(oracle_db: Session, employee_number: str) -> Optional[str]:
    """Get last_name from per_people_f by employee_number."""
    if not employee_number:
        return None
    query = text("""
        SELECT p.last_name
        FROM per_people_f p
        WHERE p.employee_number = :emp_no
          AND SYSDATE BETWEEN p.effective_start_date AND p.effective_end_date
          AND ROWNUM = 1
    """)
    result = oracle_db.execute(query, {"emp_no": employee_number.strip()}).fetchone()
    return result[0].strip() if result and result[0] else None


def get_employee_team_id(oracle_db: Session, employee_number: str) -> Optional[str]:
    """Get team_id (ass_attribute30) from PER_ALL_ASSIGNMENTS_F."""
    if not employee_number:
        return None
    query = text("""
        SELECT a.ass_attribute30
        FROM per_people_f p, PER_ALL_ASSIGNMENTS_F a
        WHERE p.PERSON_ID = a.PERSON_ID
          AND p.employee_number = :emp_no
          AND SYSDATE BETWEEN p.effective_start_date AND p.effective_end_date
          AND SYSDATE BETWEEN a.effective_start_date AND a.effective_end_date
          AND a.ass_attribute30 IS NOT NULL
          AND ROWNUM = 1
    """)
    result = oracle_db.execute(query, {"emp_no": employee_number.strip()}).fetchone()
    return result[0].strip() if result and result[0] else None


def get_team_description(oracle_db: Session, team_id: str) -> Optional[str]:
    """Get team description from fnd_flex_values_vl for CKDO_GL_COA_DEPARTMENT."""
    if not team_id:
        return None
    query = text("""
        SELECT ffvv.description
        FROM fnd_flex_values_vl ffvv, fnd_flex_value_sets ffvs
        WHERE ffvv.flex_value_set_id = ffvs.flex_value_set_id
          AND ffvs.flex_value_set_name = 'CKDO_GL_COA_DEPARTMENT'
          AND ffvv.flex_value = :team_id
          AND ROWNUM = 1
    """)
    result = oracle_db.execute(query, {"team_id": team_id.strip()}).fetchone()
    return result[0].strip() if result and result[0] else None


def get_employee_info(oracle_db: Session, employee_number: str) -> Dict[str, Optional[str]]:
    """Get all employee info in one call: last_name, team_id, team_desc."""
    info = {
        "last_name": None,
        "team_id": None,
        "team_desc": None,
    }
    if not employee_number:
        return info

    info["last_name"] = get_employee_name(oracle_db, employee_number)
    info["team_id"] = get_employee_team_id(oracle_db, employee_number)
    if info["team_id"]:
        info["team_desc"] = get_team_description(oracle_db, info["team_id"])

    return info


def get_team_list(oracle_db: Session) -> list:
    """Get all teams from Oracle CKDO_GL_COA_DEPARTMENT value set."""
    query = text("""
        SELECT DISTINCT ffvv.flex_value AS team_id, ffvv.description AS team_desc
        FROM fnd_flex_values_vl ffvv, fnd_flex_value_sets ffvs
        WHERE ffvv.flex_value_set_id = ffvs.flex_value_set_id
          AND ffvs.flex_value_set_name = 'CKDO_GL_COA_DEPARTMENT'
          AND ffvv.enabled_flag = 'Y'
        ORDER BY ffvv.flex_value
    """)
    result = oracle_db.execute(query)
    return [{"team_id": row[0].strip() if row[0] else "", "team_desc": row[1].strip() if row[1] else ""} for row in result]
