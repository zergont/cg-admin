#!/usr/bin/env bash
# ============================================================
# CG Admin Panel — install.sh v0.3.1
# Использование: sudo bash install.sh [--force]
#   --force  принудительная пересборка даже без новых коммитов
# ============================================================
set -euo pipefail

APP_DIR="/opt/cg-admin"
APP_USER="cg"
SERVICE_NAME="cg-admin"
REPO_URL="https://github.com/zergont/cg-admin.git"
FORCE=false

for arg in "$@"; do
    [[ "$arg" == "--force" ]] && FORCE=true
done

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
git config --global --add safe.directory "$APP_DIR" 2>/dev/null || true

IS_UPDATE=false
CODE_CHANGED=true   # для первой установки всегда true
OLD_COMMIT=""
NEW_COMMIT=""
OLD_VERSION="unknown"
NEW_VERSION="unknown"

if [[ -d "$APP_DIR/.git" ]]; then
    IS_UPDATE=true
    cd "$APP_DIR"

    OLD_COMMIT=$(git rev-parse HEAD)
    OLD_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "unknown")

    CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || true)
    [[ -n "$CURRENT_BRANCH" ]] || CURRENT_BRANCH="main"

    info "Получаю обновления из origin/$CURRENT_BRANCH (текущая: $OLD_VERSION)…"
    git fetch --tags origin "$CURRENT_BRANCH"
    git reset --hard "origin/$CURRENT_BRANCH"

    NEW_COMMIT=$(git rev-parse HEAD)
    NEW_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "unknown")

    if [[ "$OLD_COMMIT" == "$NEW_COMMIT" ]] && [[ "$FORCE" == false ]]; then
        CODE_CHANGED=false
        info "Код не изменился ($NEW_VERSION) — сборка и перезапуск пропущены"
        info "Для принудительной пересборки: sudo bash install.sh --force"
    else
        if [[ "$OLD_COMMIT" != "$NEW_COMMIT" ]]; then
            info "Новый коммит: ${OLD_COMMIT:0:7} → ${NEW_COMMIT:0:7}"
        else
            info "Принудительная пересборка (--force)"
        fi
    fi
else
    info "Клонирую репозиторий…"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR"
    NEW_COMMIT=$(git rev-parse HEAD)
    NEW_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo "unknown")
fi

chown -R "$APP_USER":"$APP_USER" "$APP_DIR"

# ── 4. Python venv + pip ────────────────────────────────────
if [[ "$CODE_CHANGED" == true ]]; then
    info "Настраиваю Python venv…"
    cd "$APP_DIR/backend"
    python3.12 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
else
    info "Шаг 4 пропущен: Python зависимости актуальны"
fi

# ── 5. Frontend build ───────────────────────────────────────
if [[ "$CODE_CHANGED" == true ]]; then
    info "Собираю frontend…"
    cd "$APP_DIR/frontend"
    npm install
    npm run build
else
    info "Шаг 5 пропущен: frontend актуален"
fi

# ── 6. config.yaml ──────────────────────────────────────────
DASHBOARD_CONFIG="/opt/cg-dashboard/config.yaml"
if [[ ! -f "$APP_DIR/config.yaml" ]]; then
    info "config.yaml не найден, создаю из example…"
    cp "$APP_DIR/config.yaml.example" "$APP_DIR/config.yaml"

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
    info "config.yaml уже существует"

    # ── Миграция: пароль PostgreSQL — всегда синхронизируем с dashboard ──
    if [[ -f "$DASHBOARD_CONFIG" ]]; then
        PG_PASS=$(grep -oP '(?<=postgres_password:\s")[^"]+' "$DASHBOARD_CONFIG" 2>/dev/null \
               || grep -oP "(?<=postgres_password:\s')[^']+" "$DASHBOARD_CONFIG" 2>/dev/null \
               || grep -oP '(?<=postgres_password:\s)\S+' "$DASHBOARD_CONFIG" 2>/dev/null \
               || echo "")
        CURRENT_PG=$(grep -oP '(?<=postgres_password:\s")[^"]+' "$APP_DIR/config.yaml" 2>/dev/null \
                  || grep -oP '(?<=postgres_password:\s)\S+' "$APP_DIR/config.yaml" 2>/dev/null \
                  || echo "")
        if [[ -n "$PG_PASS" && "$PG_PASS" != "CHANGE_ME"* ]]; then
            if [[ "$PG_PASS" != "$CURRENT_PG" ]]; then
                info "Синхронизирую postgres_password из $DASHBOARD_CONFIG…"
                sed -i "s|postgres_password:.*|postgres_password: \"$PG_PASS\"|" "$APP_DIR/config.yaml"
                info "Пароль PostgreSQL обновлён"
            else
                info "postgres_password актуален — пропускаю"
            fi
        else
            warn "postgres_password не найден в $DASHBOARD_CONFIG — проверьте вручную"
        fi
    else
        warn "UI Dashboard конфиг не найден ($DASHBOARD_CONFIG) — postgres_password не обновлён"
    fi

    # ── Миграция: добавляем секцию diagnostics если её нет ────
    if ! grep -q "^diagnostics:" "$APP_DIR/config.yaml"; then
        info "Добавляю секцию diagnostics в config.yaml…"
        cat >> "$APP_DIR/config.yaml" << 'YAML'

diagnostics:
  db_writer_health_url: "http://127.0.0.1:8765/health"
  mqtt_host: "localhost"
  mqtt_port: 1883
  mqtt_smoke_timeout_sec: 3.0
  latest_state_stale_sec: 300
  decoder_health_url: "http://127.0.0.1:8080/api/stats"
  dashboard_health_url: "http://127.0.0.1:5555/api/health"
YAML
        info "Секция diagnostics добавлена (дефолтные значения)"
        info "При необходимости отредактируйте: $APP_DIR/config.yaml"
    else
        info "Секция diagnostics уже есть — пропускаю"
    fi
fi

# ── 7. SQLite директория ────────────────────────────────────
mkdir -p "$APP_DIR/data"
chown "$APP_USER":"$APP_USER" "$APP_DIR/data"

# ── 8. systemd unit ─────────────────────────────────────────
info "Устанавливаю systemd unit…"
cp "$APP_DIR/deploy/cg-admin.service" /etc/systemd/system/
cp "$APP_DIR/deploy/cg-deploy@.service" /etc/systemd/system/
chmod 0755 "$APP_DIR/deploy/cg-module-update.py"
systemctl daemon-reload

# ── 9. sudoers + journal ────────────────────────────────────
if ! groups "$APP_USER" 2>/dev/null | grep -q systemd-journal; then
    info "Добавляю $APP_USER в группу systemd-journal…"
    usermod -aG systemd-journal "$APP_USER"
fi

info "Настраиваю sudoers…"
cat > /etc/sudoers.d/cg-admin << 'EOF'
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-dashboard.service
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-decoder.service
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-db-writer.service
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart cg-mqtt.service
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart nginx.service
cg ALL=(ALL) NOPASSWD: /usr/bin/systemctl start cg-deploy@*.service
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

if [[ "$CODE_CHANGED" == true ]]; then
    if [[ "$IS_UPDATE" == true ]]; then
        info "Перезапускаю сервис…"
        systemctl restart "$SERVICE_NAME"
    else
        info "Запускаю сервис (первая установка)…"
        systemctl start "$SERVICE_NAME"
    fi
    sleep 2
    systemctl status "$SERVICE_NAME" --no-pager
else
    info "Перезапуск пропущен — код не изменился"
fi

# ── Итог ─────────────────────────────────────────────────────
echo ""
info "============================================================"
if [[ "$IS_UPDATE" == true ]]; then
    if [[ "$CODE_CHANGED" == true ]]; then
        if [[ "$OLD_VERSION" != "$NEW_VERSION" ]]; then
            info "  CG Admin Panel обновлена: $OLD_VERSION → $NEW_VERSION"
        else
            info "  CG Admin Panel пересобрана: $NEW_VERSION"
        fi
    else
        info "  CG Admin Panel актуальна: $NEW_VERSION (обновлений нет)"
    fi
else
    info "  CG Admin Panel установлена: $NEW_VERSION"
fi
info "  URL:    https://192.168.0.130:9443/admin/"
info "  Config: $APP_DIR/config.yaml"
info "  Logs:   journalctl -u $SERVICE_NAME -f"
info ""
info "  Автозапуск: включён (systemctl enable)"
info "  Сервис автоматически поднимется после перезагрузки."
info "============================================================"
