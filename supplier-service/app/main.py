"""HTTP entry point for the Supplier Service."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, status
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import authorize_supplier_management, bearer, require_authenticated_user, require_supplier_create_admin
from app.config import Settings, get_settings
from app.errors import ApiError, api_error_handler, validation_error_handler
from app.repository import SupplierRepository, get_repository
from app.schemas import CategoryResponse, SupplierCreate, SupplierPatch, SupplierRemovalResponse, SupplierResponse


app = FastAPI(title="FoC Supplier Service")
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.get("/api/v1/categories", response_model=list[CategoryResponse])
def list_categories(
    _actor_id: Annotated[UUID, Depends(require_authenticated_user)],
    repository: Annotated[SupplierRepository, Depends(get_repository)],
) -> list[CategoryResponse]:
    return repository.list_categories()


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
