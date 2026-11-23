#!/usr/bin/env bash
# Dockerコンテナの起動確認・API疎通確認・フロントエンド画面動作確認、
# および「AWS認証情報がフロントエンドに一切渡っていないこと」を自動で確認するスモークテスト。
# 実際のBedrock呼び出しは行わない(課金なし)。
set -euo pipefail

API_URL="http://localhost:8000"
FRONTEND_URL="http://localhost:5173"
FAILURES=0

pass() { echo "PASS: $1"; }
fail() {
  echo "FAIL: $1"
  FAILURES=$((FAILURES + 1))
}

echo "=== Docker Composeでコンテナを起動 ==="
docker compose up -d --build

echo "=== 起動待ち(api) ==="
for _ in $(seq 1 30); do
  if curl -fs "${API_URL}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "=== 起動待ち(frontend) ==="
for _ in $(seq 1 30); do
  if curl -fs "${FRONTEND_URL}/" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "=== APIコンテナの起動確認 ==="
if curl -fs "${API_URL}/health" | grep -q '"status":"ok"'; then
  pass "api /health"
else
  fail "api /health"
fi

echo "=== API疎通確認(/models) ==="
if curl -fs "${API_URL}/models" | grep -q "amazon.nova-lite-v1:0"; then
  pass "api /models"
else
  fail "api /models"
fi

echo "=== フロントエンド画面の起動確認 ==="
if curl -fs "${FRONTEND_URL}/" | grep -q '__nuxt'; then
  pass "frontend root page"
else
  fail "frontend root page"
fi

echo "=== フロントエンド経由のAPI疎通確認(devProxy) ==="
if curl -fs "${FRONTEND_URL}/api/models" | grep -q "amazon.nova-lite-v1:0"; then
  pass "frontend /api/models proxy"
else
  fail "frontend /api/models proxy"
fi

echo "=== セキュリティ確認: AWS認証情報がfrontendコンテナの環境変数に無いこと ==="
if docker compose exec -T frontend env | grep -qi "AWS_ACCESS_KEY_ID\|AWS_SECRET_ACCESS_KEY\|AWS_SESSION_TOKEN"; then
  fail "frontendコンテナにAWS認証情報の環境変数が存在する"
else
  pass "frontendコンテナにAWS認証情報の環境変数が無い"
fi

echo "=== セキュリティ確認: フロントエンドへのレスポンスにAWS認証情報が含まれないこと ==="
if [ -n "${AWS_ACCESS_KEY_ID:-}" ]; then
  if curl -fs "${FRONTEND_URL}/" | grep -qF "${AWS_ACCESS_KEY_ID}"; then
    fail "フロントエンドのレスポンスにAWS_ACCESS_KEY_IDが含まれている"
  else
    pass "フロントエンドのレスポンスにAWS_ACCESS_KEY_IDは含まれない"
  fi
else
  echo "SKIP: AWS_ACCESS_KEY_IDが環境変数に設定されていないためこのチェックは省略"
fi

echo ""
if [ "${FAILURES}" -eq 0 ]; then
  echo "全てのスモークテストに成功しました。"
  exit 0
else
  echo "${FAILURES}件のチェックに失敗しました。"
  exit 1
fi
