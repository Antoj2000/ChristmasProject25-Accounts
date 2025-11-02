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