-- N2NFR2.1: Admin Dashboard listings read every errand newest first, optionally filtered by
-- state or supplier. The existing created-time index covers OPEN errands only.
CREATE INDEX orders_admin_created ON order_service.orders (created_at DESC, id DESC);
CREATE INDEX orders_admin_state ON order_service.orders (state, created_at DESC, id DESC);
CREATE INDEX orders_admin_supplier ON order_service.orders (supplier_id, created_at DESC, id DESC);
