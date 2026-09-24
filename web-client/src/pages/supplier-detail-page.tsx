import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { isApiRequestError } from "../api/client";
import { type Supplier, supplierService } from "../api/supplier-service";
import { useAuth } from "../app/auth-provider";
import { SupplierShell } from "../components/supplier-shell";
import { SupplierStatusActions } from "../components/supplier-status-actions";

function localDate(value: string): string {
  return new Intl.DateTimeFormat("en-SG", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Singapore" }).format(new Date(value));
}

export function SupplierDetailPage({ admin = false }: { admin?: boolean }) {
  const { supplierId } = useParams();
  const location = useLocation();
  const { withCurrentAccess } = useAuth();
  const [supplier, setSupplier] = useState<Supplier | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ status: number; message: string } | null>(null);
  const [reload, setReload] = useState(0);
  const [notice, setNotice] = useState<string | null>((location.state as { notice?: string } | null)?.notice ?? null);

  useEffect(() => {
    if (!supplierId) return;
    let active = true;
    setLoading(true);
    setError(null);
    withCurrentAccess((token) => supplierService.detail(supplierId, token, admin))
      .then((data) => { if (active) setSupplier(data); })
      .catch((failure) => { if (active) { setSupplier(null); setError({ status: isApiRequestError(failure) ? failure.status : 0, message: isApiRequestError(failure) ? failure.message : "Try again." }); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [admin, supplierId, reload, withCurrentAccess]);

  const listPath = admin ? "/admin/suppliers" : "/suppliers";
  return <SupplierShell>
    <Link className="supplier-back-link" to={listPath}>← All suppliers</Link>
    {notice ? <p className="supplier-notice" role="status">{notice}</p> : null}
    {loading ? <p className="supplier-state" role="status">Loading supplier…</p> : null}
    {error ? <section className="supplier-state supplier-state-error" role="alert"><h1>{error.status === 404 ? "Supplier not found" : "Supplier could not load"}</h1><p>{error.status === 404 ? "This supplier may have been removed or is no longer available." : error.message}</p>{error.status !== 404 ? <button className="supplier-apply-button" onClick={() => setReload((value) => value + 1)} type="button">Try again</button> : null}</section> : null}
    {!loading && supplier ? <>
      <div className="supplier-page-heading supplier-detail-heading"><div><h1>{supplier.name}</h1><p>{supplier.building_area}{supplier.floor ? ` · Floor ${supplier.floor}` : ""} · {supplier.categories.join(" / ")}</p></div><span className={`supplier-status ${supplier.status.toLowerCase()}`}>{supplier.status === "ACTIVE" ? "Active" : "Inactive"}</span></div>
      {admin ? <div className="supplier-detail-actions"><Link className="supplier-primary-action" to={`/admin/suppliers/${supplier.id}/edit`}>Edit supplier</Link><SupplierStatusActions id={supplier.id} name={supplier.name} onChanged={(message) => { setNotice(message); setReload((value) => value + 1); }} status={supplier.status} /></div> : null}
      {supplier.image_url ? <div className="supplier-detail-image"><img alt={`${supplier.name} location`} src={supplier.image_url} /></div> : null}
      <div className="supplier-detail-grid">
        <section className="supplier-detail-panel"><h2>Supplier information</h2><dl>
          <div><dt>Categories</dt><dd>{supplier.categories.join(" / ")}</dd></div>
          <div><dt>Building or campus area</dt><dd>{supplier.building_area}</dd></div>
          <div><dt>Pickup location</dt><dd>{supplier.pickup_location_description}</dd></div>
          <div><dt>Floor</dt><dd>{supplier.floor || "Not provided"}</dd></div>
          <div><dt>Opening and closing times</dt><dd>{supplier.opening_time && supplier.closing_time ? `${supplier.opening_time}–${supplier.closing_time}` : "Not provided"}</dd></div>
          <div><dt>Coordinates</dt><dd>{supplier.latitude !== null && supplier.longitude !== null ? `${supplier.latitude}, ${supplier.longitude}` : "Not provided"}</dd></div>
        </dl></section>
        <aside className="supplier-detail-side"><section className="supplier-detail-panel"><h2>Availability</h2><p>{supplier.status === "ACTIVE" ? "Available for new errands." : "This supplier is inactive and is hidden from normal supplier listings."}</p><p className="supplier-detail-pickup">Pickup: {supplier.pickup_location_description}</p></section><section className="supplier-detail-panel"><h2>Record details</h2><dl><div><dt>Supplier ID</dt><dd className="supplier-id">{supplier.id}</dd></div><div><dt>Created</dt><dd>{localDate(supplier.created_at)}</dd></div><div><dt>Last updated</dt><dd>{localDate(supplier.updated_at)}</dd></div></dl></section></aside>
      </div>
    </> : null}
  </SupplierShell>;
}
