#!/usr/bin/env bash
# Release to an EXISTING private lab host; do not use this Compose stack as production hosting.
set -euo pipefail
umask 077
sha=$1
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || exit 1
base=/opt/max1102
[[ -f "$base/.env" && -f "$base/DEPLOYMENT_READY" ]] || { echo 'Host bootstrap is missing'; exit 1; }
exec 9>"$base/deploy.lock"
flock -n 9 || { echo 'Another deployment is active'; exit 1; }
previous=$(readlink -f "$base/current")
[[ "$previous" == "$base/releases/"* && -f "$previous/docker-compose.yaml" ]] || { echo 'A working baseline release is required'; exit 1; }
# An operator confirms a maintenance window for THIS commit, with no external job triggers.
[[ -f "$base/APPROVED_COMMIT" && "$(cat "$base/APPROVED_COMMIT")" == "$sha" ]] || { echo 'A maintenance window for this commit is required'; exit 1; }
export AIRFLOW_PROJ_DIR="$base/shared/airflow" ENV_FILE_PATH="$base/.env"
export AIRFLOW_IMAGE_NAME="max1102-airflow:$(basename "$previous")"
old=(docker compose -p max1102 --env-file "$base/.env" -f "$previous/docker-compose.yaml")
"${old[@]}" exec -T airflow-scheduler airflow dags list -o json > "$base/dags.json"
python3 - "$base/dags.json" <<'PY'
import json,sys
rows=json.load(open(sys.argv[1]))
match=[r for r in rows if r.get('dag_id') == 'max1102_monthly_claims_report']
if len(match) != 1 or str(match[0].get('is_paused')).lower() != 'true':
    raise SystemExit('Pause the monthly DAG before deployment')
PY
for state in queued running; do
  "${old[@]}" exec -T airflow-scheduler airflow dags list-runs max1102_monthly_claims_report --state "$state" -o json > "$base/runs.json"
  python3 -c 'import json,sys; sys.exit(bool(json.load(open(sys.argv[1]))))' "$base/runs.json" || { echo 'Pipeline is not idle'; exit 1; }
done
release="$base/releases/$sha"
[[ ! -e "$release" ]] || { echo 'Release directory already exists; inspect it before retrying'; exit 1; }
mkdir -p "$release"
tar -xzf "/tmp/max1102-$sha.tar.gz" -C "$release"
docker build -t "max1102-airflow:$sha" "$release/airflow"
# The source gate intentionally excludes Airflow/database upgrades from this deploy path.
cmp -s "$previous/airflow/Dockerfile" "$release/airflow/Dockerfile" || { echo 'Image dependency changes need a migration review'; exit 1; }
printf '%s\n' "$previous" > "$base/previous-release"
rm "$base/APPROVED_COMMIT"
rollback() {
  trap - ERR
  echo 'Release failed; attempting restoration of the previous image and source'
  ln -sfn "$previous" "$base/current"
  ln -sfn "$previous/airflow/dags" "$base/shared/airflow/dags"
  export AIRFLOW_IMAGE_NAME="max1102-airflow:$(basename "$previous")"
  "${old[@]}" up -d --force-recreate --wait --wait-timeout 300 || echo 'Restoration failed; operator intervention is required'
  exit 1
}
trap rollback ERR
ln -sfn "$release" "$base/current"
ln -sfn "$release/airflow/dags" "$base/shared/airflow/dags"
export AIRFLOW_IMAGE_NAME="max1102-airflow:$sha"
compose=(docker compose -p max1102 --env-file "$base/.env" -f "$release/docker-compose.yaml")
"${compose[@]}" up -d --force-recreate --wait --wait-timeout 300
curl --fail --silent --show-error --max-time 20 http://127.0.0.1:8080/api/v2/monitor/health > "$base/health.json"
python3 - "$base/health.json" <<'PY'
import json,sys
health=json.load(open(sys.argv[1]))
for name in ['metadatabase','scheduler','dag_processor','triggerer']:
    if health.get(name,{}).get('status') != 'healthy':
        raise SystemExit('Airflow unhealthy: ' + name)
PY
"${compose[@]}" exec -T airflow-scheduler airflow dags list-import-errors -o json > "$base/import-errors.json"
python3 -c 'import json,sys; sys.exit(bool(json.load(open(sys.argv[1]))))' "$base/import-errors.json"
printf '%s\n' "$sha" > "$base/deployed-sha"
trap - ERR
echo 'Release healthy. DAG remains paused for operator review and a controlled test run.'
