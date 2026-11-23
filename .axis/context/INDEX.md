# Context index

Every note in `.axis/context/`, with what it covers. Read this table first, then
open the notes your task touches. `/axis-distill` owns this file. It adds a row when it
writes a note and reconciles the table against the directory on every run.

| topic                   | description                                                                          | createdAt  | updatedAt  |
| ----------------------- | ------------------------------------------------------------------------------------ | ---------- | ---------- |
| [glossary](glossary.md) | This project's domain vocabulary: canonical terms, acronyms, internal service names. | 2026-11-23 | 2026-11-23 |

`refs/` holds axis-owned reference documents (writing style, artifact design, the
AGENTS.md fill prompt). `axis sync` refreshes them and the agent that needs one
reads it by name, so they carry no rows here.
