import { BankMessage, BankMessageReview } from '@/types/sms';

/** Which review a bank message needs: withdrawals are classified, purchases are linked to their match or verified by hand. */
export const reviewTypeOf = (message: BankMessage): BankMessageReview => {
  if (message.kind === 'withdrawal') return 'withdrawal';
  return message.match ? 'match' : 'unmatched';
};
