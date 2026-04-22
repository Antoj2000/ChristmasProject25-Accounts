from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Boolean

class Base(DeclarativeBase):
    pass

class AccountsDB(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_no: Mapped[str] = mapped_column (String(6), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    #password: Mapped[str] = mapped_column(String(50), unique=False, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    range_start: Mapped[int] = mapped_column(Integer, nullable=False)
    range_end: Mapped[int] = mapped_column(Integer, nullable=False)
    current_con_num: Mapped[int] = mapped_column(Integer, nullable=False)
    phone_numbers: Mapped[list["PhoneNumberDB"]] = relationship(
        "PhoneNumberDB",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    emails: Mapped[list["EmailDB"]] = relationship(
        "EmailDB",
        back_populates="account",
        cascade="all, delete-orphan",
    )
    addresses: Mapped[list["AddressDB"]] = relationship(
        "AddressDB",
        back_populates="account",
        cascade="all, delete-orphan",
    )

class PhoneNumberDB(Base):
    """Stores a phone number associated with an account."""
    __tablename__ = "phone_numbers"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(20), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    account: Mapped[AccountsDB] = relationship(
        "AccountsDB",
        back_populates="phone_numbers",
    )


class EmailDB(Base):
    """Stores an email address associated with an account."""
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    account: Mapped[AccountsDB] = relationship(
        "AccountsDB",
        back_populates="emails",
    )


class AddressDB(Base):
    """Stores a delivery address associated with an account."""
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    line1: Mapped[str] = mapped_column(String(100), nullable=False)
    line2: Mapped[str] = mapped_column(String(100), nullable=True)
    line3: Mapped[str] = mapped_column(String(100), nullable=True)
    line4: Mapped[str] = mapped_column(String(100), nullable=True)
    eircode: Mapped[str] = mapped_column(String(10), nullable=True)
    type: Mapped[str] = mapped_column(String(20), nullable=False, default="home")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    account: Mapped[AccountsDB] = relationship(
        "AccountsDB",
        back_populates="addresses",
    )
    

