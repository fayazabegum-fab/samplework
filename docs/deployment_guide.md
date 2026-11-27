# Deployment guide

## Before provisioning

Confirm the environment project ID, Pub/Sub and BigQuery region, GCS state bucket, runtime host, and service-account attachment. Enable the Pub/Sub, BigQuery, and IAM APIs. Configure remote state access and Google Application Default Credentials or an approved short-lived identity.

The environment YAML files contain example resource names and a placeholder project ID. Replace those values before planning. Do not commit credentials, local Terraform state, plan files, or environment-specific `.tfvars`.

## Terraform preflight

From the repository root, run:

```bash
bash scripts/deploy_infrastructure.sh dev
```

This formats and validates the Terraform modules with backend initialization disabled. To create a plan against remote state, set the approved GCS bucket:

```bash
TF_STATE_BUCKET=<approved-state-bucket> RUN_TERRAFORM_PLAN=1 \
  bash scripts/deploy_infrastructure.sh dev
```

The script initializes the GCS backend with an environment-specific prefix and runs `terraform plan`. It never runs `terraform apply`.

## Reviewed Terraform apply

After the project owner approves the plan, run the following from `infrastructure/terraform` with the selected environment configuration:

```bash
terraform init \
  -backend-config="bucket=<approved-state-bucket>" \
  -backend-config="prefix=pubsub-bigquery/dev"
terraform fmt -check -recursive ../..
terraform validate
terraform plan -var="config_file=../../config/dev.yaml" -out=tfplan
terraform show tfplan
```

Review the saved plan and its resource changes. After explicit approval, apply that exact plan:

```bash
terraform apply tfplan
```

The saved plan can contain infrastructure metadata. Keep it out of version control and follow the project's retention rules.

## Create BigQuery tables

After Terraform creates the dataset, apply the DDL for each configured pipeline:

```bash
uv run python -m scripts.apply_ddl \
  --config config/dev.yaml \
  --pipeline sample
```

The script executes a BigQuery query and changes GCP state. Confirm the selected environment before running it.

## Start the worker

Run the worker using the service account from Terraform outputs. Bind that identity to the approved compute runtime. The runtime platform is not provisioned by this repository.

```bash
uv run python -m src.main --config config/dev.yaml
```

## Rollback and readiness

For an application issue, stop the worker and revert the reviewed application change. Do not destroy Pub/Sub resources or datasets as an automated rollback. Review a separate Terraform destroy plan and obtain explicit approval before removing resources.

Before requesting deployment approval, verify that:

- The selected environment has real project, region, and state bucket values.
- Terraform fmt, init, validate, and plan completed with the intended environment.
- A reviewer approved the saved plan.
- DDL created the expected raw table.
- The runtime uses the Terraform service account with the scoped grants.
- Unit results and any GCP integration results are recorded accurately.
- The independent code review summary and outstanding risks are attached to the handoff.
- No transformation, deduplication, apply, deployment, or merge occurred without approval.
