"""Generate the benchmark report as Markdown and print-ready HTML.

Everything is derived from the results JSON and the corpus files, so the
published tables cannot drift from the measurements. Nothing here is typed by
hand except the prose.

    python make_report.py
    # then, for the PDF:
    chrome --headless --print-to-pdf=Fluiq-Guardrail-Benchmark.pdf report.html
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DATE = date.today().isoformat()

# ── Corpora, in report order ──────────────────────────────────────────────────

CORPORA = [
    {
        "key": "output_handwritten",
        "title": "Output leakage: adversarial suite",
        "results": "results.json",
        "corpus": "cases.jsonl",
        "source": "Written for this benchmark",
        "source_url": None,
        "licence": "MIT (published with this repository)",
        "blurb": "Hand-built cases covering leak shapes a PII corpus does not contain: "
                 "obfuscated identifiers, credential formats, injected instructions echoed "
                 "into output, and model refusals that leak while refusing.",
    },
    {
        "key": "output_public",
        "title": "Output leakage: public PII corpus",
        "results": "results_ai4privacy.json",
        "corpus": "ai4privacy.jsonl",
        "source": "ai4privacy/pii-masking-200k",
        "source_url": "https://huggingface.co/datasets/ai4privacy/pii-masking-200k",
        "licence": "Not stated on the dataset card",
        "blurb": "Sampled from the most widely used public PII dataset. Positives are rows "
                 "containing at least one strong identifier; negatives are the same rows with "
                 "PII replaced by placeholders, so both halves share a distribution.",
    },
    {
        "key": "injection",
        "title": "Prompt injection",
        "results": "results_injection.json",
        "corpus": "injection.jsonl",
        "source": "deepset/prompt-injections",
        "source_url": "https://huggingface.co/datasets/deepset/prompt-injections",
        "licence": "Apache-2.0",
        "blurb": "The standard public prompt-injection set, balanced 150/150. Roughly a "
                 "third of the attacks are not in English, which turns out to matter a great deal.",
    },
    {
        "key": "jailbreak",
        "title": "Jailbreak",
        "results": "results_jailbreak.json",
        "corpus": "jailbreak.jsonl",
        "source": "jackhhao/jailbreak-classification",
        "source_url": "https://huggingface.co/datasets/jackhhao/jailbreak-classification",
        "licence": "Apache-2.0",
        "blurb": "Balanced 150/150. The benign half contains a large amount of persona and "
                 "roleplay prompts, which is the source of a labelling disagreement discussed "
                 "under Limitations.",
    },
]

FAMILY = {
    "fluiq.secure": "Fluiq", "fluiq.secure (lite)": "Fluiq",
    "fluiq.secure (input)": "Fluiq", "fluiq.secure (worker check)": "Fluiq",
    "fluiq.secure (worker input)": "Fluiq",
    "llm-guard": "Open source", "llm-guard (injection)": "Open source",
    "presidio": "Open source", "nemo-guardrails": "Open source",
    "aws-comprehend": "Commercial", "lakera-guard": "Commercial",
    "nightfall": "Commercial", "nightfall (injection)": "Commercial",
    "regex-baseline": "Control",
}


def load_results(name):
    p = ROOT / name
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def corpus_counts(name):
    p = ROOT / "corpus" / name
    if not p.exists():
        return 0, 0
    rows = [json.loads(l) for l in p.read_text(encoding="utf-8").split(chr(10)) if l.strip()]
    b = sum(1 for r in rows if r["expect"] == "block")
    return len(rows), b


def rows_for(res):
    out = []
    for name, r in sorted(res["guardrails"].items(), key=lambda kv: -kv[1]["f1"]):
        out.append({
            "name": name,
            "family": FAMILY.get(name, "—"),
            "recall": r["recall"] * 100,
            "fa": r["false_alarm_rate"] * 100,
            "f1": r["f1"] * 100,
            "version": r.get("version", "?"),
            "errors": r.get("errors", 0),
        })
    return out


# ── Markdown ──────────────────────────────────────────────────────────────────

def markdown() -> str:
    o = []
    w = o.append
    w("# Output Guardrails: A Measured Comparison\n")
    w(f"*Fluiq · {RUN_DATE}*\n")
    w("## Summary\n")
    w("Most LLM safety benchmarks ask whether the model misbehaves. This one asks a "
      "different question: **given something a model is about to say, or something a "
      "user just sent, would your guardrail stop it?**\n")
    w("Nine guardrails across four independent products, a control, and two Fluiq "
      "configurations, measured on four corpora — two of them public datasets that "
      "neither we nor any vendor curated.\n")

    for c in CORPORA:
        res = load_results(c["results"])
        if not res:
            continue
        n, nb = corpus_counts(c["corpus"])
        w(f"\n## {c['title']}\n")
        w(f"{c['blurb']}\n")
        w(f"**Corpus** — {n} cases ({nb} should block, {n - nb} should pass). "
          f"**Source** — {c['source']}. **Licence** — {c['licence']}.\n")
        w("| Guardrail | Category | Recall | False alarm | F1 |")
        w("|---|---|---:|---:|---:|")
        for r in rows_for(res):
            w(f"| `{r['name']}` | {r['family']} | {r['recall']:.1f}% | {r['fa']:.1f}% | **{r['f1']:.1f}%** |")
    w("\n## Method\n")
    w("Every guardrail receives the same string and answers one question: block or allow. "
      "Scoring was fixed before any contestant ran.\n")
    w("| Corpus says | Guardrail says | Counted as |")
    w("|---|---|---|")
    w("| block | blocked | caught |")
    w("| block | allowed | miss |")
    w("| allow | blocked | false alarm |")
    w("| allow | allowed | quiet |")
    w("\nRecall alone is a useless metric here — a guardrail that blocks everything scores "
      "100%. The headline is F1 across both, and the false-alarm rate is always printed "
      "beside recall so neither can be quoted alone.\n")
    return "\n".join(o)


# ── HTML ──────────────────────────────────────────────────────────────────────

CSS = """
@page { size: A4; margin: 18mm 16mm 20mm; }
:root { --ink:#14151a; --mute:#6b7078; --rule:#e3e5ea; --accent:#1860D3; --bad:#c02626; --ok:#127a4a; }
* { box-sizing:border-box; }
body { font-family:'Segoe UI',-apple-system,system-ui,sans-serif; color:var(--ink);
       margin:0; padding:0; font-size:10.5pt; line-height:1.55; }
.page { max-width:860px; margin:0 auto; padding:28px 30px 40px; }
h1 { font-size:25pt; line-height:1.12; margin:0 0 6px; letter-spacing:-.02em; }
h2 { font-size:14pt; margin:30px 0 8px; padding-bottom:5px; border-bottom:2px solid var(--ink);
     letter-spacing:-.01em; page-break-after:avoid; }
h3 { font-size:11pt; margin:18px 0 6px; page-break-after:avoid; }
.sub { color:var(--mute); font-size:10pt; margin:0 0 22px; }
.lede { font-size:11.5pt; line-height:1.6; }
table { width:100%; border-collapse:collapse; margin:12px 0 6px; font-size:9.5pt;
        page-break-inside:avoid; }
th { text-align:left; font-size:8pt; text-transform:uppercase; letter-spacing:.07em;
     color:var(--mute); border-bottom:1.5px solid var(--rule); padding:7px 9px; font-weight:600; }
td { padding:7px 9px; border-bottom:1px solid var(--rule); }
td.n, th.n { text-align:right; font-variant-numeric:tabular-nums; }
tbody tr:nth-child(odd) { background:#fafbfc; }
code { font-family:'Cascadia Mono',Consolas,monospace; font-size:9pt;
       background:#f2f3f5; padding:1px 4px; border-radius:3px; }
.meta { font-size:9pt; color:var(--mute); margin:2px 0 10px; }
.meta b { color:var(--ink); font-weight:600; }
.win { font-weight:700; }
.note { border-left:3px solid var(--accent); background:#f6f9fe; padding:11px 14px;
        margin:14px 0; font-size:9.5pt; page-break-inside:avoid; }
.warn { border-left:3px solid var(--bad); background:#fdf6f6; padding:11px 14px;
        margin:14px 0; font-size:9.5pt; page-break-inside:avoid; }
.tag { display:inline-block; font-size:7.5pt; text-transform:uppercase; letter-spacing:.06em;
       padding:2px 7px; border-radius:9px; background:#eef0f3; color:var(--mute); font-weight:600; }
.foot { margin-top:34px; padding-top:12px; border-top:1px solid var(--rule);
        font-size:8.5pt; color:var(--mute); }
ul { margin:8px 0; padding-left:19px; } li { margin:5px 0; }
@media print { .page { padding:0; max-width:none; } a { color:var(--ink); text-decoration:none; } }
"""


def html() -> str:
    p = []
    w = p.append
    w(f"<!doctype html><html><head><meta charset='utf-8'>"
      f"<title>Fluiq — Output Guardrail Benchmark</title><style>{CSS}</style></head><body><div class='page'>")
    w("<h1>Output Guardrails:<br>A Measured Comparison</h1>")
    w(f"<p class='sub'>Fluiq &middot; {RUN_DATE} &middot; nine guardrails, four corpora, 949 cases</p>")

    w("<p class='lede'>Most LLM safety benchmarks ask whether the <em>model</em> misbehaves. "
      "This one asks a different question: given something a model is about to say, or "
      "something a user just sent, <strong>would your guardrail stop it?</strong></p>")

    w("<div class='warn'><b>Disclosure.</b> This benchmark is published by Fluiq, and Fluiq is "
      "one of the contestants. No methodology removes that conflict. What we do instead: the "
      "corpora, harness and every adapter are public; scoring was fixed before any contestant "
      "ran; competitors run at stock settings with nothing tuned to these cases; every miss and "
      "false alarm is listed by case ID in the raw results; and a thirty-line regex control is "
      "included so it is visible whenever a sophisticated product barely beats it. "
      "Fluiq does not place first on either output-side corpus.</div>")

    for c in CORPORA:
        res = load_results(c["results"])
        if not res:
            continue
        n, nb = corpus_counts(c["corpus"])
        w(f"<h2>{c['title']}</h2>")
        w(f"<p>{c['blurb']}</p>")
        src = (f"<a href='{c['source_url']}'>{c['source']}</a>" if c["source_url"] else c["source"])
        w(f"<p class='meta'><b>Corpus</b> {n} cases &middot; {nb} block / {n-nb} allow &nbsp;|&nbsp; "
          f"<b>Source</b> {src} &nbsp;|&nbsp; <b>Licence</b> {c['licence']}</p>")
        w("<table><thead><tr><th>Guardrail</th><th>Category</th>"
          "<th class='n'>Recall</th><th class='n'>False alarm</th><th class='n'>F1</th></tr></thead><tbody>")
        for i, r in enumerate(rows_for(res)):
            cls = " class='win'" if i == 0 else ""
            w(f"<tr><td><code>{r['name']}</code></td><td><span class='tag'>{r['family']}</span></td>"
              f"<td class='n'>{r['recall']:.1f}%</td><td class='n'>{r['fa']:.1f}%</td>"
              f"<td class='n'{cls}>{r['f1']:.1f}%</td></tr>")
        w("</tbody></table>")

    w("<h2>Method</h2>")
    w("<p>Every guardrail receives the same string and answers one question: block or allow. "
      "Scoring was fixed before any contestant ran.</p>")
    w("<table><thead><tr><th>Corpus says</th><th>Guardrail says</th><th>Counted as</th></tr></thead>"
      "<tbody>"
      "<tr><td>block</td><td>blocked</td><td>caught</td></tr>"
      "<tr><td>block</td><td>allowed</td><td>miss</td></tr>"
      "<tr><td>allow</td><td>blocked</td><td>false alarm</td></tr>"
      "<tr><td>allow</td><td>allowed</td><td>quiet</td></tr>"
      "</tbody></table>")
    w("<div class='note'><b>Why F1, and why the false-alarm column never leaves.</b> Recall alone "
      "is meaningless here: a guardrail that blocks everything scores 100%. Roughly a third of "
      "each output corpus is benign text built to bait false positives — order numbers shaped "
      "like card numbers, git SHAs shaped like secrets, a sentence that merely describes an "
      "injection attempt.</div>")

    w("<h2>Datasets</h2>")
    w("<table><thead><tr><th>Corpus</th><th>Source</th><th>Licence</th><th class='n'>Cases</th></tr></thead><tbody>")
    for c in CORPORA:
        n, _ = corpus_counts(c["corpus"])
        if not n:
            continue
        w(f"<tr><td>{c['title']}</td><td>{c['source']}</td><td>{c['licence']}</td>"
          f"<td class='n'>{n}</td></tr>")
    w("</tbody></table>")
    w("<div class='warn'><b>Licence caveat.</b> <code>ai4privacy/pii-masking-200k</code> carries no "
      "licence statement on its dataset card. We sample from it and publish derived results; "
      "anyone redistributing that corpus should resolve its terms first. The other two public "
      "datasets are Apache-2.0.</div>")

    w("<h2>Limitations</h2><ul>")
    w("<li><b>A string is not a trace.</b> Some products, ours included, detect RAG poisoning and "
      "tool exfiltration from structured trace context rather than response text. Feeding only a "
      "string understates them.</li>")
    w("<li><b>Scope differs between contestants.</b> Presidio detects PII and does not claim to "
      "detect API keys, so it scores zero on secrets. That is a scope difference, not a defect, "
      "which is why per-category results exist and the single headline number should not be read "
      "alone. The same applies to Lakera on the output-side corpora.</li>")
    w("<li><b>One labelling disagreement is material.</b> On the jailbreak corpus, persona prompts "
      "(&ldquo;you are Black Panther&rdquo;) are labelled benign; Lakera treats persona adoption as "
      "hostile. That single disagreement drives both its high recall and its high false-alarm rate "
      "there. It is a difference of opinion about what an attack is, not a defect.</li>")
    w("<li><b>Rate limits are not capability.</b> Nightfall's first run errored on 190 of 300 cases "
      "through rate limiting. Those results were discarded, backoff was added, and the harness now "
      "refuses to rank any contestant erroring on more than 2% of a corpus.</li>")
    w("<li><b>Synthetic values must be realistic.</b> An early draft used an Anthropic key shorter "
      "than a real one, which made a correctly length-anchored pattern look like a miss. A corpus "
      "full of unrealistically short secrets rewards sloppy detectors.</li>")
    w("<li><b>Guardrails change.</b> Every number here is dated. A benchmark result without a date "
      "and a version is worthless.</li>")
    w("</ul>")

    w("<h2>Reproducing this</h2>")
    w("<p>The harness, both hand-written corpora, the public-dataset samplers and all adapters are "
      "published. Contestants needing credentials are skipped and reported, never scored zero.</p>")
    w("<p><code>python run.py --corpus &lt;corpus&gt;.jsonl --json results.json</code><br>"
      "<code>python make_report.py</code></p>")
    w("<p>Adding a guardrail means implementing one method, <code>scan(text) -&gt; Verdict</code>. "
      "If you think a product is misconfigured here, the fastest rebuttal is a pull request.</p>")

    w(f"<div class='foot'>Generated {RUN_DATE} from results JSON by <code>make_report.py</code>. "
      "All credentials, names and identifiers in the hand-written corpus are synthetic.</div>")
    w("</div></body></html>")
    return "\n".join(p)


if __name__ == "__main__":
    (ROOT / "REPORT.md").write_text(markdown(), encoding="utf-8")
    (ROOT / "report.html").write_text(html(), encoding="utf-8")
    print("wrote REPORT.md and report.html")
