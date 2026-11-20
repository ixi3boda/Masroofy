#!/usr/bin/env bash
# End-to-end check of every auth endpoint against the running stack (real PostgreSQL + real Firebase).
#
# Run from anywhere; it uses Backend/.env and Backend/docker-compose.yml.
# Requirements: the stack is up (docker compose up -d), MAIL_PROVIDER=log in .env (codes are read from the
# backend log), plus curl and jq.  Usage:  ./scripts/smoke-test.sh
# The test user is deleted from Firebase and PostgreSQL at the end.
set -euo pipefail

cd "$(dirname "$0")/.."
# Read only the keys we need; .env is not shell code (values may contain spaces).
env_value() { grep -E "^$1=" .env | tail -1 | cut -d= -f2-; }
BACKEND_PORT=$(env_value BACKEND_PORT); DB_USERNAME=$(env_value DB_USERNAME); DB_NAME=$(env_value DB_NAME)
FIREBASE_WEB_API_KEY=$(env_value FIREBASE_WEB_API_KEY)
if [[ $(env_value MAIL_PROVIDER) != log ]]; then
  echo "This script reads verification codes from the backend log, so it needs MAIL_PROVIDER=log in .env."
  echo "Set it, run 'docker compose up -d', run this script, then switch back to smtp."
  exit 1
fi

BASE="http://localhost:${BACKEND_PORT:-8080}"
API="$BASE/api/v1"
EMAIL="smoke-test-$(date +%s)-$RANDOM@example.com"
PASSWORD="Sunny-Nile9"
NEW_PASSWORD="Fresh-Start7"
# Extra curl options for calls to Google, e.g. CURL_GOOGLE_OPTS="--doh-url https://1.1.1.1/dns-query"
CURL_GOOGLE_OPTS="${CURL_GOOGLE_OPTS:-}"

pass=0
step() { printf '\n\033[1m%s\033[0m\n' "$*"; }
ok() { pass=$((pass + 1)); printf '  \033[32m✔\033[0m %s\n' "$*"; }
fail() { printf '  \033[31m✘ %s\033[0m\n' "$*"; exit 1; }

# call METHOD PATH [JSON] [TOKEN] -> sets $STATUS and $BODY
call() {
  local method=$1 path=$2 data=${3:-} token=${4:-}
  local args=(-sS -o /tmp/masroofy-smoke-body -w '%{http_code}' -X "$method" "$API$path" -H 'Content-Type: application/json')
  [[ -n $data ]] && args+=(-d "$data")
  [[ -n $token ]] && args+=(-H "Authorization: Bearer $token")
  STATUS=$(curl "${args[@]}")
  BODY=$(cat /tmp/masroofy-smoke-body)
}
expect() {
  local want=$1 label=$2
  [[ $STATUS == "$want" ]] || fail "$label: expected HTTP $want, got $STATUS: $BODY"
  ok "$label (HTTP $STATUS)"
}
# Latest code the LoggingEmailService printed for this email.
latest_code() {
  local kind=$1 masked="${EMAIL:0:1}***@${EMAIL#*@}"
  for _ in $(seq 1 20); do
    code=$(docker compose logs --no-log-prefix backend 2>/dev/null \
      | grep -F "$kind code for $masked" | tail -1 | sed -E 's/.*: ([0-9]{6}) .*/\1/')
    [[ $code =~ ^[0-9]{6}$ ]] && { echo "$code"; return; }
    sleep 0.5
  done
  fail "no $kind code found in backend log (is MAIL_PROVIDER=log?)"
}

step "Health and docs"
[[ $(curl -s "$BASE/actuator/health" | jq -r .status) == UP ]] && ok "actuator health is UP" || fail "backend not healthy"
[[ $(curl -s -o /dev/null -w '%{http_code}' "$BASE/swagger-ui/index.html") == 200 ]] && ok "Swagger UI served" || fail "Swagger UI"
[[ $(curl -s "$BASE/v3/api-docs" | jq -r '.paths | length') -ge 10 ]] && ok "OpenAPI lists every endpoint" || fail "api-docs"

step "01-02 Create an account ($EMAIL)"
call POST /auth/register "{\"fullName\":\"Smoke Tester\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"acceptedTerms\":true}"
expect 201 "register"
[[ $(jq -r .user.emailVerified <<<"$BODY") == false ]] && ok "new user is unverified"
call POST /auth/register "{\"fullName\":\"Smoke Tester\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\",\"acceptedTerms\":true}"
expect 409 "duplicate email rejected"
call POST /auth/register "{\"fullName\":\"Smoke Tester\",\"email\":\"x$EMAIL\",\"password\":\"smoketester\",\"acceptedTerms\":true}"
expect 400 "weak password rejected ($(jq -r '[.fieldErrors[].code]|join(",")' <<<"$BODY"))"

step "01-04 Log in before verifying"
call POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
expect 403 "login blocked: $(jq -r .code <<<"$BODY")"
call POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"Wrong-pass1\"}"
expect 401 "wrong password: $(jq -r .code <<<"$BODY")"

step "01-03 Verify signup email"
call POST /auth/email-verification/resend "{\"email\":\"$EMAIL\"}"
expect 429 "resend cooldown enforced"
call POST /auth/email-verification/verify "{\"email\":\"$EMAIL\",\"code\":\"000000\"}"
[[ $STATUS == 400 ]] && ok "wrong code rejected ($(jq -r .code <<<"$BODY"))" || fail "wrong code: $STATUS $BODY"
CODE=$(latest_code Verification)
call POST /auth/email-verification/verify "{\"email\":\"$EMAIL\",\"code\":\"$CODE\"}"
expect 200 "email verified with code from log"

step "01-04 Log in"
call POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
expect 200 "login"
ACCESS=$(jq -r .accessToken <<<"$BODY"); REFRESH=$(jq -r .refreshToken <<<"$BODY")
call GET /users/me "" "$ACCESS"
expect 200 "GET /users/me as $(jq -r .email <<<"$BODY")"
call GET /users/me "" "not-a-token"
expect 401 "invalid token rejected"
call POST /auth/token/refresh "{\"refreshToken\":\"$REFRESH\"}"
expect 200 "refresh token"
ACCESS=$(jq -r .accessToken <<<"$BODY"); REFRESH=$(jq -r .refreshToken <<<"$BODY")

step "01-05 to 01-08 Reset password"
call POST /auth/password/forgot "{\"email\":\"$EMAIL\"}"
expect 202 "reset code requested"
CODE=$(latest_code "Password reset")
call POST /auth/password/verify-code "{\"email\":\"$EMAIL\",\"code\":\"$CODE\"}"
expect 200 "reset code accepted"
RESET=$(jq -r .resetToken <<<"$BODY")
call POST /auth/password/reset "{\"resetToken\":\"$RESET\",\"newPassword\":\"$PASSWORD\",\"confirmPassword\":\"$PASSWORD\"}"
expect 400 "current password refused: $(jq -r .code <<<"$BODY")"
call POST /auth/password/reset "{\"resetToken\":\"$RESET\",\"newPassword\":\"$NEW_PASSWORD\",\"confirmPassword\":\"$NEW_PASSWORD\"}"
expect 200 "password updated"
call POST /auth/token/refresh "{\"refreshToken\":\"$REFRESH\"}"
expect 401 "old sessions revoked"
call POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
expect 401 "old password no longer works"
call POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"$NEW_PASSWORD\"}"
expect 200 "login with new password"
ACCESS=$(jq -r .accessToken <<<"$BODY")

step "Log out"
call POST /auth/logout "" "$ACCESS"
expect 204 "logout"
call GET /users/me "" "$ACCESS"
expect 401 "token revoked after logout"

step "Cleanup"
call POST /auth/login "{\"email\":\"$EMAIL\",\"password\":\"$NEW_PASSWORD\"}"
ID_TOKEN=$(jq -r .accessToken <<<"$BODY")
# shellcheck disable=SC2086
curl -sS $CURL_GOOGLE_OPTS -o /dev/null -X POST "https://identitytoolkit.googleapis.com/v1/accounts:delete" \
  -H "X-Goog-Api-Key: $FIREBASE_WEB_API_KEY" -H 'Content-Type: application/json' -d "{\"idToken\":\"$ID_TOKEN\"}" \
  && ok "Firebase test user deleted"
docker compose exec -T db psql -q -U "$DB_USERNAME" -d "$DB_NAME" -c "DELETE FROM users WHERE email = '$EMAIL';" \
  && ok "database test user deleted"

printf '\n\033[32mAll %d checks passed against real PostgreSQL and Firebase.\033[0m\n' "$pass"
