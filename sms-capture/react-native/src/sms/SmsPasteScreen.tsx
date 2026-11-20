// Paste a bank SMS by hand. Works on iOS and emulators too; useful for demos and for users who
// prefer not to grant SMS permission (proposal: "demonstrate the parser with messages a user chooses to share").
import { useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import type { IngestResult, SmsApi } from './smsApi';

export default function SmsPasteScreen(props: { api: SmsApi; onChanged?: () => void }) {
  const [sender, setSender] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setBusy(true); setError(null); setResult(null);
    try {
      const [r] = await props.api.ingest([{ sender: sender.trim(), body: body.trim(), receivedAt: Date.now() }]);
      setResult(r ?? null);
      if (r && (r.status === 'APPLIED' || r.status === 'DRAFT')) props.onChanged?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={s.wrap}>
      <Text style={s.label}>Sender (bank or app)</Text>
      <TextInput value={sender} onChangeText={setSender} placeholder="NileBank" style={s.input} autoCapitalize="none" />
      <Text style={s.label}>SMS text</Text>
      <TextInput value={body} onChangeText={setBody} multiline style={[s.input, s.multi]} />
      <Pressable onPress={submit} disabled={busy || !sender.trim() || !body.trim()} style={s.btn} accessibilityRole="button">
        {busy ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Add from SMS</Text>}
      </Pressable>
      {error ? <Text style={s.error}>{error}</Text> : null}
      {result ? (
        <Text style={s.result}>
          {result.status === 'APPLIED' && `Added: ${result.type} ${result.amount} ${result.currency} (${result.institution})`}
          {result.status === 'DRAFT' && `Saved for review: ${result.amount ?? ''} ${result.currency ?? ''} (${result.reviewReasons.join(', ')})`}
          {result.status === 'IGNORED' && 'Not a transaction (OTP, offer, alert or declined payment).'}
          {result.status === 'ALREADY_RECEIVED' && 'This SMS was already added.'}
        </Text>
      ) : null}
    </View>
  );
}

const s = StyleSheet.create({
  wrap: { padding: 16, gap: 6 },
  label: { fontWeight: '600', marginTop: 8 },
  input: { minHeight: 44, borderWidth: 1, borderColor: '#c9c9c9', borderRadius: 8, paddingHorizontal: 12, fontSize: 16 },
  multi: { minHeight: 120, textAlignVertical: 'top', paddingTop: 10 },
  btn: { marginTop: 14, minHeight: 48, borderRadius: 10, backgroundColor: '#1d4ed8', alignItems: 'center', justifyContent: 'center' },
  btnText: { color: '#fff', fontWeight: '600', fontSize: 16 },
  error: { color: '#b00020', marginTop: 8 },
  result: { marginTop: 12, fontSize: 15 },
});
