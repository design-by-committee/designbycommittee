#!/bin/bash
# Run a Django management command on the Render web service over SSH, e.g.:
#
#   ops/remote-manage.sh show_page /comedy/
#   ops/remote-manage.sh edit_page /comedy/ - --draft < changes.json
#
# Standard input is passed through, so `edit_page ... -` can read changes from a local file.
# Needs an SSH key added to your Render account (Account Settings → SSH Public Keys).
# The host key is pinned in ops/render_known_hosts (Render's published Frankfurt fingerprint:
# SHA256:dBRrCEA0tBkvaYLzzDw/mzaANw6nUJO961Zx806spZs).
set -euo pipefail

RENDER_SSH="${RENDER_SSH:-srv-dc24rhs9v7es73c9atj0@ssh.frankfurt.render.com}"
HERE="$(cd "$(dirname "$0")" && pwd)"

if [ $# -eq 0 ]; then
  echo "Usage: $0 <management command> [arguments...]" >&2
  exit 2
fi

# Quote each argument for the remote shell
remote_args=""
for arg in "$@"; do
  remote_args="$remote_args $(printf '%q' "$arg")"
done

exec ssh -o BatchMode=yes -o ConnectTimeout=20 \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile="$HERE/render_known_hosts" \
  "$RENDER_SSH" "cd /opt/render/project/src && python manage.py$remote_args 2>&1"
# (2>&1 on the remote side: Render's SSH doesn't pass the remote stderr back, which would hide error messages.)
