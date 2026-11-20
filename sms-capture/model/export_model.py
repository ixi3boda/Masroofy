#!/usr/bin/env python3
"""Export a trained SmsTxnModel (joblib) to sms-model.tsv.gz for the Java parser.
The file holds weights AND every regex / word list, so Java and Python share one source of truth.
Usage: python3 export_model.py sms_txn_model.joblib sms-model.tsv.gz"""
import gzip, sys
import sms_model as M

def esc(s): return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
def f(x): return "%.9g" % float(x)

m = M.SmsTxnModel.load(sys.argv[1])
L = []
def sec(name): L.append("#" + name)
def row(*cols):
    line = "\t".join(esc(str(c)) for c in cols)
    L.append("\\" + line if line.startswith("#") else line)   # a leading '#' marks section headers only

sec("meta")
row("format", "1"); row("lex_w", f(m.lex_w)); row("thr", f(m.thr))
for name, clf in [("type", m.type_clf), ("chan", m.chan_clf), ("num", m.num_clf), ("tok", m.tok_clf)]:
    row(name + "_classes", *clf.classes_); row(name + "_intercept", *[f(x) for x in clf.intercept_])
for name, n in [("char", len(m.v_char.vocabulary_)), ("word", len(m.v_word.vocabulary_)), ("lexw", len(m.v_lex.vocabulary_)),
                ("numw", len(m.v_num.vocabulary_)), ("tokw", len(m.v_tok.vocabulary_))]:
    row("count_" + name, n)          # the Java loader checks these to detect a damaged file
sec("patterns")   # name, flags (I = ignore case), pattern
for name, rx in [("DMY", M.RE_DMY), ("DMON", M.RE_DMON), ("TIME", M.RE_TIME), ("NUM", M.RE_NUM), ("XX", M.RE_XX),
                 ("TOK", M.TOK), ("WTOK", M.WTOK), ("NO_FEE", M.NO_FEE), ("MASKED", M.MASKED_RE)]:
    row(name, "I" if rx.flags & 2 else "-", rx.pattern)
row("WORD", "-", m.v_word.token_pattern)
sec("currency");  [row(t, c) for t, c in M.CURRENCY]
sec("months_en"); [row(k, v) for k, v in M.MON.items()]
sec("months_ar"); [row(k, v) for k, v in M.MON_AR.items()]
sec("lex");       [row(k, v) for k, v in M.LEX.items()]
sec("cues");      [row(k, v) for k, v in M.CUES.items()]
sec("tclass");    [row(k, v) for k, v in M.TCLASS]
sec("anchors");   [row(a) for a in sorted(M.ANCHORS)]

nc, nw = len(m.v_char.vocabulary_), len(m.v_word.vocabulary_)
Wt, Wc = m.type_clf.coef_, m.chan_clf.coef_
for name, vec, off in [("char", m.v_char, 0), ("word", m.v_word, nc)]:
    sec(name)   # term, idf, type weights..., channel weights...
    for term, j in vec.vocabulary_.items():
        row(term, f(vec.idf_[j]), *[f(x) for x in Wt[:, off + j]], *[f(x) for x in Wc[:, off + j]])
sec("lexw")     # lex feature, type weights..., channel weights...
for name, j in m.v_lex.vocabulary_.items():
    row(name, *[f(x) for x in Wt[:, nc + nw + j]], *[f(x) for x in Wc[:, nc + nw + j]])
for name, vec, clf in [("numw", m.v_num, m.num_clf), ("tokw", m.v_tok, m.tok_clf)]:
    sec(name)
    for feat, j in vec.vocabulary_.items():
        row(feat, *[f(x) for x in clf.coef_[:, j]])
with gzip.open(sys.argv[2], "wt", encoding="utf-8") as fh:
    fh.write("\n".join(L) + "\n")
print("exported", sys.argv[2], "char", nc, "word", nw, "num", len(m.v_num.vocabulary_), "tok", len(m.v_tok.vocabulary_))
