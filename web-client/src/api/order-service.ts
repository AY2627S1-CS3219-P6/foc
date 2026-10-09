import { requestJson } from "./client";

export type OrderState = "OPEN" | "ACCEPTED" | "PICKED_UP" | "DELIVERED" | "COMPLETED" | "CANCELLED" | "EXPIRED" | "FAILED";
export type OrderRelationship = "requester" | "courier";

export type OrderInput = {
  supplierId: string;
  itemDescription: string;
  deliveryLocation: string;
  reward: number;
  acceptanceDeadline: string;
  deliveryDeadline: string;
};

export type OrderAssessment = OrderInput & {
  orderId: string;
  pickup: {
    name: string;
    buildingArea: string;
    pickupLocationDescription: string;
    floor: string | null;
    latitude: number | null;
    longitude: number | null;
    updatedAt: string;
  };
  state: OrderState;
  createdAt: string;
};

export type OrderParticipant = OrderAssessment & {
  requesterId: string;
  courierId: string | null;
  updatedAt: string;
};

export type OrderDetail = OrderAssessment | OrderParticipant;

export type OrderCreation = {
  operationId: string;
  stage: "VALIDATED" | "RESERVATION_UNKNOWN" | "READY_TO_FINALIZE" | "SUCCEEDED" | "ABORTING" | "ABORTED";
  statusUrl: string;
  retryCreation: boolean;
  errorCode: string | null;
  orderId: string | null;
};

export type OrderHistoryEntry = {
  sequence: number;
  previousState: OrderState | null;
  newState: OrderState;
  actorId: string;
  actorType: "USER" | "SYSTEM";
  occurredAt: string;
};

export type OrderPage<T> = { items: T[]; page: number; pageSize: number; total: number };
export type OrderPageQuery = { page?: number; pageSize?: number };

function pageParams(query: OrderPageQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.page !== undefined) params.set("page", String(query.page));
  if (query.pageSize !== undefined) params.set("pageSize", String(query.pageSize));
  return params;
}

export const orderService = {
  // The caller owns this key: reuse both key and unchanged body after an
  // ambiguous result or auth refresh. A 202 is not a successful Order.
  create: (input: OrderInput, idempotencyKey: string, token: string) => {
    const { supplierId, itemDescription, deliveryLocation, reward, acceptanceDeadline, deliveryDeadline } = input;
    return requestJson<OrderParticipant | OrderCreation>("/orders", {
      method: "POST",
      headers: { "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ supplierId, itemDescription, deliveryLocation, reward, acceptanceDeadline, deliveryDeadline }),
    }, token);
  },
  // Construct a fixed-origin path; never follow an upstream-supplied statusUrl
  // with the user's bearer token.
  creation: (operationId: string, token: string) =>
    requestJson<OrderCreation>(`/order-creations/${encodeURIComponent(operationId)}`, { method: "GET" }, token),
  list: (query: OrderPageQuery & { supplierId?: string }, token: string) => {
    const params = pageParams(query);
    if (query.supplierId) params.set("supplierId", query.supplierId);
    return requestJson<OrderPage<OrderAssessment>>(`/orders${params.size ? `?${params}` : ""}`, { method: "GET" }, token);
  },
  mine: (relationship: OrderRelationship, query: OrderPageQuery, token: string) => {
    const params = pageParams(query);
    params.set("relationship", relationship);
    return requestJson<OrderPage<OrderParticipant>>(`/orders/mine?${params}`, { method: "GET" }, token);
  },
  detail: (orderId: string, token: string) =>
    requestJson<OrderDetail>(`/orders/${encodeURIComponent(orderId)}`, { method: "GET" }, token),
  history: (orderId: string, query: OrderPageQuery, token: string) => {
    const params = pageParams(query);
    return requestJson<OrderPage<OrderHistoryEntry>>(`/orders/${encodeURIComponent(orderId)}/history${params.size ? `?${params}` : ""}`, { method: "GET" }, token);
  },
};
