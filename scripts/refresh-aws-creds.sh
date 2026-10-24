#!/usr/bin/env bash
# .env の短期STS認証情報(AWS_ACCESS_KEY_ID等)を再発行して更新するスクリプト。
# 他の設定(BEDROCK_MODEL_ID等)は変更しない。
set -euo pipefail

PROFILE="${1:-personal}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"

if [ ! -f "$ENV_FILE" ]; then
  echo "エラー: $ENV_FILE が見つかりません。先に .env.example をコピーしてください。" >&2
  exit 1
fi

echo "==> プロファイル '$PROFILE' の認証情報を取得します..."

# まずは再ログインなしで試す(SSOセッションがまだ有効ならこれだけで済む)
if ! CREDS_OUTPUT=$(aws configure export-credentials --profile "$PROFILE" --format env-no-export 2>/tmp/refresh-aws-creds.err); then
  echo "==> SSOセッションが切れているようです。再ログインします..."
  aws sso login --profile "$PROFILE"
  CREDS_OUTPUT=$(aws configure export-credentials --profile "$PROFILE" --format env-no-export)
fi

# .env から既存のAWS認証情報行だけを除去し、新しい値を追記する
TMP_FILE="$(mktemp)"
grep -v -E '^AWS_(ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN|CREDENTIAL_EXPIRATION)=' "$ENV_FILE" > "$TMP_FILE"
mv "$TMP_FILE" "$ENV_FILE"
echo "$CREDS_OUTPUT" >> "$ENV_FILE"

echo "==> .env を更新しました。"
echo "==> docker compose up -d で反映してください。"
