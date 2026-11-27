# Plan: Raw Pub/Sub-to-BigQuery Migration

**Slug:** `pubsub-bigquery-migration` • **Created:** 2026-11-26
**Source revision:** `151a55bba9545ade491dd505e2d81f6378088e73`

## Objective

Build a review-ready Python accelerator that reads configured Pub/Sub subscriptions and writes unchanged message payloads and transport metadata to configured BigQuery raw tables. Provision topics, subscriptions, datasets, and least-privilege access through reusable Terraform modules; create tables through version-controlled SQL DDL.

## Context

- **Observed repository state:** `README.md:1` contains only the `samplework` heading. The root also contains `AGENTS.md`, `axis.json`, `.agents/`, `.axis/`, and `.github/`. No application source, dependency manifest, YAML configuration, Terraform, SQL, scripts, tests, or project documentation are present. `.venv/` and tool caches are local environment artifacts.
- **Existing-file mapping:** Keep `README.md` at the root and expand it into the project guide. Keep `AGENTS.md`, `axis.json`, `.agents/`, `.axis/`, `.github/`, and `.gitignore` at the root as repository or agent tooling. Do not move local virtual environments or caches. No existing application files need relocation.
- **Evidence gap:** No HCA project files are present, so its conventions cannot be verified. Use the structure supplied in the request, adapted to the repository root.
- **Analysis status:** Repository analysis is complete for the available project files. The plan records missing implementation artifacts and separates verified repository facts from decisions that still need owner input.
- **User-provided constraints:** Handle raw Pub/Sub payloads only. Do not add business transformations or deduplication. Terraform owns topics, subscriptions, datasets, and required IAM. SQL owns BigQuery table creation. Do not apply Terraform, deploy, or merge before explicit approval.
- **Dependencies:** Actual project IDs, topic and subscription names, dataset and table names, runtime environment, workload profile, and test-project access were not supplied. Configuration examples must use clearly marked placeholders until these are decided.

**Unresolved technical decisions requiring review before implementation:**

1. **Runtime and Python version:** Choose where the long-running consumer will run and which supported Python version to pin. Recommendation: keep the worker runnable as a process and select its production host after its operational constraints are known. The plan does not provision a compute platform.
2. **BigQuery write API:** Choose between the simpler streaming insert API and the Storage Write API. Recommendation: use streaming inserts for an initial low-volume accelerator, then revisit when expected throughput, latency, and cost are known.
3. **Raw table contract:** Confirm the proposed envelope: original payload as `BYTES`, Pub/Sub message ID, publish timestamp, attributes, and ingestion timestamp. Confirm whether tables need partitioning or expiration. No source-message schema was found.
4. **Failure and redelivery policy:** Confirm retry limits and whether a dead-letter topic is required. The baseline acknowledges a message only after BigQuery accepts its row and requests redelivery on write failure. This is at-least-once delivery; a failed acknowledgement can produce duplicate rows. Deduplication remains out of scope.
5. **GCP environment and Terraform state:** Supply project IDs, region and BigQuery location for DEV, TEST, and PROD, plus the remote state bucket/backend and state ownership. Keep state and real identifiers out of source until approved.
6. **Runtime identity:** Confirm the target platform and how it attaches a per-environment service account. Recommendation: Terraform creates a dedicated service account with Pub/Sub subscriber access scoped to each subscription and BigQuery write access scoped to each dataset; deployment binds that identity to the chosen runtime.
7. **DDL execution:** Confirm whether operators should run DDL through a repository script or the `bq` CLI. Recommendation: provide a small script that reads the selected YAML pipeline and executes the checked-in DDL with validated identifiers.
8. **Integration test access:** Identify a non-production GCP project and credentials for the end-to-end test. Without them, the plan can add gated integration tests but cannot claim a real Pub/Sub-to-BigQuery test passed.

## Approach

**Chosen:** Add one root-level deployable using the Python Google Cloud clients and YAML configuration. Each environment file is the shared source for project, region, pipeline subscription, topic, dataset, table, and DDL reference. The application uses the high-level Pub/Sub StreamingPull client, writes the payload bytes and configured metadata to BigQuery, then acknowledges only successful writes. Terraform reads the same configuration to compose reusable Pub/Sub and dataset modules and creates narrowly scoped IAM grants. A SQL DDL template and a small runner create configured tables; Terraform does not create tables.

The target layout keeps the deployable visible at the repository root and avoids an extra `pubsub-bigquery-accelerator/` wrapper. This matches the repository structure guidance and the user-provided folder organization. Python, PyYAML, the Google Cloud Pub/Sub and BigQuery clients, pytest, and a lockfile-based package workflow form the initial toolchain. The runtime version and BigQuery write API remain review decisions.

**Alternative considered:** Use a managed Pub/Sub-to-BigQuery Dataflow template. It reduces custom consumer code, but the repository currently has no application to extend, and the requested modular Python consumer, configuration loader, and writer would be left unimplemented. Reconsider it if the required throughput or operational scale makes a custom worker unsuitable.

**Reasoning:** The repository contains no existing ingestion implementation or stack to preserve. The proposed Python layout comes from the request. Keeping payload bytes opaque avoids inventing a source schema, while a shared configuration avoids duplicating resource names between application and Terraform.

**Left unbuilt:** Transformations, enrichment, deduplication, replay tooling, automatic deployment, and dead-letter resources. Add any of these only after their behavior and operational requirements are approved. Retry and dead-letter policy remains an open decision; the initial plan does not provision extra messaging resources.

Target structure:

```text
README.md
config/
  dev.yaml
  test.yaml
  prod.yaml
src/
  main.py
  pubsub/pubsub_consumer.py
  bigquery/bigquery_writer.py
  utils/config_loader.py
infrastructure/
  terraform/
    providers.tf
    versions.tf
    variables.tf
    main.tf
    outputs.tf
    terraform.tfvars.example
  modules/
    pubsub/
    bigquery/
sql/
  tables/raw_message.sql
tests/
  unit/
  integration/
scripts/
  validate_config.sh
  deploy_infrastructure.sh
  apply_ddl.py
docs/
  architecture.md
  setup_guide.md
  deployment_guide.md
pyproject.toml
uv.lock
.python-version
```

## Steps

1. `[new file: pyproject.toml]`, `[new file: uv.lock]`, `[new file: .python-version]` **Initialize:** Declare the Python package, runtime pin, production and test dependencies, and reproducible tooling; verify dependency installation, linting, and test commands.
2. `[new file: config/dev.yaml]`, `[new file: config/test.yaml]`, `[new file: config/prod.yaml]` **Configure:** Define one validated configuration shape for environment, project, region, pipeline resource names, and DDL reference; add configuration tests for missing fields, invalid identifiers, and multiple pipelines.
3. `[new file: src/utils/config_loader.py]` **Configure:** Load and validate the selected YAML at startup, fail clearly on invalid or placeholder values, and return typed configuration; test valid profiles and invalid configuration.
4. `[new file: src/pubsub/pubsub_consumer.py]`, `[new file: src/bigquery/bigquery_writer.py]` **Implement ingestion:** Add the pull callback and raw BigQuery writer behind small client boundaries; test byte preservation, metadata mapping, success acknowledgement, and write-failure redelivery.
5. `[new file: src/main.py]` **Implement ingestion:** Wire configuration, Pub/Sub, and BigQuery clients at the process entry point without environment-name branches; test that configured subscriptions and tables are selected.
6. `[new file: infrastructure/terraform/providers.tf]`, `[new file: infrastructure/terraform/versions.tf]`, `[new file: infrastructure/terraform/variables.tf]`, `[new file: infrastructure/terraform/main.tf]`, `[new file: infrastructure/terraform/outputs.tf]`, `[new file: infrastructure/terraform/terraform.tfvars.example]` **Implement infrastructure:** Read the selected environment YAML, compose the modules, provision the application identity and scoped IAM, and expose resource names and IDs; verify formatting, initialization, validation, and plans where credentials and state access permit.
7. `[new file: infrastructure/modules/pubsub/main.tf]`, `[new file: infrastructure/modules/pubsub/variables.tf]`, `[new file: infrastructure/modules/pubsub/outputs.tf]` **Implement infrastructure:** Add reusable topic and subscription resources with explicit dependency wiring and configurable names; validate module inputs and outputs with Terraform.
8. `[new file: infrastructure/modules/bigquery/main.tf]`, `[new file: infrastructure/modules/bigquery/variables.tf]`, `[new file: infrastructure/modules/bigquery/outputs.tf]` **Implement infrastructure:** Add a reusable dataset module with configurable project and location; validate it with Terraform. Keep table resources out of Terraform.
9. `[new file: sql/tables/raw_message.sql]`, `[new file: scripts/apply_ddl.py]` **Implement DDL:** Define the raw envelope table and execute its DDL for the configured project, dataset, and table; validate identifier handling and the declared BigQuery schema without applying DDL to production.
10. `[new file: scripts/validate_config.sh]`, `[new file: scripts/deploy_infrastructure.sh]` **Validate locally:** Add repeatable configuration validation and Terraform preflight/plan commands. Keep `apply` as a separately documented, human-approved command; tests must confirm the preflight script does not invoke it.
11. `[new file: tests/unit/test_config_loader.py]`, `[new file: tests/unit/test_ingestion.py]`, `[new file: tests/integration/test_pubsub_bigquery.py]` **Test:** Add unit coverage for configuration, byte-preserving row construction, acknowledgements, failures, and resource selection, plus opt-in integration coverage against an approved non-production GCP project; report cloud tests as unverified when credentials or access are unavailable.
12. `[README.md:1]`, `[new file: docs/architecture.md]` **Document:** Record purpose, strict raw-only scope, architecture, project layout, configuration, local execution, tests, and the Pub/Sub-to-BigQuery data path; check links and commands against the implementation.
13. `[new file: docs/setup_guide.md]`, `[new file: docs/deployment_guide.md]` **Review and prepare for deployment:** Document prerequisites, Terraform init/fmt/validate/plan/apply, DDL execution, runtime identity, deployment prerequisites, and rollback steps. Complete the independent code review, provide its summary with the handoff, and include a deployment readiness checklist. Mark `apply`, deployment, and merge as approval-gated; record actual validation results and remaining decisions.

## Acceptance criteria

- [ ] Adding a configured pipeline selects its Pub/Sub subscription, BigQuery dataset, table, and DDL reference without changing application logic.
- [ ] The worker writes the original Pub/Sub payload bytes unchanged and stores only agreed transport metadata; it performs no business transformation or deduplication.
- [ ] The worker acknowledges only after a successful BigQuery write and reports failures with enough context to diagnose the affected configured pipeline.
- [ ] Terraform modules provision configured topics, subscriptions, datasets, and least-privilege application access; Terraform does not provision BigQuery tables.
- [ ] Version-controlled DDL creates the raw table schema and can be run for the selected environment.
- [ ] Unit tests cover configuration selection, byte preservation, success acknowledgement, and failed-write redelivery. GCP integration results are reported only when actually run.
- [ ] Documentation includes the project structure, prerequisites, configuration, local run and test steps, Terraform commands, DDL execution, and deployment prerequisites.
- [ ] The handoff lists files created, moved, or updated; records actual check results; identifies unresolved decisions; and includes a deployment readiness checklist.
- [ ] No Terraform apply, deployment, merge, transformation, or deduplication occurs without separate scope approval.
- [ ] All existing tests still pass.

## Risks & rollback

- **Risk:** A write can succeed while the acknowledgement fails, causing redelivery and duplicate rows. **Mitigation:** State at-least-once delivery in the table and operational documentation; keep deduplication out of scope unless separately approved.
- **Risk:** Invalid or incomplete environment values can create resources in the wrong project. **Mitigation:** Validate configuration at startup and before Terraform planning; require explicit project and environment values.
- **Risk:** Terraform state backend and GCP access are not specified. **Mitigation:** Treat init/plan as blocked until approved environment values and backend are supplied; never store state in Git.
- **Risk:** The chosen write API may not meet the eventual throughput or cost target. **Mitigation:** Record expected message rate, payload size, latency, and budget before finalizing the writer.
- **Rollback:** Revert the application and configuration changes as a reviewed source change. Keep Terraform resource deletion out of rollback automation; any resource destroy requires a separate reviewed plan and explicit approval.

## Out of scope

- Payload parsing, normalization, enrichment, business rules, and deduplication.
- Terraform-managed BigQuery tables.
- Terraform apply, production deployment, and branch merge.
- Dataflow, replay/backfill tooling, and dead-letter resources unless approved after the open decisions are resolved.

## References

- `AGENTS.md` — repository workflow and local conventions.
- `.axis/playbooks/core-repository.md` — repository layout and ownership guidance.
- `.axis/playbooks/core-coding-standards.md` — module boundaries, configuration validation, and error handling.
- `.axis/playbooks/core-documentation.md` — README and operational documentation guidance.
- `.axis/playbooks/app-backend.md` — startup configuration and service structure.
- `.axis/playbooks/app-streaming.md` — message acknowledgement and failure handling guidance; project scope excludes deduplication and unapproved DLQ resources.
- `.axis/playbooks/app-testing.md` — unit and integration test boundaries.
- `.axis/playbooks/data-pipelines.md` — immutable raw data guidance; its deduplication guidance is excluded by the explicit project scope.
- `.axis/playbooks/cloud-iam.md` — workload identity and least privilege.
- `.axis/playbooks/cloud-iac.md` — Terraform module and state guidance.
- Google Cloud Pub/Sub pull subscriptions: https://cloud.google.com/pubsub/docs/pull
- BigQuery streaming inserts: https://cloud.google.com/bigquery/docs/samples/bigquery-table-insert-rows

---

## Execution log — 2026-11-26 09:56

**Blocked at step 1:** `AGENTS.md` has no `## Test` command, and the executor must not guess one.
**State on exit:** No implementation files changed. The plan records this blocker; the backlog marks execution active.
**Suggested next:** Add the project test command to `AGENTS.md` and resolve the plan's open technical decisions before retrying `/axis-code pubsub-bigquery-migration`.

## Execution log — 2026-11-26 10:02

**Decisions for this implementation:** Pin Python 3.12 and use a long-running process with Google Application Default Credentials; provision no compute runtime. Use BigQuery streaming inserts with no insert IDs. Store the Pub/Sub payload as `BYTES`, along with message ID, publish time, attributes, and ingestion time. Partition by ingestion date and set no expiration. Acknowledge only successful writes and nack failed writes; add no dead-letter resource or deduplication.
**Environment inputs:** Keep project IDs and locations as placeholders until supplied. Use a GCS Terraform backend with the bucket and per-environment prefix supplied to `terraform init`. Gate real GCP integration tests on an explicitly selected non-production project and ADC.
**State on entry:** The project test command is `uv run pytest`. Terraform is not installed in the current environment.

---

## Execution log — 2026-11-26 10:11

**Blocked at step 1:** `uv run ruff check .` reports 11 lint violations. The required `uv run pytest` passed all 12 tests.
**State on exit:** Implementation and documentation changes remain unstaged. Terraform is unavailable, and format, shell, infrastructure validation, and independent review remain unverified. No Terraform apply, deployment, or merge occurred.
**Suggested next:** Resolve the Ruff findings, rerun validation, then complete Terraform checks and independent review before staging.

---

## Execution log — 2026-11-26 10:13

**Blocked during diff review:** `git diff --check` failed with `.axis/plans/pubsub-bigquery-migration.md:3: trailing whitespace.`
**Checks completed:** `uv run pytest` passed all 12 tests. `uv run ruff check .` passed. `uv run ruff format --check .` reported 43 files already formatted. `bash -n scripts/validate_config.sh scripts/deploy_infrastructure.sh` passed. Terraform checks were skipped because Terraform is not installed.
**State on exit:** Ruff auto-fix reported 18 fixes, although the preceding lint output listed 11 findings; the subsequent lint check passed. Python and documentation changes remain in the worktree. The Git diff review stopped at the whitespace failure. No Terraform apply, deployment, or merge occurred.
**Suggested next:** Remove the reported trailing whitespace, rerun `git diff --check`, then finish reviewing the full diff and Terraform checks when available.

---

## Final review — 2026-11-26 10:17

**Diff review:** Reviewed all 42 modified or new paths. No files outside the migration deliverables were found. `git diff --check` passes after removing the trailing whitespace on line 3.
**README accuracy:** The documented commands and raw-only scope match the application, Terraform, DDL, and test entry points. All environment profiles parse as YAML and use explicit project ID placeholders.
**Security finding:** No credential or private-key material matched the repository scan. `infrastructure/terraform/main.tf:61` grants dataset-level `roles/bigquery.dataEditor`, which is broader than write-only ingestion access. Review a narrower custom role or table-level grant before production.
**Validation limits:** Terraform format and validation remain skipped because Terraform is unavailable. The GCP integration test remains unrun because no non-production project or credentials were supplied.
**Remaining decisions:** Select the production runtime and identity attachment, provide environment project IDs, BigQuery locations and the remote-state bucket, supply non-production integration resources and credentials, confirm expected throughput and cost, and review retry limits for poison messages. Independent review and the BigQuery IAM scope also remain open.
**State on exit:** No Terraform apply, deployment, merge, or commit occurred.
