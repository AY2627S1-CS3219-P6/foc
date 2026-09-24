import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { isApiRequestError } from "../api/client";
import { type Category, type SupplierList, type SupplierListItem, type SupplierQuery, supplierService } from "../api/supplier-service";
import { useAuth } from "../app/auth-provider";
import { SupplierIcon, SupplierShell } from "../components/supplier-shell";

function readQuery(params: URLSearchParams, admin: boolean): SupplierQuery {
  const page = Number(params.get("page"));
  const pageSize = Number(params.get("page_size"));
  const status = params.get("status");
  return {
    q: params.get("q") ?? "",
    categories: params.getAll("category"),
    buildingArea: params.get("building_area") ?? "",
    sort: params.get("sort") === "desc" ? "desc" : "asc",
    status: admin && (status === "ACTIVE" || status === "INACTIVE") ? status : undefined,
    page: Number.isInteger(page) && page > 0 ? page : 1,
    pageSize: Number.isInteger(pageSize) && pageSize > 0 ? pageSize : 6,
  };
}

function hours(item: SupplierListItem): string {
  return item.opening_time && item.closing_time ? `${item.opening_time}–${item.closing_time}` : "Hours not provided";
}

export function SupplierListPage({ admin = false }: { admin?: boolean }) {
  const { withCurrentAccess } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryKey = searchParams.toString();
  const query = useMemo(() => readQuery(new URLSearchParams(queryKey), admin), [queryKey, admin]);
  const [search, setSearch] = useState(query.q ?? "");
  const [area, setArea] = useState(query.buildingArea ?? "");
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoryError, setCategoryError] = useState(false);
  const [result, setResult] = useState<SupplierList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    setSearch(query.q ?? "");
    setArea(query.buildingArea ?? "");
  }, [query.q, query.buildingArea]);

  useEffect(() => {
    let active = true;
    withCurrentAccess((token) => supplierService.categories(token))
      .then((items) => { if (active) { setCategories(items); setCategoryError(false); } })
      .catch(() => { if (active) setCategoryError(true); });
    return () => { active = false; };
  }, [withCurrentAccess, reload]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError(null);
    withCurrentAccess((token) => supplierService.list(query, token, admin))
      .then((data) => { if (active) setResult(data); })
      .catch((failure) => { if (active) { setResult(null); setError(isApiRequestError(failure) ? failure.message : "We could not load suppliers. Try again."); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [admin, query, reload, withCurrentAccess]);

  function updateQuery(changes: Record<string, string | null>, categoryCodes?: string[]) {
    // Read the current URL at action time so consecutive filter changes do not
    // overwrite one another before React has rendered the previous navigation.
    const next = new URLSearchParams(window.location.search);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value); else next.delete(key);
    }
    if (categoryCodes) {
      next.delete("category");
      for (const code of categoryCodes) next.append("category", code);
    }
    if (!("page" in changes)) next.delete("page");
    setSearchParams(next);
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    updateQuery({ q: search.trim(), building_area: area.trim() });
  }

  function toggleCategory(code: string) {
    const selected = new Set(query.categories);
    if (selected.has(code)) selected.delete(code); else selected.add(code);
    updateQuery({}, [...selected]);
  }

  const selectedCategories = query.categories ?? [];
  const maxPage = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1;
  const from = result && result.total > 0 ? (result.page - 1) * result.page_size + 1 : 0;
  const to = result ? Math.min(result.total, result.page * result.page_size) : 0;
  const names = new Map(categories.map((category) => [category.code, category.display_name]));

  return <SupplierShell>
    <div className="supplier-page-heading">
      <div><h1>{admin ? "Manage suppliers" : "Campus suppliers"}</h1><p>{admin ? "Maintain supplier details and availability." : "Browse nearby campus spots and find what you need."}</p></div>
      {admin ? <Link className="supplier-primary-action" to="/admin/suppliers/new">+ Add supplier</Link> : null}
    </div>

    <section aria-label="Search and filter suppliers" className="supplier-filter-panel">
      <form className="supplier-search-form" onSubmit={submitSearch}>
        <label className="supplier-search-field"><span className="sr-only">Search suppliers</span><span aria-hidden="true">⌕</span><input onChange={(event) => setSearch(event.target.value)} placeholder="Search suppliers, areas or pickup locations" type="search" value={search} /></label>
        <label className="supplier-area-field"><span className="sr-only">Campus area</span><input onChange={(event) => setArea(event.target.value)} placeholder="Campus area: All" value={area} /></label>
        <button className="supplier-apply-button" type="submit">Search</button>
      </form>
      <div className="supplier-filter-row">
        <details className="supplier-category-picker"><summary>Categories: {selectedCategories.length ? selectedCategories.map((code) => names.get(code) ?? code).join(", ") : "All"}</summary>
          <div className="supplier-category-options">
            {categoryError ? <p>Categories could not load. <button className="supplier-inline-button" onClick={() => setReload((value) => value + 1)} type="button">Try again</button></p> : null}
            {categories.map((category) => <label key={category.code}><input checked={selectedCategories.includes(category.code)} onChange={() => toggleCategory(category.code)} type="checkbox" />{category.display_name}</label>)}
          </div>
        </details>
        <label className="supplier-select-label"><span className="sr-only">Sort suppliers</span><select onChange={(event) => updateQuery({ sort: event.target.value === "desc" ? "desc" : null })} value={query.sort}><option value="asc">Sort: Name A–Z</option><option value="desc">Sort: Name Z–A</option></select></label>
        {admin ? <label className="supplier-select-label"><span className="sr-only">Supplier status</span><select onChange={(event) => updateQuery({ status: event.target.value || null })} value={query.status ?? ""}><option value="">Status: All</option><option value="ACTIVE">Active</option><option value="INACTIVE">Inactive</option></select></label> : <span className="supplier-active-note">Active suppliers only</span>}
      </div>
    </section>

    {loading ? <p className="supplier-state" role="status">Loading suppliers…</p> : null}
    {error ? <section className="supplier-state supplier-state-error" role="alert"><h2>Suppliers could not load</h2><p>{error}</p><button className="supplier-apply-button" onClick={() => setReload((value) => value + 1)} type="button">Try again</button></section> : null}
    {!loading && !error && result?.total === 0 ? <section className="supplier-state"><h2>No suppliers found</h2><p>Try another search or clear the filters.</p><button className="supplier-apply-button" onClick={() => { setSearch(""); setArea(""); setSearchParams(new URLSearchParams()); }} type="button">Clear filters</button></section> : null}
    {!loading && !error && result && result.total > 0 ? <>
      <div aria-live="polite" className="supplier-results-count">{result.total} supplier{result.total === 1 ? "" : "s"}</div>
      <div className={admin ? "supplier-admin-results" : "supplier-card-grid"}>
        {admin ? <div aria-hidden="true" className="supplier-table-head"><span>Supplier</span><span>Category</span><span>Campus area</span><span>Status</span><span>Actions</span></div> : null}
        {result.items.map((item) => <article className={admin ? "supplier-admin-row" : "supplier-card"} key={item.id}>
          {!admin ? <div aria-hidden="true" className="supplier-card-icon"><SupplierIcon size={22} /></div> : null}
          <div className="supplier-card-main"><h2>{item.name}</h2><p>{item.building_area}{item.floor ? ` · Floor ${item.floor}` : ""}</p><p>{item.categories.map((code) => names.get(code) ?? code).join(" / ")}</p>{!admin ? <p className="supplier-card-hours">{hours(item)}</p> : null}</div>
          {admin ? <><div className="supplier-admin-area">{item.building_area}</div><span className={`supplier-status ${item.status.toLowerCase()}`}>{item.status === "ACTIVE" ? "Active" : "Inactive"}</span><div className="supplier-admin-actions"><Link to={`/admin/suppliers/${item.id}`}>View</Link><Link to={`/admin/suppliers/${item.id}/edit`}>Edit</Link></div></> : <><span className="supplier-status active">Active</span><Link aria-label={`View ${item.name}`} className="supplier-card-link" to={`/suppliers/${item.id}`}>View supplier <span aria-hidden="true">→</span></Link></>}
        </article>)}
      </div>
      <div className="supplier-pagination"><span>Showing {from}–{to} of {result.total}</span><label>Per page <select aria-label="Suppliers per page" onChange={(event) => updateQuery({ page_size: event.target.value === "6" ? null : event.target.value })} value={String(query.pageSize)}>{[6, 12, 20, 50].map((size) => <option key={size} value={size}>{size}</option>)}</select></label><div className="supplier-page-buttons"><button disabled={result.page <= 1} onClick={() => updateQuery({ page: String(result.page - 1) })} type="button">Previous</button><span>Page {result.page} of {maxPage}</span><button disabled={result.page >= maxPage} onClick={() => updateQuery({ page: String(result.page + 1) })} type="button">Next</button></div></div>
    </> : null}
  </SupplierShell>;
}
