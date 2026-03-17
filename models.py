from sqlalchemy import (
    Column, Integer, String, Boolean, ForeignKey, TIMESTAMP, text
)
from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


org_scope_enum = PgEnum("region", "cluster", "branch", name="org_scope", create_type=False)


# ── Roles ─────────────────────────────────────────────────────────────────────

class Role(Base):
    __tablename__ = "roles"

    id    = Column(Integer, primary_key=True)
    name  = Column(String(50),  nullable=False, unique=True)  # 'super_admin', 'agent' etc.
    label = Column(String(100), nullable=False)               # 'Super Admin', 'Agent' etc.
    level = Column(Integer,     nullable=False)               # 1 = highest, 5 = lowest

    users = relationship("User", back_populates="role")


# ── Org Hierarchy ─────────────────────────────────────────────────────────────

class Region(Base):
    __tablename__ = "regions"

    id         = Column(Integer, primary_key=True)
    name       = Column(String(100), nullable=False, unique=True)
    code       = Column(String(20),  nullable=False, unique=True)
    is_active  = Column(Boolean,     nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    clusters   = relationship("Cluster", back_populates="region")


class Cluster(Base):
    __tablename__ = "clusters"

    id         = Column(Integer, primary_key=True)
    region_id  = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name       = Column(String(100), nullable=False)
    code       = Column(String(20),  nullable=False, unique=True)
    is_active  = Column(Boolean,     nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    region   = relationship("Region",  back_populates="clusters")
    branches = relationship("Branch",  back_populates="cluster")


class Branch(Base):
    __tablename__ = "branches"

    id                = Column(Integer, primary_key=True)
    cluster_id        = Column(Integer, ForeignKey("clusters.id"), nullable=False)
    name              = Column(String(100), nullable=False)
    code              = Column(String(20),  nullable=False, unique=True)
    address           = Column(String,      nullable=True)
    is_active         = Column(Boolean,     nullable=False, default=True)
    branch_manager_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at        = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at        = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    cluster        = relationship("Cluster", back_populates="branches")
    branch_manager = relationship("User", foreign_keys=[branch_manager_id])


# ── Users ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id                  = Column(Integer, primary_key=True)
    role_id             = Column(Integer, ForeignKey("roles.id"), nullable=False)
    full_name           = Column(String(150), nullable=False)
    email               = Column(String(150), nullable=False, unique=True)
    phone               = Column(String(20),  nullable=True)
    password_hash       = Column(String,      nullable=False)
    scope_type          = Column(org_scope_enum, nullable=True)  # NULL for super_admin
    scope_id            = Column(Integer,        nullable=True)  # FK resolved at app level
    is_active           = Column(Boolean, nullable=False, default=True)
    # Forces password change on first login after admin creates/resets the account
    must_change_password = Column(Boolean, nullable=False, default=True)
    created_by          = Column(Integer,  ForeignKey("users.id"), nullable=True)
    created_at          = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at          = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    role    = relationship("Role", back_populates="users")
    creator = relationship("User", remote_side="User.id", foreign_keys=[created_by])


# ── Schemes ───────────────────────────────────────────────────────────────────
#
# Deposit types : lump_sum | recurring | daily
# Payout types  : cash | cash_monthly | gold_bonus
# Lock-in types : days | complete | half_tenure
# Rate types    : slab_rate | single_rate | compound | bonus_months | fixed_maturity
# Pre-maturity  : reduce_rate | simple_interest | convert_to_fd | not_applicable
#

class Scheme(Base):
    __tablename__ = "schemes"

    id           = Column(Integer, primary_key=True)
    name         = Column(String(150), nullable=False)
    code         = Column(String(30),  nullable=False, unique=True)
    description  = Column(String,      nullable=True)

    # ── Deposit & Payout ─────────────────────────────────────────────────────
    # deposit_type: lump_sum | recurring | daily
    deposit_type = Column(String(20), nullable=False)
    # payout_type: cash | cash_monthly | gold_bonus
    payout_type  = Column(String(20), nullable=False)

    # ── Amount Rules ─────────────────────────────────────────────────────────
    min_amount   = Column(Integer, nullable=False, default=0)   # in rupees
    multiples_of = Column(Integer, nullable=True)               # deposit must be in multiples of this

    # ── Lock-in ──────────────────────────────────────────────────────────────
    # lock_in_type: days | complete | half_tenure
    lock_in_type = Column(String(20), nullable=False, default="days")
    lock_in_days = Column(Integer,    nullable=True)  # used when lock_in_type = 'days'

    # ── Interest / Rate Type ─────────────────────────────────────────────────
    # rate_type: slab_rate | single_rate | compound | bonus_months | fixed_maturity
    rate_type    = Column(String(20), nullable=False, default="slab_rate")

    # For single_rate / compound schemes — one flat rate
    flat_rate    = Column(Integer, nullable=True)  # stored x100, e.g. 1275 = 12.75%

    # ── Loan Against Deposit ─────────────────────────────────────────────────
    loan_available           = Column(Boolean, nullable=False, default=False)
    # loan_eligible_from: next_day | after_days
    loan_eligible_from       = Column(String(20), nullable=True)
    loan_eligible_after_days = Column(Integer,    nullable=True)  # used when 'after_days'
    loan_max_percentage      = Column(Integer,    nullable=True)  # e.g. 80 = 80%
    # loan_rate_type: plus_on_deposit_rate | fixed_rate
    loan_rate_type           = Column(String(30), nullable=True)
    loan_rate_value          = Column(Integer,    nullable=True)  # x100, e.g. 200 = +2% OR 1800 = 18%

    # ── Forced Pre-Maturity (before lock-in) ─────────────────────────────────
    # forced_pre_type: no_interest_flat_charge | percent_on_deposit
    forced_pre_type              = Column(String(30), nullable=True)
    # for no_interest_flat_charge: 0.5% or ₹118 whichever is lower
    forced_pre_charge_percentage = Column(Integer, nullable=True)  # x100, e.g. 50 = 0.5%
    forced_pre_charge_flat       = Column(Integer, nullable=True)  # flat ₹ amount, e.g. 118
    # for percent_on_deposit: e.g. -5% on deposited amount
    forced_pre_percent_on_deposit = Column(Integer, nullable=True)  # x100

    # ── Pre-Maturity (after lock-in) ─────────────────────────────────────────
    # pre_maturity_allowed: true | false
    pre_maturity_allowed = Column(Boolean, nullable=False, default=False)
    # pre_maturity_type: reduce_rate | simple_interest | convert_to_fd | percent_on_deposit | not_applicable
    pre_maturity_type    = Column(String(30), nullable=True)
    # for reduce_rate: subtract this % from available rate
    pre_maturity_rate_reduction  = Column(Integer, nullable=True)  # x100, e.g. 200 = -2%
    # for simple_interest: give this flat SI %
    pre_maturity_si_rate         = Column(Integer, nullable=True)  # x100, e.g. 400 = 4%
    # for percent_on_deposit: deduct this % from deposited amount
    pre_maturity_percent_on_deposit = Column(Integer, nullable=True)  # x100

    is_active  = Column(Boolean,  nullable=False, default=True)
    created_by = Column(Integer,  ForeignKey("users.id"), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    tenure_slabs = relationship("TenureSlab",    back_populates="scheme", cascade="all, delete-orphan")
    criteria     = relationship("SchemeCriteria", back_populates="scheme", cascade="all, delete-orphan")
    creator      = relationship("User", foreign_keys=[created_by])


class TenureSlab(Base):
    """
    One row per tenure option on a scheme.

    Handles all rate types:
      - slab_rate     → rate_general + rate_senior (FD, SFD)
      - single_rate   → rate_general only (RD, DDS)
      - compound      → rate_general as compound rate (Sowbhagya, Bhavishya)
      - bonus_months  → bonus_months field (GK Gold)
      - fixed_maturity→ fixed_maturity_amount for a base deposit (Samrudhi, Sowbhagya)

    tenure_label is free text for display: "31-180 Days", "1 Year", "6.6 Years", etc.
    tenure_months is the numeric equivalent for calculations.
    """
    __tablename__ = "tenure_slabs"

    id                    = Column(Integer, primary_key=True)
    scheme_id             = Column(Integer, ForeignKey("schemes.id"), nullable=False)
    tenure_label          = Column(String(50),  nullable=False)   # display label
    tenure_months         = Column(Integer,     nullable=True)    # for calculation
    rate_general          = Column(Integer,     nullable=True)    # x100, below 60 age
    rate_senior           = Column(Integer,     nullable=True)    # x100, 60+ age
    bonus_months          = Column(Integer,     nullable=True)    # for gold_bonus payout
    fixed_maturity_amount = Column(Integer,     nullable=True)    # for fixed maturity schemes
    base_deposit_amount   = Column(Integer,     nullable=True)    # base deposit for fixed maturity
    sort_order            = Column(Integer,     nullable=False, default=0)

    scheme = relationship("Scheme", back_populates="tenure_slabs")


class SchemeCriteria(Base):
    """Free-text eligibility / condition points for a scheme."""
    __tablename__ = "scheme_criteria"

    id        = Column(Integer, primary_key=True)
    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)
    point     = Column(String,  nullable=False)
    order     = Column(Integer, nullable=False, default=0)

    scheme = relationship("Scheme", back_populates="criteria")


# ── Sessions ──────────────────────────────────────────────────────────────────

class UserSession(Base):
    __tablename__ = "user_sessions"

    id            = Column(Integer, primary_key=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    refresh_token = Column(String,  nullable=False, unique=True)
    ip_address    = Column(String(50), nullable=True)
    user_agent    = Column(String,     nullable=True)
    expires_at    = Column(TIMESTAMP(timezone=True), nullable=False)
    revoked_at    = Column(TIMESTAMP(timezone=True), nullable=True)  # NULL = active
    created_at    = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User")