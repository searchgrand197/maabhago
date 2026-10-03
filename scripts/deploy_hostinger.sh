#!/usr/bin/env bash
set -euo pipefail

APP_NAME="${APP_NAME:-curevice}"
APP_USER="${APP_USER:-curevice}"
APP_DIR="${APP_DIR:-/srv/curevice}"
REPO_URL="${REPO_URL:-https://healthcare_curevice-admin@bitbucket.org/healthcare_curevice/curevice.git}"
BRANCH="${BRANCH:-feature/nvn}"
DOMAIN="${DOMAIN:-_}"
DJANGO_ENV="${DJANGO_ENV:-production}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
FRONTEND_BUILD="${FRONTEND_BUILD:-1}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root: sudo bash scripts/deploy_hostinger.sh"
  exit 1
fi

echo "==> Installing OS packages"
apt-get update -y
DEBIAN_FRONTEND=noninteractive apt-get install -y \
  git curl nginx python3 python3-venv python3-pip build-essential libpq-dev

if ! id -u "${APP_USER}" >/dev/null 2>&1; then
  echo "==> Creating app user ${APP_USER}"
  useradd --system --create-home --shell /bin/bash "${APP_USER}"
fi

mkdir -p "$(dirname "${APP_DIR}")"
chown -R "${APP_USER}:${APP_USER}" "$(dirname "${APP_DIR}")"

if [[ ! -d "${APP_DIR}/.git" ]]; then
  echo "==> Cloning repository (${BRANCH})"
  sudo -u "${APP_USER}" git clone --branch "${BRANCH}" "${REPO_URL}" "${APP_DIR}"
else
  echo "==> Updating repository (${BRANCH})"
  sudo -u "${APP_USER}" git -C "${APP_DIR}" fetch origin
  sudo -u "${APP_USER}" git -C "${APP_DIR}" checkout "${BRANCH}"
  sudo -u "${APP_USER}" git -C "${APP_DIR}" pull --ff-only origin "${BRANCH}"
fi

echo "==> Python virtualenv + dependencies"
sudo -u "${APP_USER}" "${PYTHON_BIN}" -m venv "${APP_DIR}/.venv"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip wheel
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

if [[ ! -f "${APP_DIR}/.env" ]]; then
  echo "==> Creating .env from .env.example"
  cp "${APP_DIR}/.env.example" "${APP_DIR}/.env"
fi

python3 - <<PY
from pathlib import Path
import secrets
p = Path("${APP_DIR}/.env")
text = p.read_text(encoding="utf-8")
if "DJANGO_ENV=" in text:
    text = text.replace("DJANGO_ENV=development", "DJANGO_ENV=${DJANGO_ENV}")
else:
    text += "\nDJANGO_ENV=${DJANGO_ENV}\n"
if "DEBUG=" in text:
    text = text.replace("DEBUG=1", "DEBUG=0")
    text = text.replace("DEBUG=True", "DEBUG=False")
if "ALLOWED_HOSTS=" in text:
    text = text.replace("ALLOWED_HOSTS=localhost,127.0.0.1", "ALLOWED_HOSTS=${DOMAIN},www.${DOMAIN},127.0.0.1")
if "CSRF_TRUSTED_ORIGINS=" not in text:
    text += f"\nCSRF_TRUSTED_ORIGINS=https://${DOMAIN},https://www.${DOMAIN}\n"
if "SECRET_KEY=change-me" in text:
    text = text.replace("SECRET_KEY=change-me", "SECRET_KEY=" + secrets.token_urlsafe(50))
p.write_text(text, encoding="utf-8")
PY

chown "${APP_USER}:${APP_USER}" "${APP_DIR}/.env"
chmod 600 "${APP_DIR}/.env"

echo "==> Django migrate/collectstatic"
sudo -u "${APP_USER}" bash -lc "cd '${APP_DIR}' && .venv/bin/python manage.py migrate --noinput"
sudo -u "${APP_USER}" bash -lc "cd '${APP_DIR}' && .venv/bin/python manage.py collectstatic --noinput"

if [[ "${FRONTEND_BUILD}" == "1" ]]; then
  if command -v npm >/dev/null 2>&1; then
    echo "==> Building frontend dist (production build only; no npm run dev)"
    sudo -u "${APP_USER}" bash -lc "cd '${APP_DIR}/frontend' && npm ci && npm run build"
  else
    echo "ERROR: npm not found. Install Node.js (LTS) to build frontend dist."
    exit 1
  fi
else
  echo "==> FRONTEND_BUILD=0, skipping frontend build by request."
fi

if [[ ! -f "${APP_DIR}/frontend/dist/index.html" ]]; then
  echo "ERROR: frontend/dist/index.html not found."
  echo "Run: cd ${APP_DIR}/frontend && npm ci && npm run build"
  exit 1
fi

echo "==> Writing Gunicorn systemd service"
cat >/etc/systemd/system/${APP_NAME}.service <<EOF
[Unit]
Description=${APP_NAME} gunicorn
After=network.target

[Service]
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${APP_DIR}/.venv/bin/gunicorn config.wsgi:application \
  --workers 3 \
  --timeout 120 \
  --bind unix:/run/${APP_NAME}.sock
Restart=always
RestartSec=5
RuntimeDirectory=${APP_NAME}
RuntimeDirectoryMode=0755

[Install]
WantedBy=multi-user.target
EOF

echo "==> Writing Nginx site"
cat >/etc/nginx/sites-available/${APP_NAME} <<EOF
server {
    listen 80;
    server_name ${DOMAIN} www.${DOMAIN};

    client_max_body_size 25M;

    location /media/ {
        alias ${APP_DIR}/media/;
    }

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
    }

    # Serve Vite-built frontend assets directly via Nginx (cache-friendly hashed filenames)
    location /assets/ {
        alias ${APP_DIR}/frontend/dist/assets/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_pass http://unix:/run/${APP_NAME}.sock;
    }
}
EOF

ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/${APP_NAME}
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl daemon-reload
systemctl enable ${APP_NAME} nginx
systemctl restart ${APP_NAME}
systemctl restart nginx

echo "\nDeployment complete."
echo "Gunicorn status: systemctl status ${APP_NAME} --no-pager"
echo "Nginx status:    systemctl status nginx --no-pager"
echo "Next step (recommended): sudo certbot --nginx -d ${DOMAIN} -d www.${DOMAIN}"
