"""HTTP entry point for the Supplier Service."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import Depends, FastAPI, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import (
    authorize_supplier_management,
    bearer,
    require_authenticated_user,
    require_supplier_create_admin,
    require_supplier_read_admin,
)
from app.config import Settings, get_settings
from app.errors import ApiError, api_error_handler, validation_error_handler
from app.repository import SupplierRepository, get_repository
from app.schemas import (
    CategoryResponse,
    SupplierCreate,
    SupplierListFilters,
    SupplierListResponse,
    SupplierPatch,
    SupplierRemovalResponse,
    SupplierResponse,
)


app = FastAPI(title="FoC Supplier Service")
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.get("/api/v1/categories", response_model=list[CategoryResponse])
def list_categories(
    _actor_id: Annotated[UUID, Depends(require_authenticated_user)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> list[CategoryResponse]:
    return repository.list_categories()


def supplier_list_filters(
    q: str | None = None,
    category: Annotated[list[str] | None, Query()] = None,
    building_area: str | None = None,
    sort: Literal["asc", "desc"] = "asc",
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SupplierListFilters:
    return SupplierListFilters(
        q=q,
        categories=category or [],
        building_area=building_area,
        sort=sort,
        page=page,
        page_size=page_size,
    )


@app.get("/api/v1/suppliers", response_model=SupplierListResponse)
def list_active_suppliers(
    request: Request,
    _actor_id: Annotated[UUID, Depends(require_authenticated_user)],
    filters: Annotated[SupplierListFilters, Depends(supplier_list_filters)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> SupplierListResponse:
    if "status" in request.query_params:
        raise ApiError(
            422, "VALIDATION_ERROR", "Supplier query is invalid",
            [{"field": "status", "message": "Status filtering requires administrator access"}],
        )
    return repository.list_active_suppliers(filters)


@app.get("/api/v1/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_active_supplier(
    supplier_id: UUID,
    _actor_id: Annotated[UUID, Depends(require_authenticated_user)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> SupplierResponse:
    return repository.get_active_supplier(supplier_id)


@app.get("/api/v1/admin/suppliers", response_model=SupplierListResponse)
def list_admin_suppliers(
    _actor_id: Annotated[UUID, Depends(require_supplier_read_admin)],
    filters: Annotated[SupplierListFilters, Depends(supplier_list_filters)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
    status_filter: Annotated[Literal["ACTIVE", "INACTIVE"] | None, Query(alias="status")] = None,
) -> SupplierListResponse:
    return repository.list_admin_suppliers(filters, status_filter)


@app.get("/api/v1/admin/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_admin_supplier(
    supplier_id: UUID,
    _actor_id: Annotated[UUID, Depends(require_supplier_read_admin)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> SupplierResponse:
    return repository.get_admin_supplier(supplier_id)


@app.post(
    "/api/v1/admin/suppliers",
    response_model=SupplierResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_supplier(
    supplier: SupplierCreate,
    _actor_id: Annotated[UUID, Depends(require_supplier_create_admin)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> SupplierResponse:
    return repository.create(supplier)


@app.patch("/api/v1/admin/suppliers/{supplier_id}", response_model=SupplierResponse)
def update_supplier(
    supplier_id: UUID,
    patch: SupplierPatch,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> SupplierResponse:
    action = "SUPPLIER_DEACTIVATE" if patch.status == "INACTIVE" else "SUPPLIER_UPDATE"
    authorize_supplier_management(credentials, settings, action)
    return repository.update(supplier_id, patch)


@app.delete("/api/v1/admin/suppliers/{supplier_id}", response_model=SupplierRemovalResponse)
def deactivate_supplier(
    supplier_id: UUID,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> SupplierRemovalResponse:
    authorize_supplier_management(credentials, settings, "SUPPLIER_DEACTIVATE")
    return repository.deactivate(supplier_id)
