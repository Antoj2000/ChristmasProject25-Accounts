from sqlalchemy.orm import Session
from .models import AccountsDB

RANGE_SIZE = 500

def assign_number_range(db: Session):

    last_account = db.query(AccountsDB).order_by(AccountsDB.range_end.desc()).first()

    if last_account:
        start = last_account.range_end + 1
    else:
        start = 1

    end = start + RANGE_SIZE -1
    return start, end

def generate_next_account_no(db: Session) -> str:
    last_account = db.query(AccountsDB).order_by(AccountsDB.id.desc()).first()

    if last_account and last_account.account_no:
        last_number = int(last_account.account_no[1:])
        next_number = last_number + 1
    else:
        next_number = 1

    return f"A{next_number:05d}"