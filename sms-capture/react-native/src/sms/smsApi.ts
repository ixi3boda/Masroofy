// Calls to the Spring Boot SMS endpoints. Plug in your existing base URL and token getter.

export type TxType =
  | 'DEBIT' | 'CREDIT' | 'TRANSFER_OUT' | 'TRANSFER_IN' | 'ATM_WITHDRAWAL' | 'BILL_PAYMENT' | 'OTHER';

export type ReviewReason =
  | 'NO_ACCOUNT' | 'UNKNOWN_SENDER' | 'UNKNOWN_TYPE' | 'LOW_CONFIDENCE' | 'FOREIGN_CURRENCY' | 'POSSIBLE_DUPLICATE';

export interface SmsTransaction {
  id: number;
  status: 'DRAFT' | 'CONFIRMED' | 'REJECTED';
  type: TxType;
  amount: number;
  fee: number;
  currency: string;
  occurredAt: string;            // ISO instant
  merchant: string | null;
  channel: string | null;        // card, instapay, wallet, bank_transfer, atm, other, unknown
  institution: string | null;    // bank or app that sent the SMS
  accountId: number | null;
  accountLast4: string | null;
  internalTransfer: boolean;
  duplicateOfId: number | null;
  reportedBalance: number | null;
  balanceDifference: number | null;
  confidence: number | null;
  reviewReasons: ReviewReason[];
}

export interface IngestResult {
  status: 'APPLIED' | 'DRAFT' | 'IGNORED' | 'ALREADY_RECEIVED';
  transactionId: number | null;
  institution: string | null;
  type: TxType | null;
  amount: number | null;
  currency: string | null;
  occurredAt: string | null;
  accountId: number | null;
  reviewReasons: ReviewReason[];
}

export interface SmsSender {
  senderId: string;
  institution: string;
  kind: 'CASH' | 'CARD' | 'BANK' | 'WALLET';
  enabled: boolean;
  custom: boolean;
}

export interface ConfirmEdits {
  accountId?: number;
  type?: TxType;
  amount?: number;
  fee?: number;
  merchant?: string;
  occurredAt?: string;
  category?: string;
}

export interface SmsApi {
  getSenders(): Promise<SmsSender[]>;
  saveSender(s: { senderId: string; institution: string; kind: SmsSender['kind']; enabled?: boolean }): Promise<SmsSender>;
  getDrafts(): Promise<SmsTransaction[]>;
  confirm(id: number, edits?: ConfirmEdits): Promise<SmsTransaction>;
  reject(id: number): Promise<SmsTransaction>;
  /** Upload SMS text directly (paste/share flow, emulator demos). */
  ingest(messages: { sender: string; body: string; receivedAt?: number }[]): Promise<IngestResult[]>;
}

export class SmsApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
  }
}

export function createSmsApi(baseUrl: string, getToken: () => Promise<string | null>): SmsApi {
  const root = baseUrl.replace(/\/+$/, '') + '/api/sms';

  async function call<T>(path: string, method: 'GET' | 'POST' | 'PUT', body?: unknown): Promise<T> {
    const token = await getToken();
    const res = await fetch(root + path, {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!res.ok) {
      let msg = `HTTP ${res.status}`;
      try {
        const j = (await res.json()) as { message?: string; error?: string };
        msg = j.message || j.error || msg;
      } catch {
        /* body was not JSON */
      }
      throw new SmsApiError(res.status, msg);
    }
    return (await res.json()) as T;
  }

  return {
    getSenders: () => call<SmsSender[]>('/senders', 'GET'),
    saveSender: (s) => call<SmsSender>('/senders', 'PUT', s),
    getDrafts: () => call<SmsTransaction[]>('/review', 'GET'),
    confirm: (id, edits) => call<SmsTransaction>(`/transactions/${id}/confirm`, 'POST', edits ?? {}),
    reject: (id) => call<SmsTransaction>(`/transactions/${id}/reject`, 'POST'),
    ingest: async (messages) =>
      (await call<{ results: IngestResult[] }>('/ingest', 'POST', { messages })).results,
  };
}
