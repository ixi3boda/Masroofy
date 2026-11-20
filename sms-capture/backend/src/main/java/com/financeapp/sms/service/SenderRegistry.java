package com.financeapp.sms.service;

import com.financeapp.sms.config.SmsProperties;
import com.financeapp.sms.domain.AccountType;
import com.financeapp.sms.domain.SmsSender;
import com.financeapp.sms.repo.SmsSenderRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/** Maps an SMS sender ID (e.g. "NileBank", "VF-Cash") to the bank or app it belongs to. */
@Service
public class SenderRegistry {

    public record Institution(String name, AccountType kind) {}
    public record SenderView(String senderId, String institution, AccountType kind, boolean enabled, boolean custom) {}

    private final SmsProperties props;
    private final SmsSenderRepository repo;

    public SenderRegistry(SmsProperties props, SmsSenderRepository repo) { this.props = props; this.repo = repo; }

    /** "VF-Cash", "vf cash", "VFCASH" -> "vfcash". The Android receiver uses the same rule. */
    public static String normalize(String sender) {
        if (sender == null) return "";
        StringBuilder b = new StringBuilder();
        for (char c : sender.toLowerCase(Locale.ROOT).toCharArray()) if (Character.isLetterOrDigit(c)) b.append(c);
        return b.toString();
    }

    public Optional<Institution> resolve(Long userId, String sender) {
        String key = normalize(sender);
        Optional<SmsSender> own = repo.findByUserIdAndSenderId(userId, key);
        if (own.isPresent()) {
            return own.get().isEnabled() ? Optional.of(new Institution(own.get().getInstitution(), own.get().getKind())) : Optional.empty();
        }
        for (SmsProperties.Sender s : props.getSenders()) {
            if (normalize(s.getId()).equals(key)) return Optional.of(new Institution(s.getName(), s.getKind()));
        }
        return Optional.empty();
    }

    /** Defaults merged with the user's own entries; the phone uses the enabled ones as its allow-list. */
    public List<SenderView> list(Long userId) {
        Map<String, SenderView> m = new LinkedHashMap<>();
        for (SmsProperties.Sender s : props.getSenders()) {
            m.put(normalize(s.getId()), new SenderView(normalize(s.getId()), s.getName(), s.getKind(), true, false));
        }
        for (SmsSender s : repo.findByUserId(userId)) {
            m.put(s.getSenderId(), new SenderView(s.getSenderId(), s.getInstitution(), s.getKind(), s.isEnabled(), true));
        }
        return new ArrayList<>(m.values());
    }

    @Transactional
    public SenderView upsert(Long userId, String senderId, String institution, AccountType kind, boolean enabled) {
        String key = normalize(senderId);
        if (key.isEmpty() || institution == null || institution.isBlank()) throw new IllegalArgumentException("senderId and institution are required");
        SmsSender s = repo.findByUserIdAndSenderId(userId, key)
                .orElseGet(() -> new SmsSender(userId, key, institution.trim(), kind, enabled));
        s.setInstitution(institution.trim());
        s.setKind(kind);
        s.setEnabled(enabled);
        repo.save(s);
        return new SenderView(key, s.getInstitution(), kind, enabled, true);
    }
}
