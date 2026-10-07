export function SupplierNavigationIcon() {
  return <svg aria-hidden="true" fill="none" height="20" viewBox="0 0 24 24" width="20">
    <path d="m3 10 9-7 9 7H3ZM5 10v11h14V10M9 21v-7h6v7" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
  </svg>;
}

export function SupplierIcon({ size = 20 }: { size?: number }) {
  return <svg aria-hidden="true" fill="none" height={size} viewBox="0 0 24 24" width={size}>
    <path d="M4 9h16v11H4zM7 9V6a5 5 0 0 1 10 0v3" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8" />
  </svg>;
}

export function ProfileIcon() {
  return <svg aria-hidden="true" fill="none" height="20" viewBox="0 0 24 24" width="20">
    <circle cx="12" cy="8" r="4" stroke="currentColor" strokeWidth="1.8" />
    <path d="M4 21c.8-4.2 3.5-6.3 8-6.3s7.2 2.1 8 6.3" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
  </svg>;
}

export function UsersIcon() {
  return <svg aria-hidden="true" fill="none" height="20" viewBox="0 0 24 24" width="20">
    <circle cx="9" cy="8" r="3" stroke="currentColor" strokeWidth="1.8" />
    <path d="M3.5 20c.55-3.55 2.36-5.35 5.5-5.35 3.16 0 4.98 1.8 5.5 5.35" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
    <path d="M16.2 5.5a2.75 2.75 0 0 1 0 5.35M17.15 14.9c2.08.2 3.28 1.76 3.65 4.1" stroke="currentColor" strokeLinecap="round" strokeWidth="1.8" />
  </svg>;
}
