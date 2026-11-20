package com.financeapp.sms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.financeapp.sms.config.SmsProperties;
import com.financeapp.sms.domain.Account;
import com.financeapp.sms.domain.AccountType;
import com.financeapp.sms.domain.SmsMessage;
import com.financeapp.sms.domain.SmsStatus;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxStatus;
import com.financeapp.sms.domain.TxType;
import com.financeapp.sms.ledger.Ledger;
import com.financeapp.sms.parser.SmsParser;
import com.financeapp.sms.service.AccountMatcher;
import com.financeapp.sms.service.IngestResult;
import com.financeapp.sms.service.SenderRegistry;
import com.financeapp.sms.service.SmsIngestService;
import com.financeapp.sms.service.SmsIngestService.IncomingSms;
import com.financeapp.sms.service.SmsReviewService;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.TreeMap;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.web.server.ResponseStatusException;

/** End-to-end: SMS text -> parser -> account matching -> balance updates -> review, with in-memory repositories. */
class SmsIngestFlowTest {
    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");
    private static SmsParser parser;

    private InMemoryRepos db;
    private SmsIngestService ingest;
    private SmsReviewService review;
    private SenderRegistry senders;
    private Account nileCard, luxorAcc, cairoWallet;

    @BeforeEach
    void setUp() throws Exception {
        if (parser == null) {
            try (InputStream in = getClass().getResourceAsStream("/sms/sms-model.tsv.gz")) { parser = SmsParser.load(in); }
        }
        db = new InMemoryRepos();
        SmsProperties props = new SmsProperties();
        senders = new SenderRegistry(props, db.smsSenderRepository());
        ingest = new SmsIngestService(parser, props, senders, new AccountMatcher(db.accountRepository()),
                db.accountRepository(), db.transactionRepository(), db.smsMessageRepository());
        review = new SmsReviewService(db.transactionRepository(), db.accountRepository(), db.smsMessageRepository());
        nileCard = save(new Account(1L, "NileBank card", AccountType.CARD, "NileBank", "6402", new BigDecimal("10000.00")));
        luxorAcc = save(new Account(1L, "Luxor current", AccountType.BANK, "Luxor Bank", "2291", new BigDecimal("5000.00")));
        cairoWallet = save(new Account(1L, "Cairo Wallet", AccountType.WALLET, "Cairo Wallet", null, new BigDecimal("2000.00")));
    }

    private Account save(Account a) { return db.accountRepository().save(a); }

    private static long at(int day, int h, int m) {
        return LocalDateTime.of(2026, 11, day, h, m).atZone(CAIRO).toInstant().toEpochMilli();
    }

    private IngestResult in(String sender, String body, long when) { return ingest.ingestOne(1L, new IncomingSms(sender, body, when)); }

    private static void money(String expected, BigDecimal actual, String what) {
        assertEquals(0, new BigDecimal(expected).compareTo(actual), what + " = " + actual);
    }

    private static final String NILE_PURCHASE =
            "تم خصم مبلغ 1,250.00 جنيه من بطاقتكم رقم ****6402 لدى KENZ BAKERY MAADI بتاريخ 18/11/26 الساعة 14:05. الرصيد المتاح 8,750.00 جنيه.";

    @Test
    void purchaseIsAppliedToTheMatchingCardWithDateTypeAndBank() {
        IngestResult r = in("NileBank", NILE_PURCHASE, at(18, 14, 5));
        assertEquals("APPLIED", r.status());
        assertEquals("NileBank", r.institution());
        assertEquals("DEBIT", r.type());
        assertEquals(nileCard.getId(), r.accountId());
        money("1250.00", r.amount(), "amount");
        assertEquals(LocalDateTime.of(2026, 11, 18, 14, 5).atZone(CAIRO).toInstant(), r.occurredAt());
        money("8750.00", nileCard.getBalance(), "card balance");
        Transaction t = db.transactions.get(r.transactionId());
        assertEquals("KENZ BAKERY MAADI", t.getMerchant());
        assertEquals("card", t.getChannel());
        assertNull(t.getBalanceDifference(), "app balance agrees with the bank's");
    }

    @Test
    void sameSmsUploadedTwiceCountsOnce() {
        in("NileBank", NILE_PURCHASE, at(18, 14, 5));
        IngestResult again = in("NileBank", NILE_PURCHASE, at(18, 14, 5));
        assertEquals("ALREADY_RECEIVED", again.status());
        money("8750.00", nileCard.getBalance(), "card balance");
        assertEquals(1, db.transactions.size());
    }

    @Test
    void nearDuplicateGoesToReviewInsteadOfCountingTwice() {
        in("NileBank", NILE_PURCHASE, at(18, 14, 5));
        IngestResult dup = in("NileBank", NILE_PURCHASE.replace("14:05", "14:09").replace("8,750.00", "7,500.00"), at(18, 14, 9));
        assertEquals("DRAFT", dup.status());
        assertTrue(dup.reviewReasons().contains("POSSIBLE_DUPLICATE"), dup.reviewReasons().toString());
        money("8750.00", nileCard.getBalance(), "balance untouched until reviewed");
        // The user says it really was a second purchase:
        review.confirm(1L, dup.transactionId(), null);
        money("7500.00", nileCard.getBalance(), "after confirming the second purchase");
    }

    @Test
    void otpAndOffersAreIgnoredAndTheirTextIsNotStored() {
        IngestResult r = in("NileBank",
                "رمز التحقق لمرة واحدة: 615204 لإتمام عملية شراء بمبلغ 899 جنيه لدى TAKA SHOES NASR CITY. صالح لمدة 10 دقائق. لا تشارك الرمز مع أي شخص.",
                at(18, 15, 0));
        assertEquals("IGNORED", r.status());
        SmsMessage m = db.messages.values().iterator().next();
        assertNull(m.getBody(), "OTP text must not be stored");
        assertEquals(SmsStatus.IGNORED, m.getStatus());
        IngestResult promo = in("Luxor Bank",
                "Luxor Bank: You are pre-approved for a personal loan of up to EGP 150,000 at a competitive rate. Visit any branch before 30-11-2026 to apply.",
                at(18, 15, 1));
        assertEquals("IGNORED", promo.status());
        money("10000.00", nileCard.getBalance(), "nothing changed");
        assertEquals(0, db.transactions.size());
    }

    @Test
    void newCardBecomesDraftThenTheAppLearnsWhichAccountItIs() {
        String sphinx = "Your credit card ending with#5531 was charged for EGP 640.00 at NOUR ELECTRONICS 6OCT on 12/11/26 at 16:20. Available limit is EGP 18,750.01.";
        IngestResult r = in("SphinxCard", sphinx, at(12, 16, 20));
        assertEquals("DRAFT", r.status());
        assertEquals(List.of("NO_ACCOUNT"), r.reviewReasons());

        Account card = save(new Account(1L, "Credit card", AccountType.CARD, null, null, BigDecimal.ZERO));
        review.confirm(1L, r.transactionId(), new SmsReviewService.Edits(card.getId(), null, null, null, null, null, "Electronics"));
        money("-640.00", card.getBalance(), "credit card balance");
        assertEquals("SphinxCard", card.getInstitution());
        assertEquals("5531", card.getLast4());

        IngestResult next = in("SphinxCard", sphinx.replace("640.00", "75.50").replace("16:20", "18:02"), at(12, 18, 2));
        assertEquals("APPLIED", next.status(), "matched automatically now");
        money("-715.50", card.getBalance(), "after second purchase");
    }

    @Test
    void rejectingAndEditingKeepBalancesExact() {
        IngestResult r = in("NileBank", NILE_PURCHASE, at(18, 14, 5));
        review.confirm(1L, r.transactionId(), new SmsReviewService.Edits(null, null, new BigDecimal("1200.00"), null, null, null, null));
        money("8800.00", nileCard.getBalance(), "after correcting amount to 1,200");
        review.confirm(1L, r.transactionId(), new SmsReviewService.Edits(luxorAcc.getId(), null, null, null, null, null, null));
        money("10000.00", nileCard.getBalance(), "moved off the card");
        money("3800.00", luxorAcc.getBalance(), "moved to Luxor");
        review.reject(1L, r.transactionId());
        money("5000.00", luxorAcc.getBalance(), "after reject");
        assertEquals(TxStatus.REJECTED, db.transactions.get(r.transactionId()).getStatus());
        assertThrows(ResponseStatusException.class, () -> review.confirm(1L, r.transactionId(), null));
    }

    @Test
    void transferBetweenOwnAccountsIsLinkedAndNotSpending() {
        IngestResult out = in("Luxor Bank",
                "Luxor Bank: Your A/C xx2291 was debited EGP 1,000.00 on 18-11-2026 for InstaPay transfer to MONA HEGAZY. Ref 77209183456. Avl Bal EGP 4,000.00.",
                at(18, 10, 0));
        IngestResult inn = in("NileBank",
                "تم استلام تحويل وارد عبر انستاباي بمبلغ 1,000.00 جنيه من منى حجازي إلى حسابكم ****6402 بتاريخ 18/11/2026. الرصيد المتاح 11,000.00 جنيه.",
                at(18, 10, 2));
        assertEquals("APPLIED", out.status());
        assertEquals("APPLIED", inn.status());
        Transaction a = db.transactions.get(out.transactionId()), b = db.transactions.get(inn.transactionId());
        assertEquals(TxType.TRANSFER_OUT, a.getType());
        assertEquals(TxType.TRANSFER_IN, b.getType());
        assertNotNull(a.getTransferGroup(), "linked");
        assertEquals(a.getTransferGroup(), b.getTransferGroup());
        assertTrue(a.isInternalTransfer() && b.isInternalTransfer(), "internal");
        assertTrue(!Ledger.countsAsSpending(a), "not counted as spending");
        money("4000.00", luxorAcc.getBalance(), "Luxor");
        money("11000.00", nileCard.getBalance(), "NileBank");
    }

    @Test
    void unknownSenderAndForeignCurrencyNeedReview() {
        IngestResult u = in("MyBank", NILE_PURCHASE, at(18, 14, 5));
        assertEquals("DRAFT", u.status());
        assertTrue(u.reviewReasons().contains("UNKNOWN_SENDER"), u.reviewReasons().toString());

        senders.upsert(1L, "MyBank", "NileBank", AccountType.BANK, true);   // user says MyBank = NileBank
        IngestResult known = in("MyBank", NILE_PURCHASE.replace("1,250.00", "99.00").replace("14:05", "20:30"), at(18, 20, 30));
        assertEquals("APPLIED", known.status());

        Account card = save(new Account(1L, "Sphinx", AccountType.CARD, "SphinxCard", "5531", BigDecimal.ZERO));
        IngestResult usd = in("SphinxCard",
                "SphinxCard: Online purchase of USD 12.99 at SHAMS STREAM with card **5531 on 15/11/2026. The EGP equivalent will appear on your statement.",
                at(15, 9, 0));
        assertEquals("DRAFT", usd.status());
        assertEquals("USD", usd.currency());
        assertTrue(usd.reviewReasons().contains("FOREIGN_CURRENCY"), usd.reviewReasons().toString());
        ResponseStatusException ex = assertThrows(ResponseStatusException.class, () -> review.confirm(1L, usd.transactionId(), null));
        assertTrue(ex.getMessage().contains("EGP"), ex.getMessage());
        money("0", card.getBalance(), "nothing applied by the failed confirm");
        review.confirm(1L, usd.transactionId(), new SmsReviewService.Edits(null, null, new BigDecimal("645.10"), null, null, null, null));
        money("-645.10", card.getBalance(), "charged in EGP");
        assertEquals("EGP", db.transactions.get(usd.transactionId()).getCurrency());
    }

    @Test
    void usersCannotSeeOrChangeEachOthersTransactions() {
        IngestResult r = in("NileBank", NILE_PURCHASE, at(18, 14, 5));
        assertThrows(ResponseStatusException.class, () -> review.reject(2L, r.transactionId()));
        assertThrows(ResponseStatusException.class, () -> review.confirm(2L, r.transactionId(), null));
        assertEquals(0, review.drafts(2L).size());
        money("8750.00", nileCard.getBalance(), "unchanged");
    }

    /** All 1,000 synthetic SMS + random confirms/rejects: every balance must equal opening + counted transactions. */
    @Test
    void wholeDatasetKeepsEveryBalanceConsistent() throws Exception {
        db = new InMemoryRepos();
        SmsProperties props = new SmsProperties();
        SenderRegistry reg = new SenderRegistry(props, db.smsSenderRepository());
        ingest = new SmsIngestService(parser, props, reg, new AccountMatcher(db.accountRepository()),
                db.accountRepository(), db.transactionRepository(), db.smsMessageRepository());
        review = new SmsReviewService(db.transactionRepository(), db.accountRepository(), db.smsMessageRepository());
        BigDecimal opening = new BigDecimal("100000.00");
        Map<String, Account> byBank = new HashMap<>();
        for (SmsProperties.Sender s : props.getSenders()) {
            byBank.put(s.getName(), save(new Account(1L, s.getName(), s.getKind(), s.getName(), null, opening)));
        }

        Map<String, Integer> outcomes = new TreeMap<>();
        long t0 = at(1, 8, 0);
        int i = 0;
        try (BufferedReader r = new BufferedReader(new InputStreamReader(
                getClass().getResourceAsStream("/sms/sms_dataset.tsv"), StandardCharsets.UTF_8))) {
            String line;
            while ((line = r.readLine()) != null) {
                if (line.startsWith("#")) continue;
                String[] c = line.split("\t", 3);
                String body = c[2].replace("\\n", "\n").replace("\\t", "\t").replace("\\\\", "\\");
                IngestResult res = ingest.ingestOne(1L, new IncomingSms(c[1], body, t0 + 7L * 60_000 * i++));
                outcomes.merge(res.status(), 1, Integer::sum);
            }
        }
        Random rnd = new Random(7);
        for (Transaction t : review.drafts(1L)) {
            if (rnd.nextInt(5) == 0) { review.reject(1L, t.getId()); continue; }
            Account acc = byBank.get(t.getInstitution());
            String type = t.getType() == TxType.OTHER ? "DEBIT" : null;
            BigDecimal amount = "EGP".equals(t.getCurrency()) ? null : t.getAmount().multiply(new BigDecimal("50"));
            review.confirm(1L, t.getId(), new SmsReviewService.Edits(acc.getId(), type, amount, null, null, null, null));
        }
        for (Transaction t : List.copyOf(db.transactions.values())) {
            if (t.getStatus() == TxStatus.CONFIRMED && rnd.nextInt(10) == 0) review.reject(1L, t.getId());
        }

        for (Account a : db.accounts.values()) {
            BigDecimal expected = opening;
            for (Transaction t : db.transactions.values()) {
                if (t.isApplied() && a.getId().equals(t.getAccountId())) expected = expected.add(Ledger.delta(t.getType(), t.getAmount(), t.getFee()));
            }
            money(expected.toPlainString(), a.getBalance(), a.getName());
        }
        for (Transaction t : db.transactions.values()) {
            assertEquals(t.isApplied(), t.getStatus() == TxStatus.CONFIRMED, "applied <=> confirmed for " + t.getId());
        }
        assertEquals(0, review.drafts(1L).size());
        System.out.println("    dataset outcomes: " + outcomes + ", transactions: " + db.transactions.size());
    }
}
