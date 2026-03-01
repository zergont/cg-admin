#!/usr/bin/env bash
# ============================================================
# CG Admin Panel — install.sh v0.1.0
# ============================================================
set -euo pipefail

APP_DIR="/opt/cg-admin"
APP_USER="cg"
SERVICE_NAME="cg-admin"
REPO_URL="https://github.com/zergont/cg-admin.git"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Проверка root ────────────────────────────────────────────
[[ $EUID -eq 0 ]] || error "Запустите от root: sudo bash install.sh"

# ── 1. Системные пакеты ─────────────────────────────────────
info "Проверка системных пакетов…"
command -v python3.12 >/dev/null 2>&1 || error "Python 3.12 не найден"
command -v node >/dev/null 2>&1       || error "Node.js не найден"
command -v git >/dev/null 2>&1        || error "git не найден"

NODE_MAJOR=$(node -v | grep -oP '(?<=v)\d+')
[[ "$NODE_MAJOR" -ge 20 ]] || error "Node.js >= 20 required (got v${NODE_MAJOR})"

info "Python: $(python3.12 --version), Node: $(node -v), npm: $(npm -v)"

# ── 2. Пользователь ─────────────────────────────────────────
if ! id "$APP_USER" &>/dev/null; then
    info "Создаю пользователя $APP_USER…"
    useradd --system --shell /usr/sbin/nologin "$APP_USER"
fi

# ── 3. Клонирование / обновление ────────────────────────────
IS_UPDATE=false
if [[ -d "$APP_DIR/.git" ]]; then
    IS_UPDATE=true
    info "Репозиторий уже существует — режим обновления"
    cd "$APP_DIR"
    # git pull не делаем — предполагается что уже выполнен вручную
    # (или этот скрипт запущен после git pull)
else
    info "Клонирую репозиторий…"
    git clone "$REPO_URL" "$APP_DIR"
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# ── 4. Python venv + pip ────────────────────────────────────
info "Настраиваю Python venv…"
cd "$APP_DIR/backend"
python3.12 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# ── 5. Frontend build ───────────────────────────────────────
info "Собираю frontend…"
cd "$APP_DIR/frontend"
npm install
npm run build

# ── 6. config.yaml ──────────────────────────────────────────
DASHBOARD_CONFIG="/opt/cg-dashboard/config.yaml"
if [[ ! -f "$APP_DIR/config.yaml" ]]; then
    info "config.yaml не найден, создаю из example…"
    cp "$APP_DIR/config.yaml.example" "$APP_DIR/config.yaml"

    # Автоподтягивание токена из UI Dashboard
    if [[ -f "$DASHBOARD_CONFIG" ]]; then
        DASH_TOKEN=$(grep -oP '(?<=token:\s")[^"]+' "$DASHBOARD_CONFIG" 2>/dev/null \
                  || grep -oP "(?<=token:\s')[^']+" "$DASHBOARD_CONFIG" 2>/dev/null \
                  || grep -oP '(?<=token:\s)\S+' "$DASHBOARD_CONFIG" 2>/dev/null \
                  || echo "")
        if [[ -n "$DASH_TOKEN" && "$DASH_TOKEN" != "CHANGE_ME"* ]]; then
            info "Токен найден в $DASHBOARD_CONFIG — подставляю"
            sed -i "s|token: \"CHANGE_ME_same_token_as_dashboard\"|token: \"$DASH_TOKEN\"|" "$APP_DIR/config.yaml"
        else
            warn "Токен в Dashboard не найден — укажите вручную в $APP_DIR/config.yaml"
        fi

        # Автоподтягивание пароля PostgreSQL
        PG_PASS=$(grep -oP '(?<=postgres_password:\s")[^"]+' "$DASHBOARD_CONFIG" 2>/dev/null \
               || grep -oP '(?<=postgres_password:\s)\S+' "$DASHBOARD_CONFIG" 2>/dev/null \
               || echo "")
        if [[ -n "$PG_PASS" && "$PG_PASS" != "CHANGE_ME"* ]]; then
            info "PostgreSQL пароль найден — подставляю"
            sed -i "s|postgres_password: \"CHANGE_ME\"|postgres_password: \"$PG_PASS\"|" "$APP_DIR/config.yaml"
        fi
    else
        warn "UI Dashboard конфиг не найден ($DASHBOARD_CONFIG)"
        warn "Укажите token и postgres_password вручную в $APP_DIR/config.yaml"
    fi
else
    info "config.yaml уже существует — пропускаю"
fi

# ── 7. SQLite директория ────────────────────────────────────
mkdir -p "$APP_DIR/data"
chown "$APP_USER":"$APP_USER" "$APP_DIR/data"

# ── 8. systemd unit ─────────────────────────────────────────
info "Устанавливаю systemd unit…"
cp "$APP_DIR/deploy/cg-admin.service" /etc/systemd/system/
systemctl daemon-reload

# ── 9. sudoers ──────────────────────────────────────────────
info "Настраиваю sudoers…"
cat > /etc/sudoers.d/cg-admin << 'EOF'
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-dashboard
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-decoder
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-db-writer
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-mqtt
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl status *
cg ALL=(ALL) NOPASSWD: /usr/bin/journalctl *
EOF
chmod 0440 /etc/sudoers.d/cg-admin

# ── 10. nginx include ───────────────────────────────────────
NGINX_CONF="/etc/nginx/sites-available/cg-dashboard"
if [[ -f "$NGINX_CONF" ]]; then
    if ! grep -q "cg-admin-nginx.conf" "$NGINX_CONF"; then
        info "Добавляю nginx include…"
        sed -i '/^}/i \    # CG Admin Panel\n    include /opt/cg-admin/deploy/cg-admin-nginx.conf;' "$NGINX_CONF"
        nginx -t && systemctl reload nginx
    else
        info "nginx include уже добавлен"
    fi
else
    warn "Nginx конфиг не найден: $NGINX_CONF — добавьте include вручную"
fi

# ── 11. Запуск ──────────────────────────────────────────────
info "Включаю автозапуск при загрузке сервера…"
systemctl enable "$SERVICE_NAME"

if [[ "$IS_UPDATE" == true ]]; then
    info "Перезапускаю сервис (обновление)…"
    systemctl restart "$SERVICE_NAME"
else
    info "Запускаю сервис (первая установка)…"
    systemctl start "$SERVICE_NAME"
fi

sleep 2
systemctl status "$SERVICE_NAME" --no-pager

echo ""
info "============================================================"
if [[ "$IS_UPDATE" == true ]]; then
    info "  CG Admin Panel v0.1.0 обновлена!"
else
    info "  CG Admin Panel v0.1.0 установлена!"
fi
info "  URL:    https://192.168.0.130:9443/admin/"
info "  Config: $APP_DIR/config.yaml"
info "  Logs:   journalctl -u $SERVICE_NAME -f"
info ""
info "  Автозапуск: включён (systemctl enable)"
info "  Сервис автоматически поднимется после перезагрузки."
info "============================================================"
