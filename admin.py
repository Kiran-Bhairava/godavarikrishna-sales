from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional
from database import get_db
from dependencies import require_role, get_current_user
from security import hash_password
from models import User, Role, Region, Cluster, Branch, Scheme, TenureSlab, SchemeCriteria
from schemas import (
    RoleCreate, RoleUpdate, RoleOut,
    RegionCreate, RegionUpdate, RegionOut,
    ClusterCreate, ClusterUpdate, ClusterOut,
    BranchCreate, BranchUpdate, BranchOut, BranchDetailOut,
    AssignBranchManager,
    SchemeCreate, SchemeUpdate, SchemeOut, SchemeListOut,
    TenureSlabIn, SchemeCriteriaIn,
    UserCreate, UserUpdate, UserResetPassword, UserOut, UserListOut,
)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Roles that must have a scope assigned
SCOPED_ROLES = {"region_manager", "cluster_manager", "branch_manager", "agent"}

# Reusable super_admin guard
super_admin = Depends(require_role("super_admin"))


# ── Util ──────────────────────────────────────────────────────────────────────

def _get_or_404(db: Session, model, record_id: int, label: str):
    obj = db.query(model).filter(model.id == record_id).first()
    if not obj:
        raise HTTPException(404, f"{label} not found")
    return obj


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.post("/roles", response_model=RoleOut)
def create_role(data: RoleCreate, db: Session = Depends(get_db), _=super_admin):
    if db.query(Role).filter(Role.name == data.name).first():
        raise HTTPException(400, "Role name already exists")
    role = Role(**data.model_dump())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


@router.get("/roles", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), _=super_admin):
    return db.query(Role).order_by(Role.level).all()


@router.get("/roles/{role_id}", response_model=RoleOut)
def get_role(role_id: int, db: Session = Depends(get_db), _=super_admin):
    return _get_or_404(db, Role, role_id, "Role")


@router.patch("/roles/{role_id}", response_model=RoleOut)
def update_role(role_id: int, data: RoleUpdate, db: Session = Depends(get_db), _=super_admin):
    role = _get_or_404(db, Role, role_id, "Role")
    if role.name == "super_admin":
        raise HTTPException(400, "super_admin role cannot be modified")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(role, field, value)
    db.commit()
    db.refresh(role)
    return role


# ── Regions ───────────────────────────────────────────────────────────────────

@router.post("/regions", response_model=RegionOut)
def create_region(data: RegionCreate, db: Session = Depends(get_db), _=super_admin):
    if db.query(Region).filter(Region.code == data.code).first():
        raise HTTPException(400, "Region code already exists")
    region = Region(**data.model_dump())
    db.add(region)
    db.commit()
    db.refresh(region)
    return region


@router.get("/regions", response_model=list[RegionOut])
def list_regions(db: Session = Depends(get_db), _=super_admin):
    return db.query(Region).order_by(Region.name).all()


@router.get("/regions/{region_id}", response_model=RegionOut)
def get_region(region_id: int, db: Session = Depends(get_db), _=super_admin):
    return _get_or_404(db, Region, region_id, "Region")


@router.patch("/regions/{region_id}", response_model=RegionOut)
def update_region(region_id: int, data: RegionUpdate, db: Session = Depends(get_db), _=super_admin):
    region = _get_or_404(db, Region, region_id, "Region")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(region, field, value)
    db.commit()
    db.refresh(region)
    return region


# ── Clusters ──────────────────────────────────────────────────────────────────

@router.post("/clusters", response_model=ClusterOut)
def create_cluster(data: ClusterCreate, db: Session = Depends(get_db), _=super_admin):
    _get_or_404(db, Region, data.region_id, "Region")
    if db.query(Cluster).filter(Cluster.code == data.code).first():
        raise HTTPException(400, "Cluster code already exists")
    cluster = Cluster(**data.model_dump())
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    return cluster


@router.get("/clusters", response_model=list[ClusterOut])
def list_clusters(region_id: Optional[int] = None, db: Session = Depends(get_db), _=super_admin):
    q = db.query(Cluster)
    if region_id:
        q = q.filter(Cluster.region_id == region_id)
    return q.order_by(Cluster.name).all()


@router.get("/clusters/{cluster_id}", response_model=ClusterOut)
def get_cluster(cluster_id: int, db: Session = Depends(get_db), _=super_admin):
    return _get_or_404(db, Cluster, cluster_id, "Cluster")


@router.patch("/clusters/{cluster_id}", response_model=ClusterOut)
def update_cluster(cluster_id: int, data: ClusterUpdate, db: Session = Depends(get_db), _=super_admin):
    cluster = _get_or_404(db, Cluster, cluster_id, "Cluster")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(cluster, field, value)
    db.commit()
    db.refresh(cluster)
    return cluster


# ── Branches ──────────────────────────────────────────────────────────────────

@router.post("/branches", response_model=BranchOut)
def create_branch(data: BranchCreate, db: Session = Depends(get_db), _=super_admin):
    _get_or_404(db, Cluster, data.cluster_id, "Cluster")
    if db.query(Branch).filter(Branch.code == data.code).first():
        raise HTTPException(400, "Branch code already exists")
    branch = Branch(**data.model_dump())
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return branch


@router.get("/branches", response_model=list[BranchDetailOut])
def list_branches(
    cluster_id: Optional[int]  = None,
    region_id:  Optional[int]  = None,
    is_active:  Optional[bool] = None,
    db: Session = Depends(get_db),
    _=super_admin
):
    q = db.query(Branch).join(Branch.cluster).join(Cluster.region)
    if cluster_id is not None: q = q.filter(Branch.cluster_id == cluster_id)
    if region_id  is not None: q = q.filter(Cluster.region_id == region_id)
    if is_active  is not None: q = q.filter(Branch.is_active  == is_active)
    return [BranchDetailOut.from_branch(b) for b in q.order_by(Branch.name).all()]


@router.get("/branches/{branch_id}", response_model=BranchDetailOut)
def get_branch(branch_id: int, db: Session = Depends(get_db), _=super_admin):
    branch = _get_or_404(db, Branch, branch_id, "Branch")
    return BranchDetailOut.from_branch(branch)


@router.patch("/branches/{branch_id}", response_model=BranchOut)
def update_branch(branch_id: int, data: BranchUpdate, db: Session = Depends(get_db), _=super_admin):
    branch = _get_or_404(db, Branch, branch_id, "Branch")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(branch, field, value)
    db.commit()
    db.refresh(branch)
    return branch


@router.patch("/branches/{branch_id}/assign-manager", response_model=BranchOut)
def assign_branch_manager(branch_id: int, data: AssignBranchManager, db: Session = Depends(get_db), _=super_admin):
    branch = _get_or_404(db, Branch, branch_id, "Branch")
    user   = _get_or_404(db, User, data.user_id, "User")

    if user.role.name != "branch_manager":
        raise HTTPException(400, "User must have the branch_manager role")

    if str(user.scope_type) != "branch" or user.scope_id != branch_id:
        raise HTTPException(400, "User is not scoped to this branch")

    branch.branch_manager_id = user.id
    db.commit()
    db.refresh(branch)
    return branch


@router.delete("/branches/{branch_id}/unassign-manager", response_model=BranchOut)
def unassign_branch_manager(branch_id: int, db: Session = Depends(get_db), _=super_admin):
    branch = _get_or_404(db, Branch, branch_id, "Branch")
    branch.branch_manager_id = None
    db.commit()
    db.refresh(branch)
    return branch


# ── Schemes ───────────────────────────────────────────────────────────────────

@router.post("/schemes", response_model=SchemeOut)
def create_scheme(
    data: SchemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin"))
):
    if db.query(Scheme).filter(Scheme.code == data.code.upper()).first():
        raise HTTPException(400, "Scheme code already exists")

    scheme = Scheme(
        name         = data.name,
        code         = data.code.upper(),
        description  = data.description,
        deposit_type = data.deposit_type,
        payout_type  = data.payout_type,
        min_amount   = data.min_amount,
        multiples_of = data.multiples_of,

        lock_in_type = data.lock_in_type,
        lock_in_days = data.lock_in_days,
        rate_type    = data.rate_type,
        flat_rate    = data.flat_rate,

        loan_available           = data.loan_available,
        loan_eligible_from       = data.loan_eligible_from,
        loan_eligible_after_days = data.loan_eligible_after_days,
        loan_max_percentage      = data.loan_max_percentage,
        loan_rate_type           = data.loan_rate_type,
        loan_rate_value          = data.loan_rate_value,

        forced_pre_type               = data.forced_pre_type,
        forced_pre_charge_percentage  = data.forced_pre_charge_percentage,
        forced_pre_charge_flat        = data.forced_pre_charge_flat,
        forced_pre_percent_on_deposit = data.forced_pre_percent_on_deposit,

        pre_maturity_allowed            = data.pre_maturity_allowed,
        pre_maturity_type               = data.pre_maturity_type,
        pre_maturity_rate_reduction     = data.pre_maturity_rate_reduction,
        pre_maturity_si_rate            = data.pre_maturity_si_rate,
        pre_maturity_percent_on_deposit = data.pre_maturity_percent_on_deposit,

        created_by = current_user.id,
    )
    db.add(scheme)
    db.flush()

    for i, slab in enumerate(data.tenure_slabs):
        db.add(TenureSlab(
            scheme_id             = scheme.id,
            tenure_label          = slab.tenure_label,
            tenure_months         = slab.tenure_months,
            rate_general          = slab.rate_general,
            rate_senior           = slab.rate_senior,
            bonus_months          = slab.bonus_months,
            fixed_maturity_amount = slab.fixed_maturity_amount,
            base_deposit_amount   = slab.base_deposit_amount,
            sort_order            = slab.sort_order if slab.sort_order else i,
        ))

    for i, c in enumerate(data.criteria):
        db.add(SchemeCriteria(
            scheme_id = scheme.id,
            point     = c.point,
            order     = c.order if c.order else i,
        ))

    db.commit()
    db.refresh(scheme)
    return scheme


@router.get("/schemes", response_model=list[SchemeListOut])
def list_schemes(
    deposit_type: Optional[str]  = None,
    payout_type:  Optional[str]  = None,
    is_active:    Optional[bool] = None,
    db: Session = Depends(get_db),
    _=super_admin
):
    q = db.query(Scheme)
    if deposit_type is not None: q = q.filter(Scheme.deposit_type == deposit_type)
    if payout_type  is not None: q = q.filter(Scheme.payout_type  == payout_type)
    if is_active    is not None: q = q.filter(Scheme.is_active    == is_active)

    return [
        SchemeListOut(
            id=s.id, name=s.name, code=s.code,
            deposit_type=s.deposit_type, payout_type=s.payout_type,
            min_amount=s.min_amount, is_active=s.is_active,
            slab_count=len(s.tenure_slabs),
        )
        for s in q.order_by(Scheme.name).all()
    ]


@router.get("/schemes/{scheme_id}", response_model=SchemeOut)
def get_scheme(scheme_id: int, db: Session = Depends(get_db), _=super_admin):
    return _get_or_404(db, Scheme, scheme_id, "Scheme")


@router.patch("/schemes/{scheme_id}", response_model=SchemeOut)
def update_scheme(scheme_id: int, data: SchemeUpdate, db: Session = Depends(get_db), _=super_admin):
    scheme = _get_or_404(db, Scheme, scheme_id, "Scheme")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(scheme, field, value)
    db.commit()
    db.refresh(scheme)
    return scheme


# ── Scheme — Tenure Slabs ─────────────────────────────────────────────────────

@router.post("/schemes/{scheme_id}/slabs", response_model=SchemeOut)
def add_tenure_slab(scheme_id: int, data: TenureSlabIn, db: Session = Depends(get_db), _=super_admin):
    scheme = _get_or_404(db, Scheme, scheme_id, "Scheme")
    # Prevent duplicate label on same scheme
    exists = db.query(TenureSlab).filter(
        TenureSlab.scheme_id == scheme_id,
        TenureSlab.tenure_label == data.tenure_label
    ).first()
    if exists:
        raise HTTPException(400, f"Slab '{data.tenure_label}' already exists on this scheme")
    db.add(TenureSlab(
        scheme_id=scheme_id, tenure_label=data.tenure_label,
        tenure_months=data.tenure_months, rate_general=data.rate_general,
        rate_senior=data.rate_senior, bonus_months=data.bonus_months,
        fixed_maturity_amount=data.fixed_maturity_amount,
        base_deposit_amount=data.base_deposit_amount,
        sort_order=data.sort_order,
    ))
    db.commit()
    db.refresh(scheme)
    return scheme


@router.patch("/schemes/{scheme_id}/slabs/{slab_id}", response_model=SchemeOut)
def update_tenure_slab(scheme_id: int, slab_id: int, data: TenureSlabIn, db: Session = Depends(get_db), _=super_admin):
    scheme = _get_or_404(db, Scheme, scheme_id, "Scheme")
    slab = db.query(TenureSlab).filter(
        TenureSlab.id == slab_id, TenureSlab.scheme_id == scheme_id
    ).first()
    if not slab:
        raise HTTPException(404, "Slab not found on this scheme")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(slab, field, value)
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/schemes/{scheme_id}/slabs/{slab_id}", response_model=SchemeOut)
def remove_tenure_slab(scheme_id: int, slab_id: int, db: Session = Depends(get_db), _=super_admin):
    scheme = _get_or_404(db, Scheme, scheme_id, "Scheme")
    slab = db.query(TenureSlab).filter(
        TenureSlab.id == slab_id, TenureSlab.scheme_id == scheme_id
    ).first()
    if not slab:
        raise HTTPException(404, "Slab not found on this scheme")
    if len(scheme.tenure_slabs) <= 1:
        raise HTTPException(400, "Cannot remove the last tenure slab")
    db.delete(slab)
    db.commit()
    db.refresh(scheme)
    return scheme


# ── Scheme — Criteria ─────────────────────────────────────────────────────────

@router.post("/schemes/{scheme_id}/criteria", response_model=SchemeOut)
def add_criteria(scheme_id: int, data: SchemeCriteriaIn, db: Session = Depends(get_db), _=super_admin):
    scheme = _get_or_404(db, Scheme, scheme_id, "Scheme")
    db.add(SchemeCriteria(scheme_id=scheme_id, point=data.point, order=data.order))
    db.commit()
    db.refresh(scheme)
    return scheme


@router.delete("/schemes/{scheme_id}/criteria/{criteria_id}", response_model=SchemeOut)
def remove_criteria(scheme_id: int, criteria_id: int, db: Session = Depends(get_db), _=super_admin):
    scheme   = _get_or_404(db, Scheme, scheme_id, "Scheme")
    criteria = db.query(SchemeCriteria).filter(
        SchemeCriteria.id == criteria_id,
        SchemeCriteria.scheme_id == scheme_id
    ).first()
    if not criteria:
        raise HTTPException(404, "Criteria not found on this scheme")
    db.delete(criteria)
    db.commit()
    db.refresh(scheme)
    return scheme


# ── Users ─────────────────────────────────────────────────────────────────────

@router.post("/users", response_model=UserOut)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("super_admin"))
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already in use")

    role = _get_or_404(db, Role, data.role_id, "Role")

    if role.name in SCOPED_ROLES and not (data.scope_type and data.scope_id):
        raise HTTPException(400, f"Role '{role.label}' requires scope_type and scope_id")

    if role.name == "super_admin" and (data.scope_type or data.scope_id):
        raise HTTPException(400, "Super admin cannot have an org scope")

    user = User(
        role_id       = data.role_id,
        full_name     = data.full_name,
        email         = data.email,
        phone         = data.phone,
        password_hash = hash_password(data.temp_password),
        scope_type    = data.scope_type,
        scope_id      = data.scope_id,
        created_by    = current_user.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=UserListOut)
def list_users(
    role_id:    Optional[int]  = Query(None),
    scope_type: Optional[str]  = Query(None),
    scope_id:   Optional[int]  = Query(None),
    search:     Optional[str]  = Query(None),
    is_active:  Optional[bool] = Query(None),
    page:       int            = Query(1,  ge=1),
    page_size:  int            = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=super_admin
):
    q = db.query(User).join(User.role)

    if role_id    is not None: q = q.filter(User.role_id    == role_id)
    if scope_type is not None: q = q.filter(User.scope_type == scope_type)
    if scope_id   is not None: q = q.filter(User.scope_id   == scope_id)
    if is_active  is not None: q = q.filter(User.is_active  == is_active)
    if search:
        term = f"%{search}%"
        q = q.filter(or_(User.full_name.ilike(term), User.email.ilike(term)))

    total   = q.count()
    results = q.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size).all()

    return UserListOut(total=total, page=page, page_size=page_size, results=results)


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _=super_admin):
    return _get_or_404(db, User, user_id, "User")


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), _=super_admin):
    user = _get_or_404(db, User, user_id, "User")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/toggle-active", response_model=UserOut)
def toggle_active(user_id: int, db: Session = Depends(get_db), _=super_admin):
    user = _get_or_404(db, User, user_id, "User")
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/reset-password")
def reset_password(user_id: int, data: UserResetPassword, db: Session = Depends(get_db), _=super_admin):
    user = _get_or_404(db, User, user_id, "User")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": f"Password reset for {user.email}"}