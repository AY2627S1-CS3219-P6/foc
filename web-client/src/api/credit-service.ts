import { requestJson } from "./client";

export type Wallet = { userId: string; available: number; reserved: number; total: number; updatedAt: string };
export type CreditTransactionType = "ALLOCATION" | "RESERVATION" | "RELEASE" | "TRANSFER";
export type CreditTransaction = {
  transactionId: string;
  type: CreditTransactionType;
  amount: number;
  walletUserId: string;
  counterpartyUserId: string | null;
  orderId: string | null;
  createdAt: string;
};
export type CreditPage<T> = { items: T[]; page: number; pageSize: number; total: number };
export type CreditPageQuery = { page: number; pageSize: number };

export const creditService = {
  myWallet: (token: string) => requestJson<Wallet>("/wallets/me", { method: "GET" }, token),
  myTransactions: (query: CreditPageQuery, token: string) => {
    const params = new URLSearchParams({ page: String(query.page), pageSize: String(query.pageSize) });
    return requestJson<CreditPage<CreditTransaction>>(`/wallets/me/transactions?${params}`, { method: "GET" }, token);
  },
};
