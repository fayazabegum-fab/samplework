#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
environment="${1:-dev}"

case "$environment" in
  dev|test|prod) ;;
  *)
    printf 'Environment must be dev, test, or prod.\n' >&2
    exit 2
    ;;
esac

terraform fmt -check -recursive "$repo_root/infrastructure"

if [[ "${RUN_TERRAFORM_PLAN:-0}" == "1" ]]; then
  : "${TF_STATE_BUCKET:?Set TF_STATE_BUCKET to the approved GCS state bucket}"
  terraform -chdir="$repo_root/infrastructure/terraform" init \
    -backend-config="bucket=${TF_STATE_BUCKET}" \
    -backend-config="prefix=pubsub-bigquery/${environment}" \
    -input=false
  terraform -chdir="$repo_root/infrastructure/terraform" validate
  terraform -chdir="$repo_root/infrastructure/terraform" plan \
    -input=false \
    -var="config_file=../../config/${environment}.yaml"
else
  terraform -chdir="$repo_root/infrastructure/terraform" init -backend=false -input=false
  terraform -chdir="$repo_root/infrastructure/terraform" validate
fi
