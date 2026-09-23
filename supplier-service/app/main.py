"""HTTP entry point for the Supplier Service."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, status
from fastapi.exceptions import RequestValidationError

from app.auth import require_supplier_create_admin
from app.errors import ApiError, api_error_handler, validation_error_handler
from app.repository import SupplierRepository, get_repository
from app.schemas import SupplierCreate, SupplierResponse


app = FastAPI(title="FoC Supplier Service")
app.add_exception_handler(ApiError, api_error_handler)
app.add_exception_handler(RequestValidationError, validation_error_handler)


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
