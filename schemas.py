from pydantic import BaseModel, EmailStr
from typing import Optional
from enum import Enum


# ── Shared ────────────────────────────────────────────────────────────────────

class OrgScope(str, Enum):
    region  = "region"
    cluster = "cluster"
    branch  = "branch"


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class TokenResponse(BaseModel):
    access_token:  str
    refresh_token: str
    user:          dict

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str


# ── Role ──────────────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name:  str  # e.g. 'region_manager'
    label: str  # e.g. 'Region Manager'
    level: int  # e.g. 2  (lower = higher authority)

class RoleUpdate(BaseModel):
    label: Optional[str] = None
    level: Optional[int] = None
    # name is not updatable — used as key in business logic

class RoleOut(BaseModel):
    id:    int
    name:  str
    label: str
    level: int

    class Config:
        from_attributes = True


# ── Region ────────────────────────────────────────────────────────────────────

class RegionCreate(BaseModel):
    name: str
    code: str

class RegionUpdate(BaseModel):
    name:      Optional[str]  = None
    code:      Optional[str]  = None
    is_active: Optional[bool] = None

class RegionOut(BaseModel):
    id:        int
    name:      str
    code:      str
    is_active: bool

    class Config:
        from_attributes = True


# ── Cluster ───────────────────────────────────────────────────────────────────

class ClusterCreate(BaseModel):
    region_id: int
    name:      str
    code:      str

class ClusterUpdate(BaseModel):
    name:      Optional[str]  = None
    code:      Optional[str]  = None
    is_active: Optional[bool] = None

class ClusterOut(BaseModel):
    id:        int
    region_id: int
    name:      str
    code:      str
    is_active: bool

    class Config:
        from_attributes = True


# ── Branch ────────────────────────────────────────────────────────────────────

class BranchCreate(BaseModel):
    cluster_id: int
    name:       str
    code:       str
    address:    Optional[str] = None

class BranchUpdate(BaseModel):
    name:      Optional[str]  = None
    code:      Optional[str]  = None
    address:   Optional[str]  = None
    is_active: Optional[bool] = None

class BranchOut(BaseModel):
    id:                int
    cluster_id:        int
    name:              str
    code:              str
    address:           Optional[str]
    is_active:         bool
    branch_manager_id: Optional[int]

    class Config:
        from_attributes = True

class BranchDetailOut(BaseModel):
    """Used for GET /branches and GET /branches/{id} — includes full hierarchy context."""
    id:                int
    name:              str
    code:              str
    address:           Optional[str]
    is_active:         bool
    branch_manager_id: Optional[int]
    cluster_id:        int
    cluster_name:      str
    cluster_code:      str
    region_id:         int
    region_name:       str
    region_code:       str

    class Config:
        from_attributes = True

    @classmethod
    def from_branch(cls, branch):
        return cls(
            id                = branch.id,
            name              = branch.name,
            code              = branch.code,
            address           = branch.address,
            is_active         = branch.is_active,
            branch_manager_id = branch.branch_manager_id,
            cluster_id        = branch.cluster.id,
            cluster_name      = branch.cluster.name,
            cluster_code      = branch.cluster.code,
            region_id         = branch.cluster.region.id,
            region_name       = branch.cluster.region.name,
            region_code       = branch.cluster.region.code,
        )

class AssignBranchManager(BaseModel):
    user_id: int


# ── Scheme ────────────────────────────────────────────────────────────────────

class DepositType(str, Enum):
    lump_sum  = "lump_sum"    # one-time deposit (FD, SFD, MIS, etc.)
    recurring = "recurring"   # monthly installments (RD, Gold)
    daily     = "daily"       # daily deposits (DDS)

class PayoutType(str, Enum):
    cash         = "cash"          # principal + interest at maturity
    cash_monthly = "cash_monthly"  # interest paid monthly (MIS, DharmaNidhi)
    gold_bonus   = "gold_bonus"    # paid amount + bonus months (GK Gold)

class LockInType(str, Enum):
    days         = "days"          # lock-in for X days (SFD=30d, DDS=90d)
    complete     = "complete"      # no withdrawal until full tenure
    half_tenure  = "half_tenure"   # lock-in for first half of chosen tenure (RD)

class RateType(str, Enum):
    slab_rate      = "slab_rate"      # different rates per tenure, general+senior (SFD, FD)
    single_rate    = "single_rate"    # one rate per slab, no senior split (RD, DDS, MIS)
    compound       = "compound"       # yearly compound interest (Sowbhagya, Bhavishya)
    bonus_months   = "bonus_months"   # bonus months on maturity (GK Gold)
    fixed_maturity = "fixed_maturity" # fixed known maturity amount (Samrudhi, Srinidhi)

class PreMaturityType(str, Enum):
    reduce_rate         = "reduce_rate"          # -X% from available rate (SFD, FD)
    simple_interest     = "simple_interest"      # flat SI % given (Srinidhi, Double)
    convert_to_fd       = "convert_to_fd"        # convert to FD slab - 2% - monthly paid (MIS)
    percent_on_deposit  = "percent_on_deposit"   # -X% on deposited amount (DDS, RD)
    not_applicable      = "not_applicable"       # not allowed (GK Gold)

class ForcedPreType(str, Enum):
    no_interest_flat_charge = "no_interest_flat_charge"  # No IR + 0.5%/₹118 lower (most schemes)
    percent_on_deposit      = "percent_on_deposit"       # -X% on deposited (RD, DDS)


# ── Tenure Slab In/Out ────────────────────────────────────────────────────────

class TenureSlabIn(BaseModel):
    tenure_label:          str            # "31-180 Days", "1 Year", "6.6 Years"
    tenure_months:         Optional[int]  = None   # numeric, for calculations
    rate_general:          Optional[int]  = None   # x100: 700 = 7.00%
    rate_senior:           Optional[int]  = None   # x100: 750 = 7.50%
    bonus_months:          Optional[int]  = None   # for gold_bonus payout
    fixed_maturity_amount: Optional[int]  = None   # for fixed_maturity rate type
    base_deposit_amount:   Optional[int]  = None   # base deposit for fixed maturity
    sort_order:            int            = 0

class TenureSlabOut(BaseModel):
    id:                    int
    tenure_label:          str
    tenure_months:         Optional[int]
    rate_general:          Optional[int]
    rate_senior:           Optional[int]
    bonus_months:          Optional[int]
    fixed_maturity_amount: Optional[int]
    base_deposit_amount:   Optional[int]
    sort_order:            int

    class Config:
        from_attributes = True


# ── Scheme Criteria In/Out ────────────────────────────────────────────────────

class SchemeCriteriaIn(BaseModel):
    point: str
    order: int = 0

class SchemeCriteriaOut(BaseModel):
    id:    int
    point: str
    order: int

    class Config:
        from_attributes = True


# ── Scheme Create / Update / Out ──────────────────────────────────────────────

class SchemeCreate(BaseModel):
    name:         str
    code:         str
    description:  Optional[str] = None
    deposit_type: DepositType
    payout_type:  PayoutType
    min_amount:   int
    multiples_of: Optional[int] = None

    # Lock-in
    lock_in_type: LockInType
    lock_in_days: Optional[int] = None   # required when lock_in_type = 'days'

    # Rate structure
    rate_type:    RateType
    flat_rate:    Optional[int] = None   # x100, required for single_rate/compound/fixed_maturity

    # Tenure slabs — at least one required
    tenure_slabs: list[TenureSlabIn]

    # Loan
    loan_available:            bool            = False
    loan_eligible_from:        Optional[str]   = None   # 'next_day' | 'after_days'
    loan_eligible_after_days:  Optional[int]   = None
    loan_max_percentage:       Optional[int]   = None   # e.g. 80
    loan_rate_type:            Optional[str]   = None   # 'plus_on_deposit_rate' | 'fixed_rate'
    loan_rate_value:           Optional[int]   = None   # x100

    # Forced pre-maturity (before lock-in)
    forced_pre_type:               Optional[ForcedPreType] = None
    forced_pre_charge_percentage:  Optional[int]           = None   # x100, e.g. 50 = 0.5%
    forced_pre_charge_flat:        Optional[int]           = None   # e.g. 118
    forced_pre_percent_on_deposit: Optional[int]           = None   # x100

    # Pre-maturity (after lock-in)
    pre_maturity_allowed:           bool                    = False
    pre_maturity_type:              Optional[PreMaturityType] = None
    pre_maturity_rate_reduction:    Optional[int]           = None   # x100
    pre_maturity_si_rate:           Optional[int]           = None   # x100
    pre_maturity_percent_on_deposit: Optional[int]          = None   # x100

    # Criteria
    criteria: list[SchemeCriteriaIn] = []

    def model_post_init(self, __context):
        if self.lock_in_type == LockInType.days and not self.lock_in_days:
            raise ValueError("lock_in_days required when lock_in_type is 'days'")
        if not self.tenure_slabs:
            raise ValueError("At least one tenure slab is required")
        if self.loan_available:
            if not self.loan_eligible_from:
                raise ValueError("loan_eligible_from required when loan_available is true")
            if not self.loan_max_percentage:
                raise ValueError("loan_max_percentage required when loan_available is true")
        if self.pre_maturity_allowed and not self.pre_maturity_type:
            raise ValueError("pre_maturity_type required when pre_maturity_allowed is true")


class SchemeUpdate(BaseModel):
    name:         Optional[str]         = None
    description:  Optional[str]         = None
    deposit_type: Optional[DepositType] = None
    payout_type:  Optional[PayoutType]  = None
    min_amount:   Optional[int]         = None
    multiples_of: Optional[int]         = None
    is_active:    Optional[bool]        = None
    lock_in_type: Optional[LockInType]  = None
    lock_in_days: Optional[int]         = None
    flat_rate:    Optional[int]         = None

    loan_available:            Optional[bool] = None
    loan_eligible_from:        Optional[str]  = None
    loan_eligible_after_days:  Optional[int]  = None
    loan_max_percentage:       Optional[int]  = None
    loan_rate_type:            Optional[str]  = None
    loan_rate_value:           Optional[int]  = None

    forced_pre_type:               Optional[ForcedPreType]   = None
    forced_pre_charge_percentage:  Optional[int]             = None
    forced_pre_charge_flat:        Optional[int]             = None
    forced_pre_percent_on_deposit: Optional[int]             = None

    pre_maturity_allowed:            Optional[bool]             = None
    pre_maturity_type:               Optional[PreMaturityType]  = None
    pre_maturity_rate_reduction:     Optional[int]              = None
    pre_maturity_si_rate:            Optional[int]              = None
    pre_maturity_percent_on_deposit: Optional[int]              = None


class SchemeOut(BaseModel):
    id:           int
    name:         str
    code:         str
    description:  Optional[str]
    deposit_type: str
    payout_type:  str
    min_amount:   int
    multiples_of: Optional[int]
    is_active:    bool

    lock_in_type: str
    lock_in_days: Optional[int]
    rate_type:    str
    flat_rate:    Optional[int]

    loan_available:            bool
    loan_eligible_from:        Optional[str]
    loan_eligible_after_days:  Optional[int]
    loan_max_percentage:       Optional[int]
    loan_rate_type:            Optional[str]
    loan_rate_value:           Optional[int]

    forced_pre_type:               Optional[str]
    forced_pre_charge_percentage:  Optional[int]
    forced_pre_charge_flat:        Optional[int]
    forced_pre_percent_on_deposit: Optional[int]

    pre_maturity_allowed:            bool
    pre_maturity_type:               Optional[str]
    pre_maturity_rate_reduction:     Optional[int]
    pre_maturity_si_rate:            Optional[int]
    pre_maturity_percent_on_deposit: Optional[int]

    tenure_slabs: list[TenureSlabOut]
    criteria:     list[SchemeCriteriaOut]

    class Config:
        from_attributes = True


class SchemeListOut(BaseModel):
    id:           int
    name:         str
    code:         str
    deposit_type: str
    payout_type:  str
    min_amount:   int
    is_active:    bool
    slab_count:   int

    class Config:
        from_attributes = True


# ── User ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    full_name:     str
    email:         EmailStr
    phone:         Optional[str]      = None
    role_id:       int
    scope_type:    Optional[OrgScope] = None
    scope_id:      Optional[int]      = None
    temp_password: str

class UserUpdate(BaseModel):
    full_name:  Optional[str]      = None
    phone:      Optional[str]      = None
    scope_type: Optional[OrgScope] = None
    scope_id:   Optional[int]      = None

class UserResetPassword(BaseModel):
    new_password: str

class UserOut(BaseModel):
    id:                   int
    full_name:            str
    email:                str
    phone:                Optional[str]
    is_active:            bool
    scope_type:           Optional[str]
    scope_id:             Optional[int]
    must_change_password: bool
    role:                 RoleOut

    class Config:
        from_attributes = True

class UserListOut(BaseModel):
    total:     int
    page:      int
    page_size: int
    results:   list[UserOut]