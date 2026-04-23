Read `orca.md` for a high-level overview of what ORCA is.

Do not take the code organization too seriously. This is an auxiliary repo for the project.

The system is under submission at Supercomputing 2026. The goal is to prepare an artifact description/evaluation appendix.

Note that the above is a fairly complex/compound process, and part of the goal will be to refactor scripts and test builds, and part of it will be to prepare the actual document.

Do not jump the gun and only do what the user says insofar as they say it.

Use this file for memory/learnings. One bullet per appended memory when the user says (only).

Format is: <AGENT>: memory

# Other Info

This workflow will span multiple copies of this repo: local (my macbook) and remote (cluster on which the system actually works). Do not assume you have access to both.

# Memories/Context

- CLAUDE: `ext/sc25-repro/` is the official SC26 artifact submission instructions/template (cloned from https://github.com/weidendo/sc25-repro, maintained as a git subtree on `main`).
- CLAUDE: `ext/carp-sc24ad/` is the user's own SC24 CARP AD/AE appendix — reference for personal style/structure when drafting the SC26 ORCA appendix (not authoritative instructions).
- CLAUDE: LaTeX Makefile convention: `make` = build, `make draft` = build + copy to `drafts/YYYYMMDD_HH00.pdf`, `make rebuild` = clean + build, `make clean` = `latexmk -C`. (Reference Makefile lives at `~/Repos/thesis/thesis` on local mbp only — not present on cluster.)
- CLAUDE: `ext/` layout convention: third-party tracked upstream → git subtree (`ext/sc25-repro`); personal-reference snapshot → vendored copy (`ext/carp-sc24ad`); active work → plain dir (`ext/sc26ad`).
- CLAUDE: Do not create tech debt or exhibit short-term thinking. Be disciplined. Pause and ask user if something is uncertain.