package com.financeapp.sms;

import com.financeapp.sms.domain.Account;
import com.financeapp.sms.domain.SmsMessage;
import com.financeapp.sms.domain.SmsSender;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxStatus;
import com.financeapp.sms.repo.AccountKey;
import com.financeapp.sms.repo.AccountRepository;
import com.financeapp.sms.repo.SmsMessageRepository;
import com.financeapp.sms.repo.SmsSenderRepository;
import com.financeapp.sms.repo.TransactionRepository;
import java.lang.reflect.InvocationHandler;
import java.lang.reflect.Method;
import java.lang.reflect.Proxy;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Optional;

/**
 * In-memory stand-ins for the Spring Data repositories, built with dynamic proxies so they compile against
 * the real interfaces without implementing every JpaRepository method. Objects are shared by reference,
 * like managed JPA entities inside one transaction. Locking/rollback are not simulated (see the README's
 * PostgreSQL lock test for that).
 */
public final class InMemoryRepos {
    public final Map<Long, Account> accounts = new LinkedHashMap<>();
    public final Map<Long, Transaction> transactions = new LinkedHashMap<>();
    public final Map<Long, SmsMessage> messages = new LinkedHashMap<>();
    public final Map<Long, SmsSender> senders = new LinkedHashMap<>();
    private long seq = 1;

    public AccountRepository accountRepository() {
        return proxy(AccountRepository.class, (m, a) -> switch (m.getName()) {
            case "save" -> save(accounts, a[0]);
            case "findById" -> Optional.ofNullable(accounts.get((Long) a[0]));
            case "findKeysByUserId" -> accounts.values().stream().filter(x -> x.getUserId().equals(a[0]))
                    .map(x -> new AccountKey(x.getId(), x.getInstitution(), x.getLast4(), x.getCurrency())).toList();
            case "lockByIdAndUserId" -> Optional.ofNullable(accounts.get((Long) a[0])).filter(x -> x.getUserId().equals(a[1]));
            default -> throw new UnsupportedOperationException(m.getName());
        });
    }

    public TransactionRepository transactionRepository() {
        return proxy(TransactionRepository.class, (m, a) -> switch (m.getName()) {
            case "save" -> save(transactions, a[0]);
            case "findById" -> Optional.ofNullable(transactions.get((Long) a[0]));
            case "lockByIdAndUserId" -> Optional.ofNullable(transactions.get((Long) a[0])).filter(x -> x.getUserId().equals(a[1]));
            case "findByUserIdAndStatusOrderByOccurredAtDesc" -> transactions.values().stream()
                    .filter(x -> x.getUserId().equals(a[0]) && x.getStatus() == a[1])
                    .sorted(Comparator.comparing(Transaction::getOccurredAt).reversed()).toList();
            case "findNear" -> transactions.values().stream()
                    .filter(x -> x.getUserId().equals(a[0]) && x.getAmount().compareTo((BigDecimal) a[1]) == 0
                            && x.getStatus() != (TxStatus) a[2]
                            && !x.getOccurredAt().isBefore((Instant) a[3]) && !x.getOccurredAt().isAfter((Instant) a[4]))
                    .sorted(Comparator.comparing(Transaction::getOccurredAt)).toList();
            default -> throw new UnsupportedOperationException(m.getName());
        });
    }

    public SmsMessageRepository smsMessageRepository() {
        return proxy(SmsMessageRepository.class, (m, a) -> switch (m.getName()) {
            case "save" -> save(messages, a[0]);
            case "findById" -> Optional.ofNullable(messages.get((Long) a[0]));
            case "existsByUserIdAndBodyHash" -> messages.values().stream()
                    .anyMatch(x -> x.getUserId().equals(a[0]) && x.getBodyHash().equals(a[1]));
            default -> throw new UnsupportedOperationException(m.getName());
        });
    }

    public SmsSenderRepository smsSenderRepository() {
        return proxy(SmsSenderRepository.class, (m, a) -> switch (m.getName()) {
            case "save" -> save(senders, a[0]);
            case "findById" -> Optional.ofNullable(senders.get((Long) a[0]));
            case "findByUserId" -> senders.values().stream().filter(x -> x.getUserId().equals(a[0])).toList();
            case "findByUserIdAndSenderId" -> senders.values().stream()
                    .filter(x -> x.getUserId().equals(a[0]) && x.getSenderId().equals(a[1])).findFirst();
            default -> throw new UnsupportedOperationException(m.getName());
        });
    }

    @SuppressWarnings("unchecked")
    private <T> Object save(Map<Long, T> store, Object entity) throws ReflectiveOperationException {
        Long id = (Long) entity.getClass().getMethod("getId").invoke(entity);
        if (id == null) {
            id = seq++;
            entity.getClass().getMethod("setId", Long.class).invoke(entity, id);
        }
        store.put(id, (T) entity);
        return entity;
    }

    private interface Handler { Object handle(Method m, Object[] a) throws Exception; }

    @SuppressWarnings("unchecked")
    private static <R> R proxy(Class<R> type, Handler h) {
        InvocationHandler ih = (p, m, a) -> switch (m.getName()) {
            case "toString" -> "InMemory" + type.getSimpleName();
            case "hashCode" -> System.identityHashCode(p);
            case "equals" -> p == a[0];
            default -> h.handle(m, a == null ? new Object[0] : a);
        };
        return (R) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[]{type}, ih);
    }
}
