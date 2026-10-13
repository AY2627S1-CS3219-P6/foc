import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { isApiRequestError } from "../api/client";
import { creditService, type CreditPage, type CreditTransaction, type Wallet } from "../api/credit-service";
import { useAuth } from "../app/use-auth";
import { WorkspaceShell } from "../components/workspace-shell";

const PAGE_SIZE = 10;
const labels: Record<CreditTransaction["type"], string> = {
  ALLOCATION: "Welcome credits",
  RESERVATION: "Reserved for errand",
  RELEASE: "Returned from errand",
  TRANSFER: "Errand reward",
};

function signedAmount(item: CreditTransaction, me: string): string {
  if (item.type === "TRANSFER") return item.counterpartyUserId === me ? `+${item.amount}` : `−${item.amount}`;
  if (item.type === "RESERVATION") return `−${item.amount}`;
  return `+${item.amount}`;
}

export function WalletPage() {
  const { user, withCurrentAccess } = useAuth();
  const [page, setPage] = useState(1);
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [history, setHistory] = useState<CreditPage<CreditTransaction> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    // The wallet read get-or-creates it, so request it before reading its history.
    withCurrentAccess(async (token) => {
      const nextWallet = await creditService.myWallet(token);
      const nextHistory = await creditService.myTransactions({ page, pageSize: PAGE_SIZE }, token);
      return [nextWallet, nextHistory] as const;
    })
      .then(([nextWallet, nextHistory]) => {
        if (!active) return;
        setWallet(nextWallet);
        setHistory(nextHistory);
      })
      .catch((failure) => {
        if (!active) return;
        setError(isApiRequestError(failure) && failure.code === "WALLET_NOT_READY"
          ? "Your wallet is being set up. Refresh in a moment."
          : "Credits are unavailable right now. Try again shortly.");
      });
    return () => { active = false; };
  }, [page, withCurrentAccess]);

  const lastPage = history ? Math.max(1, Math.ceil(history.total / history.pageSize)) : 1;
  return <WorkspaceShell className="order-shell" userDescription="Your credits for requesting and delivering errands.">
    {error ? <section className="order-panel" role="alert"><p>{error}</p></section> : null}
    {wallet ? <section className="order-panel" aria-label="Credit balance">
      <h1>Credits</h1>
      <dl>
        <div><dt>Available</dt><dd>{wallet.available}</dd></div>
        <div><dt>Reserved</dt><dd>{wallet.reserved}</dd></div>
        <div><dt>Total</dt><dd>{wallet.total}</dd></div>
      </dl>
    </section> : null}
    {history && user ? <section className="order-panel" aria-label="Credit history">
      <h2>History</h2>
      {history.items.length === 0 ? <p>No credit activity yet.</p> : <ul>
        {history.items.map((item) => <li key={item.transactionId}>
          <span>{labels[item.type]}</span>{" "}
          <strong>{signedAmount(item, user.userId)}</strong>{" "}
          {item.orderId ? <Link to={`/orders/${item.orderId}`}>View errand</Link> : null}{" "}
          <time dateTime={item.createdAt}>{new Date(item.createdAt).toLocaleString()}</time>
        </li>)}
      </ul>}
      <nav aria-label="History pages">
        <button type="button" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
        <span>Page {page} of {lastPage}</span>
        <button type="button" disabled={page >= lastPage} onClick={() => setPage(page + 1)}>Next</button>
      </nav>
    </section> : null}
  </WorkspaceShell>;
}
