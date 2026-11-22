import { mockBankMessages, mockSharedMessageText, mockTrackingAccounts } from '@/mocks/data/smsMessages';
import { mockTransactionService } from '@/mocks/services/mockTransactionService';
import { SmsService } from '@/services/types';
import { strings } from '@/strings';
import { BankMessage, BankMessageMatch, BankMessageReview } from '@/types/sms';
import { AppError } from '@/utils/errors';

/**
 * In-memory stand-in for bank SMS import and review. It parses pasted text,
 * finds an existing mock transaction with the same amount, merchant, card and
 * day (checked again on every read until the message is reviewed), and keeps
 * each message's status until the app reloads. Screens use `@/services/smsService`, never this file.
 */

const RESPONSE_DELAY_MS = 600;
const EXTRACTION_DELAY_MS = 1500;
const KNOWN_BANKS = ['CIB', 'NBE', 'Banque Misr', 'QNB', 'HSBC'];
const UNKNOWN_BANK = 'Bank message';

const AMOUNT = /EGP\s*([\d,]+(?:\.\d{1,2})?)/i;
const DATE_TIME = /(\d{2})\/(\d{2})\/(\d{4})\s+(\d{2}):(\d{2})/;
const CARD = /card ending\s*(\d{4})/i;
const MERCHANT = /\bat\s+(.+?)\s+on\s+\d{2}\//i;
const WITHDRAWAL = /withdrawal|transfer/i;

type ParsedMessage = Omit<BankMessage, 'match'>;

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const findMatch = ({ kind, merchant, amount, cardLast4, receivedAt }: ParsedMessage): BankMessageMatch | undefined => {
  if (kind !== 'purchase' || !merchant) return undefined;
  const account = mockTrackingAccounts.find((candidate) => candidate.cardLast4 === cardLast4);
  if (!account) return undefined;

  const day = receivedAt.slice(0, 10);
  // Mock Uber is a cash record that the sample SMS text (card •4821) is documented to match, so account is not compared.
  const transaction = mockTransactionService
    .getTransactions()
    .find(
      (candidate) =>
        candidate.amount === -amount && candidate.date === day && candidate.title.toLowerCase() === merchant.toLowerCase(),
    );
  return transaction
    ? { transactionId: transaction.id, merchant: transaction.title, category: transaction.category, account }
    : undefined;
};

/** A reviewed message keeps the record it was linked to; the others follow the current transactions. */
const withMatch = (message: BankMessage): BankMessage =>
  message.status === 'reviewed' ? message : { ...message, match: findMatch(message) };

/** Reads amount, date, card and merchant from SMS text; `null` when the amount or date is missing. */
const parse = (body: string): ParsedMessage | null => {
  const amount = body.match(AMOUNT);
  const dateTime = body.match(DATE_TIME);
  if (!amount || !dateTime) return null;

  const value = Number(amount[1].replace(/,/g, ''));
  if (!(value > 0)) return null;

  const [, day, month, year, hour, minute] = dateTime;
  const kind = WITHDRAWAL.test(body) ? 'withdrawal' : 'purchase';
  return {
    id: `sms-${Date.now()}`,
    bank: KNOWN_BANKS.find((bank) => body.toLowerCase().includes(bank.toLowerCase())) ?? UNKNOWN_BANK,
    receivedAt: `${year}-${month}-${day}T${hour}:${minute}`,
    body,
    amount: value,
    kind,
    status: 'new',
    merchant: kind === 'purchase' ? body.match(MERCHANT)?.[1].trim() : undefined,
    cardLast4: body.match(CARD)?.[1],
  };
};

const reviewFor = (message: BankMessage): BankMessageReview => {
  if (message.kind === 'withdrawal') return 'withdrawal';
  return message.match ? 'match' : 'unmatched';
};

let messages: BankMessage[] = mockBankMessages;

const findMessage = (id: string): BankMessage => {
  const message = messages.find((candidate) => candidate.id === id);
  if (!message) throw new AppError(strings.common.genericError);
  return message;
};

const updateMessage = (id: string, changes: Partial<BankMessage>): BankMessage => {
  const updated = { ...findMessage(id), ...changes };
  messages = messages.map((message) => (message.id === id ? updated : message));
  return updated;
};

export const mockSmsService: SmsService = {
  getMessages: () => messages.map(withMatch),

  getMessage(id) {
    const message = messages.find((candidate) => candidate.id === id);
    return message && withMatch(message);
  },

  getTrackingAccounts: () => mockTrackingAccounts,

  getSharedText: () => mockSharedMessageText,

  async importMessage(text) {
    await wait(RESPONSE_DELAY_MS);
    const body = text.trim();

    const existing = messages.find((message) => message.body === body);
    if (existing) {
      return withMatch(existing.status === 'ignored' ? updateMessage(existing.id, { status: 'new' }) : existing);
    }

    const parsed = parse(body);
    if (!parsed) return null;

    messages = [parsed, ...messages];
    return withMatch(parsed);
  },

  async extractDetails(id) {
    await wait(EXTRACTION_DELAY_MS);
    return reviewFor(withMatch(findMessage(id)));
  },

  async confirmMatch(id) {
    await wait(RESPONSE_DELAY_MS);
    return updateMessage(id, { match: findMatch(findMessage(id)), status: 'reviewed' });
  },

  async ignoreMessage(id) {
    await wait(RESPONSE_DELAY_MS);
    updateMessage(id, { status: 'ignored' });
  },
};
