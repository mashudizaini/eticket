"""
Backfill script to update existing tickets with Oracle employee/team data.
Run this once to enrich existing tickets with:
  - requester_fullname (from per_people_f)
  - team_id (from PER_ALL_ASSIGNMENTS_F)
  - team_desc (from fnd_flex_values_vl)
  - pic_fullname (from per_people_f)

Usage:
  python backfill_oracle_fields.py

In Docker:
  docker compose exec backend python backfill_oracle_fields.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, OracleSessionLocal
from app.models.ticket import Ticket
from app.services.oracle_lookup import get_employee_info, get_employee_name


def backfill():
    pg_db = SessionLocal()
    oracle_db = OracleSessionLocal()

    try:
        tickets = pg_db.query(Ticket).all()
        total = len(tickets)
        updated = 0
        errors = 0

        print(f"Found {total} tickets to process...")

        # Cache to avoid repeated Oracle queries
        emp_cache = {}
        name_cache = {}

        for i, ticket in enumerate(tickets):
            try:
                changed = False

                # Enrich requester info
                if ticket.requester_name and not ticket.requester_fullname:
                    emp_no = ticket.requester_name.strip()
                    if emp_no not in emp_cache:
                        emp_cache[emp_no] = get_employee_info(oracle_db, emp_no)
                    info = emp_cache[emp_no]

                    if info["last_name"]:
                        ticket.requester_fullname = info["last_name"]
                        changed = True
                    if info["team_id"] and not ticket.team_id:
                        ticket.team_id = info["team_id"]
                        changed = True
                    if info["team_desc"] and not ticket.team_desc:
                        ticket.team_desc = info["team_desc"]
                        changed = True

                # Enrich PIC info
                if ticket.pic_name and not ticket.pic_fullname:
                    pic_no = ticket.pic_name.strip()
                    if pic_no not in name_cache:
                        name_cache[pic_no] = get_employee_name(oracle_db, pic_no)
                    pic_fullname = name_cache[pic_no]

                    if pic_fullname:
                        ticket.pic_fullname = pic_fullname
                        changed = True

                if changed:
                    updated += 1

                if (i + 1) % 50 == 0:
                    pg_db.commit()
                    print(f"  Processed {i + 1}/{total} tickets ({updated} updated)...")

            except Exception as e:
                errors += 1
                print(f"  Error processing ticket {ticket.ticket_id}: {e}")

        pg_db.commit()
        print(f"\nDone! Processed {total} tickets: {updated} updated, {errors} errors.")

    except Exception as e:
        print(f"Fatal error: {e}")
        pg_db.rollback()
    finally:
        pg_db.close()
        oracle_db.close()


if __name__ == "__main__":
    backfill()
