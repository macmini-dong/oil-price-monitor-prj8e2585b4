#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VPS_HOST="${VPS_HOST:-43.167.189.158}"
VPS_USER="${VPS_USER:-ubuntu}"
SSH_KEY="${SSH_KEY:-/Users/macmini_dong/Desktop/openclaw.pem}"
HOOK_SECRET="${HOOK_SECRET:-}"

if [[ -z "$HOOK_SECRET" ]]; then
  echo "HOOK_SECRET is required" >&2
  exit 1
fi

SSH_OPTS=(-i "$SSH_KEY" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new)

ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "sudo mkdir -p /opt/oil-monitor/deploy && sudo chown -R ${VPS_USER}:${VPS_USER} /opt/oil-monitor"
rsync -az -e "ssh -i $SSH_KEY -o IdentitiesOnly=yes" "$ROOT_DIR/deploy/vps/" "${VPS_USER}@${VPS_HOST}:/opt/oil-monitor/deploy/"

ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "chmod +x /opt/oil-monitor/deploy/deploy.sh /opt/oil-monitor/deploy/oil_webhook.py"
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "cat > /opt/oil-monitor/deploy/hook.env <<EOF
WEBHOOK_SECRET=$HOOK_SECRET
EOF"
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "sudo cp /opt/oil-monitor/deploy/oil-webhook.service /etc/systemd/system/oil-webhook.service"
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "sudo python3 - <<'PY'
from pathlib import Path
path = Path('/etc/nginx/sites-available/a-share-dashboard.conf')
text = path.read_text()
block = '''    location /oil-webhook {
        proxy_pass http://127.0.0.1:9002/oil-webhook;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

'''
if 'location /oil-webhook' not in text:
    text = text.replace('    location / {\\n', block + '    location / {\\n', 1)
    path.write_text(text)
PY"
ssh "${SSH_OPTS[@]}" "${VPS_USER}@${VPS_HOST}" "sudo nginx -t && sudo systemctl daemon-reload && sudo systemctl enable --now oil-webhook.service && sudo systemctl restart oil-webhook.service && sudo systemctl reload nginx"

echo "WEBHOOK_SETUP_OK http://${VPS_HOST}/oil-webhook"
