"""Supplier-owned PostgreSQL writes. Supabase migrations own the schema."""

import psycopg
from fastapi import Depends
from psycopg.rows import dict_row

from app.config import Settings, get_settings
from app.errors import ApiError
from app.schemas import SupplierCreate, SupplierResponse


class SupplierRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def create(self, supplier: SupplierCreate) -> SupplierResponse:
        if not self.database_url:
            raise ApiError(503, "DATABASE_UNAVAILABLE", "Supplier database is unavailable")
        try:
            # The connection context commits only after all inserts and the
            # deferred category trigger succeed; errors roll everything back.
            with psycopg.connect(self.database_url, connect_timeout=5, row_factory=dict_row) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT code FROM supplier_service.categories WHERE code = ANY(%s)",
                        (supplier.categories,),
                    )
                    supported = {row["code"] for row in cursor.fetchall()}
                    unknown = sorted(set(supplier.categories) - supported)
                    if unknown:
                        raise ApiError(
                            422,
                            "VALIDATION_ERROR",
                            "Supplier data is invalid",
                            [{"field": "categories", "message": f"Unsupported category: {code}"} for code in unknown],
                        )

                    cursor.execute(
                        """
                        INSERT INTO supplier_service.suppliers (
                            name, building_area, pickup_location_description,
                            floor, latitude, longitude, opening_time, closing_time,
                            image_url, status
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s::time, %s::time,
                            %s, %s::supplier_service.supplier_status
                        ) RETURNING id
                        """,
                        (
                            supplier.name,
                            supplier.building_area,
                            supplier.pickup_location_description,
                            supplier.floor,
                            supplier.latitude,
                            supplier.longitude,
                            supplier.opening_time,
                            supplier.closing_time,
                            str(supplier.image_url) if supplier.image_url is not None else None,
                            supplier.status,
                        ),
                    )
                    supplier_id = cursor.fetchone()["id"]
                    cursor.executemany(
                        """
                        INSERT INTO supplier_service.supplier_categories (supplier_id, category_code)
                        VALUES (%s, %s)
                        """,
                        [(supplier_id, code) for code in supplier.categories],
                    )
                    cursor.execute(
                        "SELECT * FROM supplier_service.suppliers WHERE id = %s",
                        (supplier_id,),
                    )
                    row = cursor.fetchone()

            # Reaching here means the transaction, including deferred checks,
            # committed successfully.
            result = dict(row)
            result["categories"] = supplier.categories
            result["opening_time"] = row["opening_time"].strftime("%H:%M") if row["opening_time"] else None
            result["closing_time"] = row["closing_time"].strftime("%H:%M") if row["closing_time"] else None
            return SupplierResponse.model_validate(result)
        except psycopg.errors.UniqueViolation as error:
            raise ApiError(409, "DUPLICATE_SUPPLIER", "A supplier with this name, area, and floor already exists") from error
        except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation) as error:
            raise ApiError(422, "VALIDATION_ERROR", "Supplier data is invalid") from error
        except psycopg.Error as error:
            raise ApiError(503, "DATABASE_UNAVAILABLE", "Supplier database is unavailable") from error


def get_repository(settings: Settings = Depends(get_settings)) -> SupplierRepository:
    return SupplierRepository(settings.database_url)
