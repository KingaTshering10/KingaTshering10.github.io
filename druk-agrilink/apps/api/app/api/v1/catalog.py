"""Reference data: locations, products, varieties, grades.

Reads are available to any authenticated user (and are cached offline by the
PWA); writes are admin-only and audited.
"""

import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession, require_roles
from app.core.errors import NotFoundError
from app.domain.enums import LocationType, Role
from app.models import Location, Product, ProductVariety, QualityGrade
from app.schemas.catalog import (
    GradeCreate,
    GradeOut,
    LocationCreate,
    LocationOut,
    ProductCreate,
    ProductOut,
    VarietyCreate,
    VarietyOut,
)
from app.schemas.common import Page, PageParams
from app.services.audit import record_audit

router = APIRouter(tags=["catalog"])

AdminUser = Depends(require_roles(Role.ADMIN))


# ---------- locations ----------


@router.get("/locations", response_model=Page[LocationOut])
def list_locations(
    db: DbSession,
    user: CurrentUser,
    params: PageParams = Depends(),
    dzongkhag: str | None = Query(None),
    location_type: LocationType | None = Query(None),
):
    query = select(Location).where(Location.is_active.is_(True))
    if dzongkhag:
        query = query.where(Location.dzongkhag == dzongkhag)
    if location_type:
        query = query.where(Location.location_type == location_type)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(Location.dzongkhag, Location.name).offset(params.offset).limit(params.page_size)
    ).all()
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/locations", response_model=LocationOut, status_code=201, dependencies=[AdminUser])
def create_location(payload: LocationCreate, db: DbSession, user: CurrentUser, request: Request):
    location = Location(**payload.model_dump())
    db.add(location)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="location.create",
        entity_type="Location",
        entity_id=location.id,
        after={"name": location.name, "dzongkhag": location.dzongkhag},
        request=request,
    )
    db.commit()
    return location


# ---------- products ----------


@router.get("/products", response_model=Page[ProductOut])
def list_products(
    db: DbSession,
    user: CurrentUser,
    params: PageParams = Depends(),
    category: str | None = Query(None),
):
    query = select(Product).where(Product.is_active.is_(True))
    if category:
        query = query.where(Product.category == category)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Product.name).offset(params.offset).limit(params.page_size)).all()
    return Page(items=items, total=total, page=params.page, page_size=params.page_size)


@router.post("/products", response_model=ProductOut, status_code=201, dependencies=[AdminUser])
def create_product(payload: ProductCreate, db: DbSession, user: CurrentUser, request: Request):
    product = Product(**payload.model_dump())
    db.add(product)
    db.flush()
    record_audit(
        db,
        actor_user_id=user.id,
        action="product.create",
        entity_type="Product",
        entity_id=product.id,
        after={"name": product.name},
        request=request,
    )
    db.commit()
    return product


@router.get("/products/{product_id}/varieties", response_model=list[VarietyOut])
def list_varieties(product_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return db.scalars(
        select(ProductVariety).where(ProductVariety.product_id == product_id).order_by(ProductVariety.name)
    ).all()


@router.post(
    "/products/{product_id}/varieties",
    response_model=VarietyOut,
    status_code=201,
    dependencies=[AdminUser],
)
def create_variety(product_id: uuid.UUID, payload: VarietyCreate, db: DbSession, user: CurrentUser):
    if db.get(Product, product_id) is None:
        raise NotFoundError("Product not found.")
    variety = ProductVariety(product_id=product_id, **payload.model_dump())
    db.add(variety)
    db.commit()
    return variety


@router.get("/products/{product_id}/grades", response_model=list[GradeOut])
def list_grades(product_id: uuid.UUID, db: DbSession, user: CurrentUser):
    return db.scalars(
        select(QualityGrade).where(QualityGrade.product_id == product_id).order_by(QualityGrade.sort_order)
    ).all()


@router.post(
    "/products/{product_id}/grades",
    response_model=GradeOut,
    status_code=201,
    dependencies=[AdminUser],
)
def create_grade(product_id: uuid.UUID, payload: GradeCreate, db: DbSession, user: CurrentUser):
    if db.get(Product, product_id) is None:
        raise NotFoundError("Product not found.")
    grade = QualityGrade(product_id=product_id, **payload.model_dump())
    db.add(grade)
    db.commit()
    return grade
