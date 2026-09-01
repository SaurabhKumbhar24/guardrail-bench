# Paper

`main.tex` builds to an 8-page preprint: *Ranking Without Resolution: Most LLM
Guardrail Benchmark Comparisons Are Not Statistically Significant.*

```bash
pdflatex main.tex && pdflatex main.tex   # twice, for cross-references
```

Every number in it comes from the repository, and both scripts that produce them
are here rather than in the paper:

```bash
python stats.py    # Wilson intervals, pairwise McNemar (Tables 2, and the prose)
python power.py    # Monte Carlo power estimates (Table 3)
```

If you re-run the benchmark, those numbers change and the paper's tables have to
be updated by hand. They are not generated from the results JSON the way
`REPORT.md` is. That is a deliberate limit: a paper is a point-in-time claim and
regenerating it silently would defeat the purpose.

## Before submitting this anywhere

Three things need a human, in rough order of how much they matter.

**Verify every citation resolves.** The bibliography was written from memory and
not checked against the actual papers. Every entry should exist and be correctly
attributed, but "should" is not good enough for a reference list. Look up all
nine, confirm the year, venue, and author list, and fix anything that drifted.
A wrong citation is the fastest way to lose a reader who knows the field.

**Decide about the single-annotator gap.** Section 7 states plainly that every
label came from one person who works on one of the evaluated systems, and that
there is no inter-annotator agreement figure. That is honest, and it is also the
first thing a reviewer will push on. Options, cheapest first: recruit one second
annotator for the 49-case adversarial suite alone and report Cohen's kappa; use
an LLM as a second annotator and report the agreement with that clearly labelled
as what it is; or leave it as a stated limitation. The first is a few hours of
someone else's time and would materially strengthen the paper.

**Decide on the author line.** It currently reads "Independent" with a personal
email. If you would rather it carry a company affiliation, or a different contact
address, change it before posting rather than after.

## arXiv specifics

Category: `cs.CR` is the right primary, with `cs.LG` or `cs.CL` as cross-list.

**You will need an endorsement.** arXiv requires one for a first-time submitter
to a category, and a personal email address with no prior submissions will not
bypass it. An endorser is someone who has published in `cs.CR` recently. The
practical route is to email two or three authors of adjacent work, link the
repository, and include the significance table, which is a far more substantial
cold email than most endorsement requests. Budget a few weeks for this step
alone, and start it before the paper is finished rather than after.

Upload the `.tex` source, not the PDF. arXiv compiles it itself. This paper has
no figures and no `.bst` dependency (the bibliography is a literal
`thebibliography` environment), so the source is a single self-contained file and
should build on their end without adjustment.

arXiv is a preprint server and confers no peer review. If you want that later,
SaTML and the ACM AISec workshop are the natural venues and both accept work
already posted to arXiv.
