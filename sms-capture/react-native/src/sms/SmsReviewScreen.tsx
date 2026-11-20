// Review list for SMS transactions that were not applied automatically (proposal: "suggests details for review").
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator, Alert, FlatList, Pressable, RefreshControl, StyleSheet, Text, TextInput, View,
} from 'react-native';
import type { ReviewReason, SmsApi, SmsTransaction, TxType } from './smsApi';

export interface AccountOption { id: number; name: string; institution?: string | null; last4?: string | null }
type Lang = 'en' | 'ar';

const T = {
  en: {
    title: 'SMS transactions to review', empty: 'Nothing to review', confirm: 'Confirm', reject: 'Reject',
    account: 'Account', type: 'Type', amount: 'Amount', fee: 'Fee', own: 'Between your own accounts',
    bank: 'Bank balance in SMS', error: 'Could not save', rejectQ: 'Reject this transaction?', cancel: 'Cancel',
  },
  ar: {
    title: 'معاملات من الرسائل للمراجعة', empty: 'لا يوجد ما يحتاج مراجعة', confirm: 'تأكيد', reject: 'رفض',
    account: 'الحساب', type: 'النوع', amount: 'المبلغ', fee: 'الرسوم', own: 'تحويل بين حساباتك',
    bank: 'رصيد البنك في الرسالة', error: 'تعذر الحفظ', rejectQ: 'رفض هذه المعاملة؟', cancel: 'إلغاء',
  },
} as const;

const TYPE_LABEL: Record<Lang, Record<TxType, string>> = {
  en: { DEBIT: 'Purchase', CREDIT: 'Money in', TRANSFER_OUT: 'Transfer sent', TRANSFER_IN: 'Transfer received',
        ATM_WITHDRAWAL: 'ATM withdrawal', BILL_PAYMENT: 'Bill payment', OTHER: 'Choose a type' },
  ar: { DEBIT: 'شراء', CREDIT: 'إيداع', TRANSFER_OUT: 'تحويل صادر', TRANSFER_IN: 'تحويل وارد',
        ATM_WITHDRAWAL: 'سحب نقدي', BILL_PAYMENT: 'دفع فاتورة', OTHER: 'اختر النوع' },
};

const REASON_LABEL: Record<Lang, Record<ReviewReason, string>> = {
  en: { NO_ACCOUNT: 'Choose the account', UNKNOWN_SENDER: 'Unknown sender', UNKNOWN_TYPE: 'Type unclear',
        LOW_CONFIDENCE: 'Please check the details', FOREIGN_CURRENCY: 'Foreign currency: enter the EGP amount',
        POSSIBLE_DUPLICATE: 'Looks like a duplicate' },
  ar: { NO_ACCOUNT: 'اختر الحساب', UNKNOWN_SENDER: 'مرسل غير معروف', UNKNOWN_TYPE: 'النوع غير واضح',
        LOW_CONFIDENCE: 'راجع التفاصيل', FOREIGN_CURRENCY: 'عملة أجنبية: أدخل المبلغ بالجنيه',
        POSSIBLE_DUPLICATE: 'قد تكون مكررة' },
};

const TYPES: TxType[] = ['DEBIT', 'CREDIT', 'TRANSFER_OUT', 'TRANSFER_IN', 'ATM_WITHDRAWAL', 'BILL_PAYMENT'];

function money(n: number, currency: string, lang: Lang): string {
  try {
    return new Intl.NumberFormat(lang === 'ar' ? 'ar-EG' : 'en-EG', { style: 'currency', currency }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency}`;
  }
}

function DraftCard(props: {
  tx: SmsTransaction; accounts: AccountOption[]; lang: Lang;
  onConfirm: (tx: SmsTransaction, edits: { accountId?: number; type?: TxType; amount?: number }) => Promise<void>;
  onReject: (tx: SmsTransaction) => void;
}) {
  const { tx, accounts, lang } = props;
  const t = T[lang];
  const [accountId, setAccountId] = useState<number | null>(tx.accountId);
  const [type, setType] = useState<TxType>(tx.type);
  const [amount, setAmount] = useState(String(tx.amount));
  const [busy, setBusy] = useState(false);
  const rtl = lang === 'ar';
  const parsedAmount = Number(amount.replace(/[٠-٩]/g, (d) => String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace(/,/g, ''));
  const canConfirm = accountId !== null && type !== 'OTHER' && parsedAmount > 0 && !busy;

  const confirm = async () => {
    setBusy(true);
    try {
      await props.onConfirm(tx, {
        accountId: accountId ?? undefined,
        type: type !== tx.type ? type : undefined,
        amount: parsedAmount !== tx.amount ? parsedAmount : undefined,
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={[s.card, rtl && s.rtl]}>
      <Text style={s.amount}>{money(tx.amount, tx.currency, lang)}</Text>
      <Text style={s.line}>
        {TYPE_LABEL[lang][tx.type]} · {tx.institution ?? '?'}{tx.channel ? ` · ${tx.channel}` : ''}
      </Text>
      {tx.merchant ? <Text style={s.line}>{tx.merchant}</Text> : null}
      <Text style={s.muted}>{new Date(tx.occurredAt).toLocaleString(lang === 'ar' ? 'ar-EG' : 'en-EG')}</Text>
      {tx.fee > 0 ? <Text style={s.muted}>{t.fee}: {money(tx.fee, tx.currency, lang)}</Text> : null}
      {tx.internalTransfer ? <Text style={s.muted}>{t.own}</Text> : null}
      {tx.reportedBalance !== null ? (
        <Text style={s.muted}>{t.bank}: {money(tx.reportedBalance, tx.currency, lang)}</Text>
      ) : null}

      <View style={s.chips}>
        {tx.reviewReasons.map((r) => (
          <Text key={r} style={s.reason}>{REASON_LABEL[lang][r] ?? r}</Text>
        ))}
      </View>

      <Text style={s.label}>{t.account}</Text>
      <View style={s.chips}>
        {accounts.map((a) => (
          <Pressable key={a.id} onPress={() => setAccountId(a.id)} accessibilityRole="button"
                     style={[s.chip, accountId === a.id && s.chipOn]}>
            <Text style={accountId === a.id ? s.chipTextOn : undefined}>
              {a.name}{a.last4 ? ` ••${a.last4}` : ''}
            </Text>
          </Pressable>
        ))}
      </View>

      {tx.type === 'OTHER' || tx.reviewReasons.includes('UNKNOWN_TYPE') || tx.reviewReasons.includes('LOW_CONFIDENCE') ? (
        <>
          <Text style={s.label}>{t.type}</Text>
          <View style={s.chips}>
            {TYPES.map((ty) => (
              <Pressable key={ty} onPress={() => setType(ty)} accessibilityRole="button"
                         style={[s.chip, type === ty && s.chipOn]}>
                <Text style={type === ty ? s.chipTextOn : undefined}>{TYPE_LABEL[lang][ty]}</Text>
              </Pressable>
            ))}
          </View>
        </>
      ) : null}

      {tx.reviewReasons.includes('FOREIGN_CURRENCY') || tx.reviewReasons.includes('LOW_CONFIDENCE') ? (
        <>
          <Text style={s.label}>{t.amount} (EGP)</Text>
          <TextInput value={amount} onChangeText={setAmount} keyboardType="decimal-pad" style={s.input} />
        </>
      ) : null}

      <View style={s.actions}>
        <Pressable disabled={busy} onPress={() => props.onReject(tx)} style={[s.btn, s.btnGhost]} accessibilityRole="button">
          <Text>{t.reject}</Text>
        </Pressable>
        <Pressable disabled={!canConfirm} onPress={confirm} accessibilityRole="button"
                   style={[s.btn, canConfirm ? s.btnPrimary : s.btnDisabled]}>
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={s.btnPrimaryText}>{t.confirm}</Text>}
        </Pressable>
      </View>
    </View>
  );
}

export default function SmsReviewScreen(props: {
  api: SmsApi; accounts: AccountOption[]; lang?: Lang;
  /** Called after any change so the app can reload balances, budgets and charts. */
  onChanged?: () => void;
}) {
  const lang: Lang = props.lang ?? 'en';
  const t = T[lang];
  const { api, onChanged } = props;
  const [items, setItems] = useState<SmsTransaction[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await api.getDrafts());
    } catch (e) {
      Alert.alert(t.error, e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [api, t.error]);

  useEffect(() => { void load(); }, [load]);

  const onConfirm = async (tx: SmsTransaction, edits: { accountId?: number; type?: TxType; amount?: number }) => {
    try {
      await api.confirm(tx.id, edits);
      setItems((prev) => prev.filter((x) => x.id !== tx.id));
      onChanged?.();
    } catch (e) {
      Alert.alert(t.error, e instanceof Error ? e.message : String(e));
    }
  };

  const onReject = (tx: SmsTransaction) => {
    Alert.alert(t.rejectQ, money(tx.amount, tx.currency, lang), [
      { text: t.cancel, style: 'cancel' },
      {
        text: t.reject, style: 'destructive',
        onPress: async () => {
          try {
            await api.reject(tx.id);
            setItems((prev) => prev.filter((x) => x.id !== tx.id));
            onChanged?.();
          } catch (e) {
            Alert.alert(t.error, e instanceof Error ? e.message : String(e));
          }
        },
      },
    ]);
  };

  return (
    <FlatList
      data={items}
      keyExtractor={(x) => String(x.id)}
      contentContainerStyle={s.list}
      ListHeaderComponent={<Text style={[s.title, lang === 'ar' && s.rtl]}>{t.title}</Text>}
      ListEmptyComponent={loading ? null : <Text style={s.muted}>{t.empty}</Text>}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
      renderItem={({ item }) => (
        <DraftCard tx={item} accounts={props.accounts} lang={lang} onConfirm={onConfirm} onReject={onReject} />
      )}
    />
  );
}

const s = StyleSheet.create({
  list: { padding: 16, gap: 12 },
  title: { fontSize: 20, fontWeight: '600', marginBottom: 8 },
  rtl: { direction: 'rtl' },
  card: { borderRadius: 12, padding: 16, backgroundColor: '#fff', borderWidth: 1, borderColor: '#e3e3e3', gap: 4 },
  amount: { fontSize: 22, fontWeight: '700' },
  line: { fontSize: 15 },
  muted: { fontSize: 13, color: '#666' },
  label: { marginTop: 10, fontSize: 13, fontWeight: '600' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 4 },
  reason: { fontSize: 12, color: '#8a4b00', backgroundColor: '#fff3e0', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8 },
  chip: { minHeight: 44, justifyContent: 'center', paddingHorizontal: 12, borderRadius: 22, borderWidth: 1, borderColor: '#c9c9c9' },
  chipOn: { backgroundColor: '#1d4ed8', borderColor: '#1d4ed8' },
  chipTextOn: { color: '#fff' },
  input: { minHeight: 44, borderWidth: 1, borderColor: '#c9c9c9', borderRadius: 8, paddingHorizontal: 12, fontSize: 16 },
  actions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 12, marginTop: 14 },
  btn: { minHeight: 44, minWidth: 96, alignItems: 'center', justifyContent: 'center', borderRadius: 10, paddingHorizontal: 16 },
  btnGhost: { borderWidth: 1, borderColor: '#c9c9c9' },
  btnPrimary: { backgroundColor: '#1d4ed8' },
  btnDisabled: { backgroundColor: '#9db1e6' },
  btnPrimaryText: { color: '#fff', fontWeight: '600' },
});
