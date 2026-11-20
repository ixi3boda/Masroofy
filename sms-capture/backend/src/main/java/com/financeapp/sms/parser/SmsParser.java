package com.financeapp.sms.parser;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.time.DateTimeException;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.GZIPInputStream;

/**
 * Pure-Java inference for the SMS transaction model trained in Python (model/sms_model.py).
 * No dependencies: usable in Spring Boot and on Android. Thread-safe after construction.
 *
 * Load once:  SmsParser p = SmsParser.load(getClass().getResourceAsStream("/sms/sms-model.tsv.gz"));
 * Use:        ParsedSms r = p.parse(smsBody);
 *
 * Every regex and word list comes from the model file, so retraining in Python and re-exporting
 * (model/export_model.py) updates Java without code changes.
 */
public final class SmsParser {

    // Python's re (str patterns) is Unicode-aware and '.' excludes only '\n': mirror that.
    private static final int RX = Pattern.UNICODE_CHARACTER_CLASS | Pattern.UNIX_LINES;
    private static final int RXI = RX | Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE;
    private static final Pattern DIGITS = Pattern.compile("\\d+", RX);
    private static final Pattern ARABIC = Pattern.compile("[\\u0600-\\u06FF]+", RX);
    private static final Pattern DEC2 = Pattern.compile("\\.\\d\\d$", RX);
    private static final Pattern LATIN1 = Pattern.compile("[A-Za-z]", RX);

    private double lexW, thr;
    private String[] typeClasses, chanClasses, numClasses, tokClasses;
    private double[] typeB, chanB, numB, tokB;
    private final Map<String, double[]> charTerms = new HashMap<>();  // [idf, type w..., chan w...]
    private final Map<String, double[]> wordTerms = new HashMap<>();
    private final Map<String, double[]> lexTerms = new HashMap<>();   // [type w..., chan w...]
    private final Map<String, double[]> numW = new HashMap<>();
    private final Map<String, double[]> tokW = new HashMap<>();
    private final Map<String, Pattern> pat = new HashMap<>();
    private final List<String[]> currency = new ArrayList<>();
    private final Map<String, Integer> monEn = new HashMap<>(), monAr = new HashMap<>();
    private final LinkedHashMap<String, Pattern> lex = new LinkedHashMap<>(), cues = new LinkedHashMap<>(),
            tclass = new LinkedHashMap<>();
    private final Set<String> anchors = new HashSet<>();
    private final Map<String, Integer> expectedCounts = new HashMap<>();

    private SmsParser() {}

    // ------------------------------------------------------------------ loading
    public static SmsParser load(InputStream gzippedModel) throws IOException {
        SmsParser p = new SmsParser();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(new GZIPInputStream(gzippedModel), StandardCharsets.UTF_8))) {
            String section = "", line;
            while ((line = r.readLine()) != null) {
                if (line.isEmpty()) continue;
                if (line.startsWith("#")) { section = line.substring(1); continue; }
                String[] c = line.split("\t", -1);
                for (int i = 0; i < c.length; i++) c[i] = unesc(c[i]);
                p.readRow(section, c);
            }
        }
        if (p.typeClasses == null || p.pat.get("NUM") == null) throw new IOException("invalid SMS model file");
        Map<String, Integer> got = Map.of("char", p.charTerms.size(), "word", p.wordTerms.size(), "lexw", p.lexTerms.size(),
                "numw", p.numW.size(), "tokw", p.tokW.size());
        for (Map.Entry<String, Integer> en : got.entrySet()) {
            Integer want = p.expectedCounts.get(en.getKey());
            if (want == null || !want.equals(en.getValue()))
                throw new IOException("SMS model file damaged: " + en.getKey() + " has " + en.getValue() + " rows, expected " + want);
        }
        return p;
    }

    private void readRow(String section, String[] c) {
        switch (section) {
            case "meta" -> {
                switch (c[0]) {
                    case "lex_w" -> lexW = Double.parseDouble(c[1]);
                    case "thr" -> thr = Double.parseDouble(c[1]);
                    case "type_classes" -> typeClasses = tail(c);
                    case "chan_classes" -> chanClasses = tail(c);
                    case "num_classes" -> numClasses = tail(c);
                    case "tok_classes" -> tokClasses = tail(c);
                    case "type_intercept" -> typeB = nums(c, 1);
                    case "chan_intercept" -> chanB = nums(c, 1);
                    case "num_intercept" -> numB = nums(c, 1);
                    case "tok_intercept" -> tokB = nums(c, 1);
                    default -> { if (c[0].startsWith("count_")) expectedCounts.put(c[0].substring(6), Integer.parseInt(c[1])); }
                }
            }
            case "patterns" -> pat.put(c[0], Pattern.compile(c[2], "I".equals(c[1]) ? RXI : RX));
            case "currency" -> currency.add(new String[]{c[0], c[1]});
            case "months_en" -> monEn.put(c[0], Integer.parseInt(c[1]));
            case "months_ar" -> monAr.put(c[0], Integer.parseInt(c[1]));
            case "lex" -> lex.put(c[0], Pattern.compile(c[1], RXI));
            case "cues" -> cues.put(c[0], Pattern.compile(c[1], RXI));
            case "tclass" -> tclass.put(c[0], Pattern.compile("(?:" + c[1] + ")", RXI));
            case "anchors" -> anchors.add(c[0]);
            case "char" -> charTerms.put(c[0], nums(c, 1));
            case "word" -> wordTerms.put(c[0], nums(c, 1));
            case "lexw" -> lexTerms.put(c[0], nums(c, 1));
            case "numw" -> numW.put(c[0], nums(c, 1));
            case "tokw" -> tokW.put(c[0], nums(c, 1));
            default -> { }
        }
    }

    private static String[] tail(String[] c) { return Arrays.copyOfRange(c, 1, c.length); }
    private static double[] nums(String[] c, int from) {
        double[] d = new double[c.length - from];
        for (int i = from; i < c.length; i++) d[i - from] = Double.parseDouble(c[i]);
        return d;
    }
    private static String unesc(String s) {
        if (s.indexOf('\\') < 0) return s;
        StringBuilder b = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char ch = s.charAt(i);
            if (ch == '\\' && i + 1 < s.length()) {
                char n = s.charAt(++i);
                b.append(n == 'n' ? '\n' : n == 't' ? '\t' : n == 'r' ? '\r' : n);
            } else b.append(ch);
        }
        return b.toString();
    }

    // ------------------------------------------------------------------ text helpers
    /** Emoji and other non-BMP characters -> U+FFFD so offsets match the Python model. */
    public static String bmp(String s) {
        if (s == null) return "";
        StringBuilder b = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); ) {
            int cp = s.codePointAt(i);
            b.append(cp > 0xFFFF ? '�' : (char) cp);
            i += Character.charCount(cp);
        }
        return b.toString();
    }

    /** Arabic-Indic / Persian digits and separators -> ASCII, one char for one char. */
    public static String normalize(String s) {
        char[] a = s.toCharArray();
        for (int i = 0; i < a.length; i++) {
            char ch = a[i];
            if (ch >= '٠' && ch <= '٩') a[i] = (char) ('0' + ch - '٠');
            else if (ch >= '۰' && ch <= '۹') a[i] = (char) ('0' + ch - '۰');
            else if (ch == '٬') a[i] = ',';
            else if (ch == '٫') a[i] = '.';
        }
        return new String(a);
    }

    private static boolean pyWs(char c) {     // Python str.isspace()
        return Character.isWhitespace(c) || c == ' ' || c == ' ' || c == ' ' || c == '\u0085';
    }
    private static String lstrip(String s) { int i = 0; while (i < s.length() && pyWs(s.charAt(i))) i++; return s.substring(i); }
    private static String rstrip(String s) { int i = s.length(); while (i > 0 && pyWs(s.charAt(i - 1))) i--; return s.substring(0, i); }
    private static String sub(String s, int a, int b) {      // Python slicing with clamping
        a = Math.max(0, Math.min(a, s.length())); b = Math.max(a, Math.min(b, s.length()));
        return s.substring(a, b);
    }
    private static String lower(String s) { return s.toLowerCase(Locale.ROOT); }

    private static List<String> findAll(Pattern p, String s) {
        List<String> out = new ArrayList<>();
        Matcher m = p.matcher(s);
        while (m.find()) out.add(m.group());
        return out;
    }

    // ------------------------------------------------------------------ dates, times, currency
    private record Span<T>(int s, int e, T v) {}

    private List<Span<LocalDate>> findDates(String n) {
        List<Span<LocalDate>> out = new ArrayList<>();
        Matcher m = pat.get("DMY").matcher(n);
        while (m.find()) {
            int d = Integer.parseInt(m.group(1)), mo = Integer.parseInt(m.group(3)), y = Integer.parseInt(m.group(4));
            if (y < 100) y += 2000;
            try { out.add(new Span<>(m.start(), m.end(), LocalDate.of(y, mo, d))); } catch (DateTimeException ignored) { }
        }
        m = pat.get("DMON").matcher(n);
        while (m.find()) {
            String name = m.group(2);
            Integer mo = monAr.get(name);
            if (mo == null) mo = monEn.get(lower(name.substring(0, Math.min(3, name.length()))));
            if (mo != null) {
                try { out.add(new Span<>(m.start(), m.end(), LocalDate.of(Integer.parseInt(m.group(3)), mo, Integer.parseInt(m.group(1))))); }
                catch (DateTimeException ignored) { }
            }
        }
        out.sort(Comparator.<Span<LocalDate>>comparingInt(Span::s).thenComparingInt(Span::e).thenComparing(Span::v));
        return out;
    }

    private List<Span<LocalTime>> findTimes(String n) {
        List<Span<LocalTime>> out = new ArrayList<>();
        Matcher m = pat.get("TIME").matcher(n);
        while (m.find()) {
            int h = Integer.parseInt(m.group(1)), mi = Integer.parseInt(m.group(2));
            String ap = m.group(3);
            if (ap != null) {
                boolean pm = lower(ap).equals("pm") || ap.equals("م");
                if (h == 12) h = 0;
                if (pm) h += 12;
            }
            if (h > 23) continue;
            out.add(new Span<>(m.start(), m.end(), LocalTime.of(h, mi)));
        }
        return out;
    }

    private String currencyNear(String n, int s, int e) {
        String rawR = sub(n, e, e + 8), rawL = sub(n, s - 8, s);
        String right = lstrip(rawR), left = rstrip(rawL);
        for (String[] tc : currency) {
            String tok = tc[0];
            if (right.startsWith(tok)) {
                String next = sub(right, tok.length(), tok.length() + 1);
                if (next.isEmpty()) next = " ";
                if (!LATIN1.matcher(next).lookingAt() && rawR.length() - right.length() <= 3) return tc[1];
            }
            if (left.endsWith(tok) && rawL.length() - left.length() <= 3) return tc[1];
        }
        return null;
    }

    // ------------------------------------------------------------------ number candidates
    private record Cand(int s, int e, String txt, double val) {}

    private List<Cand> candidates(String n) {
        List<int[]> masked = new ArrayList<>();
        for (Span<LocalDate> d : findDates(n)) masked.add(new int[]{d.s(), d.e()});
        for (Span<LocalTime> t : findTimes(n)) masked.add(new int[]{t.s(), t.e()});
        List<Cand> out = new ArrayList<>();
        Matcher m = pat.get("XX").matcher(n);
        while (m.find()) out.add(new Cand(m.start(1), m.end(1), m.group(1), Double.parseDouble(m.group(1))));
        m = pat.get("NUM").matcher(n);
        outer:
        while (m.find()) {
            int s = m.start(1), e = m.end(1);
            for (int[] ab : masked) if (ab[0] <= s && s < ab[1]) continue outer;
            String txt = m.group(1);
            double val;
            try { val = Double.parseDouble(txt.replace(",", "")); } catch (NumberFormatException ex) { continue; }
            out.add(new Cand(s, e, txt, val));
        }
        out.sort(Comparator.comparingInt(Cand::s).thenComparingInt(Cand::e).thenComparing(Cand::txt)
                .thenComparingDouble(Cand::val));
        return out;
    }

    private record Cue(String key, int dist) {}

    private Cue nearestCue(String window, boolean left) {
        String best = null; int bd = 1_000_000;
        for (Map.Entry<String, Pattern> en : cues.entrySet()) {
            Matcher m = en.getValue().matcher(window);
            while (m.find()) {
                int d = left ? window.length() - m.end() : m.start();
                if (d < bd) { best = en.getKey(); bd = d; }
            }
        }
        return best == null ? null : new Cue(best, bd);
    }

    private Map<String, Double> numFeats(String n, List<Cand> cands, int k) {
        Cand c = cands.get(k);
        int s = c.s(), e = c.e();
        String txt = c.txt();
        Map<String, Double> f = new HashMap<>();
        f.put("bias", 1.0);
        String intPart = txt.replace(",", "").split("\\.", -1)[0];
        f.put("digits=" + Math.min(intPart.length(), 7), 1.0);
        flag(f, "has_dec", txt.contains("."));
        flag(f, "has_comma", txt.contains(","));
        flag(f, "dec2", DEC2.matcher(txt).find());
        flag(f, "len4_int", txt.length() == 4 && txt.chars().allMatch(ch -> ch >= '0' && ch <= '9'));
        flag(f, "lead0", txt.startsWith("0") && txt.length() > 1);
        f.put("rank=" + Math.min(k, 5), 1.0);
        f.put("rev_rank=" + Math.min(cands.size() - 1 - k, 5), 1.0);
        double mx = Double.NEGATIVE_INFINITY, mn = Double.POSITIVE_INFINITY;
        for (Cand x : cands) { mx = Math.max(mx, x.val()); mn = Math.min(mn, x.val()); }
        flag(f, "is_max", c.val() == mx);
        flag(f, "is_min", c.val() == mn);
        f.put("prev_char=" + (s > 0 ? String.valueOf(n.charAt(s - 1)) : "^"), 1.0);
        f.put("next_char=" + (e < n.length() ? String.valueOf(n.charAt(e)) : "$"), 1.0);
        flag(f, "cur_near", currencyNear(n, s, e) != null);
        flag(f, "masked", pat.get("MASKED").matcher(sub(n, s - 22, s)).find());
        Cue lc = nearestCue(sub(n, s - 35, s), true), rc = nearestCue(sub(n, e, e + 12), false);
        if (lc != null) { f.put("Lcue=" + lc.key(), 1.0); f.put("Lcue=" + lc.key() + "|d" + Math.min(lc.dist() / 8, 3), 1.0); }
        if (rc != null) f.put("Rcue=" + rc.key(), 1.0);
        List<String> L = findAll(pat.get("TOK"), sub(n, s - 40, s));
        L = L.subList(Math.max(0, L.size() - 4), L.size());
        List<String> R = findAll(pat.get("TOK"), sub(n, e, e + 30));
        R = R.subList(0, Math.min(3, R.size()));
        for (int i = 0; i < L.size(); i++) f.put("L" + i + "=" + lower(L.get(L.size() - 1 - i)), 1.0);
        for (int i = 0; i < R.size(); i++) f.put("R" + i + "=" + lower(R.get(i)), 1.0);
        if (L.size() >= 2) f.put("L10=" + lower(L.get(L.size() - 2)) + "|" + lower(L.get(L.size() - 1)), 1.0);
        for (String t : L) f.put("Lbag=" + lower(t), 1.0);
        for (String t : R) f.put("Rbag=" + lower(t), 1.0);
        return f;
    }

    private static void flag(Map<String, Double> f, String k, boolean v) { if (v) f.put(k, 1.0); }

    // ------------------------------------------------------------------ merchant tagger
    private record Tok(int s, int e, String w) {}

    private List<Tok> wtokens(String text) {
        List<Tok> out = new ArrayList<>();
        Matcher m = pat.get("WTOK").matcher(text);
        while (m.find()) out.add(new Tok(m.start(), m.end(), m.group()));
        return out;
    }

    private static boolean pyIsUpper(String w) {
        boolean cased = false;
        for (int i = 0; i < w.length(); i++) {
            char ch = w.charAt(i);
            if (Character.isLowerCase(ch) || Character.isTitleCase(ch)) return false;
            if (Character.isUpperCase(ch)) cased = true;
        }
        return cased;
    }
    private static boolean pyIsAlpha(String w) {
        if (w.isEmpty()) return false;
        for (int i = 0; i < w.length(); i++) if (!Character.isLetter(w.charAt(i))) return false;
        return true;
    }
    private static boolean pyIsAlnum1(char ch) {
        int t = Character.getType(ch);
        return Character.isLetterOrDigit(ch) || t == Character.LETTER_NUMBER || t == Character.OTHER_NUMBER;
    }

    private String shape(String w) {
        if (DIGITS.matcher(w).matches()) return "D";
        if (ARABIC.matcher(w).matches()) return "AR";
        if (pyIsUpper(w) && pyIsAlpha(w)) return "UP";
        if (!w.isEmpty() && Character.isUpperCase(w.charAt(0))) return "Title";
        if (pyIsAlpha(w)) return "low";
        return w.length() == 1 ? "P:" + w : "mix";
    }

    private String tclassOf(String w) {
        if (DIGITS.matcher(w).matches()) return "NUM";
        for (Map.Entry<String, Pattern> en : tclass.entrySet()) if (en.getValue().matcher(w).matches()) return en.getKey();
        if (w.length() == 1 && !pyIsAlnum1(w.charAt(0))) return "PUNCT";
        return "WORD";
    }

    private Map<String, Double> tokFeats(List<Tok> toks, int i) {
        Map<String, Double> f = new HashMap<>();
        java.util.function.IntFunction<String> w = j -> j >= 0 && j < toks.size() ? lower(toks.get(j).w()) : (j < 0 ? "<s>" : "</s>");
        java.util.function.IntFunction<String> sh = j -> j >= 0 && j < toks.size() ? shape(toks.get(j).w()) : "PAD";
        java.util.function.IntFunction<String> tc = j -> j >= 0 && j < toks.size() ? tclassOf(toks.get(j).w()) : "PAD";
        f.put("bias", 1.0);
        f.put("w=" + w.apply(i), 1.0); f.put("sh=" + sh.apply(i), 1.0);
        f.put("w-1=" + w.apply(i - 1), 1.0); f.put("w-2=" + w.apply(i - 2), 1.0);
        f.put("w+1=" + w.apply(i + 1), 1.0); f.put("w+2=" + w.apply(i + 2), 1.0);
        f.put("sh-1=" + sh.apply(i - 1), 1.0); f.put("sh+1=" + sh.apply(i + 1), 1.0);
        f.put("w-1|w=" + w.apply(i - 1) + "|" + w.apply(i), 1.0);
        f.put("sh-1|sh|sh+1=" + sh.apply(i - 1) + "|" + sh.apply(i) + "|" + sh.apply(i + 1), 1.0);
        f.put("pos=" + (Math.min(i, 12) / 3), 1.0);
        for (int k = 1; k < 6; k++) {
            if (i - k >= 0 && anchors.contains(lower(toks.get(i - k).w()))) {
                f.put("anchor=" + lower(toks.get(i - k).w()), 1.0); f.put("anchor_dist=" + k, 1.0); break;
            }
        }
        for (int d = -2; d <= 2; d++) f.put("c" + d + "=" + tc.apply(i + d), 1.0);
        f.put("c-1|c0|c+1=" + tc.apply(i - 1) + "|" + tc.apply(i) + "|" + tc.apply(i + 1), 1.0);
        f.put("c-2|c-1=" + tc.apply(i - 2) + "|" + tc.apply(i - 1), 1.0);
        f.put("c0|c+1|c+2=" + tc.apply(i) + "|" + tc.apply(i + 1) + "|" + tc.apply(i + 2), 1.0);
        return f;
    }

    // ------------------------------------------------------------------ text classifiers
    private void charWb(String text, Map<String, Integer> counts) {
        String t = lower(text);
        int i = 0, len = t.length();
        while (i < len) {
            while (i < len && pyWs(t.charAt(i))) i++;
            if (i >= len) break;
            int j = i;
            while (j < len && !pyWs(t.charAt(j))) j++;
            String w = " " + t.substring(i, j) + " ";
            i = j;
            int wl = w.length();
            for (int n = 2; n <= 5; n++) {
                int off = 0;
                counts.merge(w.substring(off, Math.min(off + n, wl)), 1, Integer::sum);
                while (off + n < wl) { off++; counts.merge(w.substring(off, off + n), 1, Integer::sum); }
                if (off == 0) break;
            }
        }
    }

    private void wordNgrams(String text, Map<String, Integer> counts) {
        List<String> toks = findAll(pat.get("WORD"), lower(text));
        for (String t : toks) counts.merge(t, 1, Integer::sum);
        for (int i = 0; i + 1 < toks.size(); i++) counts.merge(toks.get(i) + " " + toks.get(i + 1), 1, Integer::sum);
    }

    /** Adds the L2-normalised sublinear TF-IDF block's contribution to type and channel logits. */
    private void addTfidf(Map<String, Integer> counts, Map<String, double[]> vocab, double[] zt, double[] zc) {
        List<double[]> rows = new ArrayList<>(); List<Double> vals = new ArrayList<>();
        double norm = 0;
        for (Map.Entry<String, Integer> en : counts.entrySet()) {
            double[] r = vocab.get(en.getKey());
            if (r == null) continue;
            double v = (1 + Math.log(en.getValue())) * r[0];
            rows.add(r); vals.add(v); norm += v * v;
        }
        if (norm == 0) return;
        norm = Math.sqrt(norm);
        int nt = zt.length, nc = zc.length;
        for (int k = 0; k < rows.size(); k++) {
            double[] r = rows.get(k); double v = vals.get(k) / norm;
            for (int c = 0; c < nt; c++) zt[c] += v * r[1 + c];
            for (int c = 0; c < nc; c++) zc[c] += v * r[1 + nt + c];
        }
    }

    private static double[] softmax(double[] z) {
        double mx = Double.NEGATIVE_INFINITY; for (double v : z) mx = Math.max(mx, v);
        double[] p = new double[z.length]; double s = 0;
        for (int i = 0; i < z.length; i++) { p[i] = Math.exp(z[i] - mx); s += p[i]; }
        for (int i = 0; i < z.length; i++) p[i] /= s;
        return p;
    }
    private static int argmax(double[] v) { int b = 0; for (int i = 1; i < v.length; i++) if (v[i] > v[b]) b = i; return b; }

    private static double[] linearProba(Map<String, Double> feats, Map<String, double[]> weights, double[] bias) {
        double[] z = bias.clone();
        for (Map.Entry<String, Double> en : feats.entrySet()) {
            double[] w = weights.get(en.getKey());
            if (w == null) continue;
            for (int c = 0; c < z.length; c++) z[c] += en.getValue() * w[c];
        }
        return softmax(z);
    }

    // ------------------------------------------------------------------ predict
    public ParsedSms parse(String rawSms) {
        String sms = bmp(rawSms), n = normalize(sms);
        double[] zt = typeB.clone(), zc = chanB.clone();
        Map<String, Integer> counts = new HashMap<>();
        charWb(n, counts); addTfidf(counts, charTerms, zt, zc);
        counts.clear(); wordNgrams(n, counts); addTfidf(counts, wordTerms, zt, zc);
        List<String> lexOn = new ArrayList<>();
        for (Map.Entry<String, Pattern> en : lex.entrySet()) if (en.getValue().matcher(n).find()) lexOn.add("lex=" + en.getKey());
        if (candidates(n).isEmpty()) lexOn.add("no_number");
        for (String lf : lexOn) {
            double[] w = lexTerms.get(lf);
            if (w == null) continue;
            for (int c = 0; c < zt.length; c++) zt[c] += lexW * w[c];
            for (int c = 0; c < zc.length; c++) zc[c] += lexW * w[zt.length + c];
        }
        double[] p = softmax(zt);
        int ti = argmax(p);
        String typ = typeClasses[ti];
        ParsedSms out = new ParsedSms();
        out.confidence = Math.round(p[ti] * 1000) / 1000.0;
        if (typ.equals("none")) return out;

        List<Cand> cands = new ArrayList<>();
        for (Cand c : candidates(n)) if (c.val() > 0) cands.add(c);
        if (cands.isEmpty()) { out.reason = "no amount found"; return out; }
        out.isTransaction = true;
        out.type = typ;
        out.channel = chanClasses[argmax(zc)];

        double[][] P = new double[cands.size()][];
        for (int k = 0; k < cands.size(); k++) P[k] = linearProba(numFeats(n, cands, k), numW, numB);
        Map<String, Integer> ci = new HashMap<>();
        for (int i = 0; i < numClasses.length; i++) ci.put(numClasses[i], i);
        Set<Integer> taken = new HashSet<>();
        Integer ka = pick(P, ci, "amount", 0.0, taken);
        Cand a = cands.get(ka);
        out.amount = a.val();
        out.currency = currencyNear(n, a.s(), a.e());
        Integer kf = pick(P, ci, "fee", thr, taken), kb = pick(P, ci, "balance", thr, taken), kl = pick(P, ci, "last4", thr, taken);
        if (kf != null) out.fee = cands.get(kf).val();
        else if (pat.get("NO_FEE").matcher(n).find()) out.fee = 0.0;
        if (kb != null) out.balanceAfter = cands.get(kb).val();
        if (kl != null) out.accountLast4 = cands.get(kl).txt();

        List<Span<LocalDate>> ds = findDates(n);
        if (!ds.isEmpty()) {
            out.date = ds.get(0).v();
            List<Span<LocalTime>> ts = findTimes(n);
            if (!ts.isEmpty()) out.time = ts.get(0).v();
        }

        List<Tok> toks = wtokens(sms);
        if (!toks.isEmpty()) {
            Map<String, Integer> ti2 = new HashMap<>();
            for (int i = 0; i < tokClasses.length; i++) ti2.put(tokClasses[i], i);
            double[][] PT = new double[toks.size()][];
            for (int j = 0; j < toks.size(); j++) PT[j] = linearProba(tokFeats(toks, j), tokW, tokB);
            int B = ti2.get("B"), I = ti2.get("I");
            int j = 0;
            for (int t = 1; t < toks.size(); t++) if (PT[t][B] > PT[j][B]) j = t;
            if (PT[j][B] >= 0.35) {
                int k = j;
                while (k + 1 < toks.size() && PT[k + 1][I] >= 0.3 && PT[k + 1][I] >= PT[k + 1][B]) k++;
                out.merchant = sms.substring(toks.get(j).s(), toks.get(k).e());
            }
        }
        return out;
    }

    private static Integer pick(double[][] P, Map<String, Integer> ci, String role, double thr, Set<Integer> taken) {
        Integer c = ci.get(role);
        if (c == null) return null;
        Integer[] order = new Integer[P.length];
        for (int i = 0; i < P.length; i++) order[i] = i;
        Arrays.sort(order, (x, y) -> Double.compare(P[y][c], P[x][c]));   // stable, descending
        for (int k : order) {
            if (!taken.contains(k) && P[k][c] >= thr) { taken.add(k); return k; }
        }
        return null;
    }
}
