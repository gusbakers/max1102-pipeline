#!/usr/bin/env bash
# The existing host must be dedicated to this lab, have Docker, and hold its own .env.
set -euo pipefail
[[ "${GITHUB_SHA:-}" =~ ^[0-9a-f]{40}$ ]] || { echo 'Missing release SHA'; exit 1; }
[[ "${AIRFLOW_HOST:-}" =~ ^[a-zA-Z0-9][a-zA-Z0-9.-]*$ ]] || { echo 'Invalid host'; exit 1; }
[[ "${AIRFLOW_USER:-}" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'Invalid SSH user'; exit 1; }
[[ -n "${AIRFLOW_SSH_KEY:-}" && -n "${AIRFLOW_KNOWN_HOSTS:-}" ]] || { echo 'SSH credentials and pinned host keys are required'; exit 1; }
sshdir=$(mktemp -d)
trap 'rm -f "$sshdir/key" "$sshdir/known_hosts"; rmdir "$sshdir"' EXIT
chmod 700 "$sshdir"
printf '%s\n' "$AIRFLOW_SSH_KEY" > "$sshdir/key"
printf '%s\n' "$AIRFLOW_KNOWN_HOSTS" > "$sshdir/known_hosts"
chmod 600 "$sshdir/key" "$sshdir/known_hosts"
options=(-i "$sshdir/key" -o BatchMode=yes -o StrictHostKeyChecking=yes -o "UserKnownHostsFile=$sshdir/known_hosts" -o ConnectTimeout=20)
scp "${options[@]}" release/airflow.tar.gz "$AIRFLOW_USER@$AIRFLOW_HOST:/tmp/max1102-$GITHUB_SHA.tar.gz"
ssh "${options[@]}" "$AIRFLOW_USER@$AIRFLOW_HOST" bash -s -- "$GITHUB_SHA" < ops/airflow/apply_release.sh
