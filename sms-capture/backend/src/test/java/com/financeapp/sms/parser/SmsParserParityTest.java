package com.financeapp.sms.parser;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;

/** The Java parser must give exactly the Python model's output (fixture made by model/export_model.py's pipeline). */
class SmsParserParityTest {

    private static String unesc(String s) {
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '\\' && i + 1 < s.length()) { char n = s.charAt(++i); b.append(n == 'n' ? '\n' : n == 't' ? '\t' : n == 'r' ? '\r' : n); }
            else b.append(c);
        }
        return b.toString();
    }

    private static String str(Object o) { return o == null ? "null" : o.toString(); }

    @Test
    void matchesPythonOnAllFixtureMessages() throws Exception {
        SmsParser p;
        try (InputStream in = SmsParserParityTest.class.getResourceAsStream("/sms/sms-model.tsv.gz")) { p = SmsParser.load(in); }
        List<String> failures = new ArrayList<>();
        int n = 0;
        try (BufferedReader r = new BufferedReader(new InputStreamReader(
                SmsParserParityTest.class.getResourceAsStream("/sms/parity_fixture.tsv"), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                if (line.startsWith("#")) continue;
                String[] c = line.split("\t", -1);
                ParsedSms got = p.parse(unesc(c[1]));
                String[] want = new String[11];
                for (int i = 0; i < 11; i++) want[i] = unesc(c[2 + i]);
                n++;
                check(failures, c[0], "is_transaction", want[0], String.valueOf(got.isTransaction));
                check(failures, c[0], "type", want[1], str(got.type));
                checkNum(failures, c[0], "amount", want[2], got.amount, 1e-9);
                check(failures, c[0], "currency", want[3], str(got.currency));
                checkNum(failures, c[0], "fee", want[4], got.fee, 1e-9);
                checkNum(failures, c[0], "balance", want[5], got.balanceAfter, 1e-9);
                check(failures, c[0], "merchant", want[6], str(got.merchant));
                check(failures, c[0], "channel", want[7], str(got.channel));
                check(failures, c[0], "datetime", want[8], str(got.isoDateTime()));
                check(failures, c[0], "last4", want[9], str(got.accountLast4));
                checkNum(failures, c[0], "confidence", want[10], got.confidence, 1.1e-3);
            }
        }
        assertTrue(n > 1000, "fixture rows: " + n);
        assertEquals(List.of(), failures.subList(0, Math.min(10, failures.size())), failures.size() + " mismatches");
    }

    private static void check(List<String> f, String id, String field, String want, String got) {
        if (!want.equals(got)) f.add(id + " " + field + ": want " + want + " got " + got);
    }

    private static void checkNum(List<String> f, String id, String field, String want, Double got, double tol) {
        if (want.equals("null") ? got != null : (got == null || Math.abs(Double.parseDouble(want) - got) > tol)) {
            f.add(id + " " + field + ": want " + want + " got " + got);
        }
    }
}
