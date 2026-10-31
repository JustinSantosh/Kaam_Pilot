/** Typed client for the FastAPI backend (shapes mirror docs/openapi.json). */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type TurnStatus =
  | "awaiting_approval"
  | "needs_clarification"
  | "completed"
  | "rejected"
  | "busy";

export interface Customer {
  name: string;
  phone: string;
  state: string | null;
}

export interface ChatSendResponse {
  status: TurnStatus;
  reply: string;
  quote_id: string | null;
  conversation_id: string;
}

export interface Message {
  id: number;
  role: "customer" | "business";
  text: string;
  kind: string;
  quote_id: string | null;
  pdf_url: string | null;
  created_at: string;
}

export interface Scenario {
  id: string;
  label: string;
  message: string;
  follow_up: string | null;
}

export interface QuoteSummary {
  quote_id: string;
  number: string;
  conversation_id: string;
  customer_name: string;
  status: string;
  revision: number;
  total_paise: number;
  item_count: number;
  flags: string[];
  created_at: string;
  updated_at: string;
}

export interface LineItem {
  sku: string;
  name: string;
  hsn: string;
  unit: string;
  quantity: number;
  specs: Record<string, string>;
  unit_price_paise: number;
  setup_fee_paise: number;
  line_subtotal_paise: number;
  discount_paise: number;
  taxable_paise: number;
  gst_rate_bp: number;
  cgst_paise: number;
  sgst_paise: number;
  igst_paise: number;
  line_total_paise: number;
}

export interface Totals {
  subtotal_paise: number;
  discount_paise: number;
  taxable_paise: number;
  cgst_paise: number;
  sgst_paise: number;
  igst_paise: number;
  tax_paise: number;
  total_paise: number;
}

export interface ValidationItem {
  index: number;
  item_text: string;
  sku: string | null;
  name: string | null;
  quantity: number | null;
  specs: Record<string, string>;
  notes: string[];
  issues: { code: string; field: string | null; message: string; options: string[] }[];
}

export interface QuoteDetail extends QuoteSummary {
  customer_phone: string;
  customer_state: string | null;
  supply_type: "intra_state" | "inter_state" | null;
  raw_query: string;
  extraction: {
    items?: { item_text: string; quantity: number | null; specs: { name: string; value: string }[]; notes: string | null }[];
    delivery_by?: string | null;
    customer_state?: string | null;
  };
  validation: { complete?: boolean; items?: ValidationItem[] };
  items: LineItem[];
  totals: Totals;
  discount: { kind: "flat" | "percent"; value: number } | null;
  pdf_url: string | null;
  rejection_reason: string | null;
  customer_notes: string[];
  edit_errors: string[];
  revisions: number[];
  events: { kind: string; payload: Record<string, unknown>; created_at: string }[];
}

export interface CatalogOption {
  sku: string;
  name: string;
  category: string;
  unit: string;
  moq: number;
  required_specs: string[];
  spec_options: Record<string, string[]>;
}

export interface ItemEdit {
  sku: string;
  quantity: number;
  specs?: Record<string, string> | null;
}

export type Decision =
  | { action: "approve" }
  | { action: "reject"; reason: string }
  | {
      action: "edit";
      edits: {
        items?: ItemEdit[];
        discount?: { kind: "flat" | "percent"; value: number } | null;
        remove_discount?: boolean;
      };
    };

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    cache: "no-store",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const err = body?.error;
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? res.statusText);
  }
  return res.json() as Promise<T>;
}

export const fileUrl = (path: string | null) => (path ? `${API_URL}${path}` : null);

export const api = {
  scenarios: () => request<Scenario[]>("/api/demo/scenarios"),
  send: (conversationId: string, customer: Customer, message: string) =>
    request<ChatSendResponse>("/api/chat/send", {
      method: "POST",
      body: JSON.stringify({ conversation_id: conversationId, customer, message }),
    }),
  sendAudio: async (conversationId: string, customer: Customer, audio: Blob) => {
    const form = new FormData();
    form.append("conversation_id", conversationId);
    form.append("name", customer.name);
    form.append("phone", customer.phone);
    if (customer.state) form.append("state", customer.state);
    form.append("audio", audio, "voice-note.webm");
    const res = await fetch(`${API_URL}/api/chat/send-audio`, { method: "POST", body: form });
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new ApiError(res.status, body?.error?.code ?? "http_error", body?.error?.message ?? res.statusText);
    }
    return (await res.json()) as ChatSendResponse;
  },
  messages: (conversationId: string, since = 0) =>
    request<Message[]>(`/api/conversations/${conversationId}/messages?since=${since}`),
  inbox: (status: "awaiting_approval" | "open" | "closed" | "all") =>
    request<QuoteSummary[]>(`/api/business/inbox?status=${status}`),
  catalog: () => request<CatalogOption[]>("/api/business/catalog"),
  quote: (quoteId: string) => request<QuoteDetail>(`/api/quotes/${quoteId}`),
  decide: (quoteId: string, decision: Decision, revision?: number) =>
    request<QuoteDetail>(
      `/api/quotes/${quoteId}/decision${revision ? `?revision=${revision}` : ""}`,
      { method: "POST", body: JSON.stringify(decision) },
    ),
};
