# STEP 4: Vue (Nuxt) + TypeScriptチャット画面の実装

> 当初はReact + Vite構成で実装したが、途中でVue (Nuxt) + TypeScript構成に作り直した。本メモはNuxt版の最終構成について記録する。

## 構成図

```
ブラウザ (http://127.0.0.1:5173)
    │  ofetch('/api/chat')
    ▼
frontendコンテナ (Nuxt dev server / SPAモード, 0.0.0.0:5173)
    │  Nitroのdevプロキシ機能で /api/chat, /api/health を個別にマッピング
    │  http://api:8000/chat, /health へ転送（Docker内部ネットワーク）
    ▼
apiコンテナ (FastAPI + Uvicorn, 0.0.0.0:8000)
    │  boto3 (bedrock-runtime).converse()
    ▼
Amazon Bedrock (ap-northeast-1)
```

- ブラウザはfrontendコンテナにしか触れず、apiコンテナのAWS認証情報には一切アクセスしない
- frontendコンテナにはAWS関連の環境変数を渡していない（`compose.yaml`参照）

## 実装した機能

- 質問入力フォーム（`ChatInput.vue`）
  - Enterで送信、Shift+Enterで改行
  - 空文字送信の防止（trimして空なら送信しない）
  - 送信中（`isLoading`）は入力欄・ボタンを`disabled`化し、二重送信を防止
- メッセージ送信と回答表示（`MessageList.vue`、`app.vue`のstate管理）
- 送信中のローディング表示（「AIが応答を生成しています...」）
- APIエラーの表示（`ChatApiError`のメッセージをそのまま表示）
- 入出力トークン数の表示（AIの発言ごとに`input_tokens`/`output_tokens`を表示）
- 会話履歴の画面表示（Vueの`ref`で配列として保持）

## 採用技術と理由

| 技術 | 理由 |
|---|---|
| Vue 3 (Composition API) + Nuxt 4 | ディレクトリ構成だけでコンポーネント/composableの自動インポートが効き、設定が簡潔 |
| Nuxt SPAモード (`ssr: false`) | ローカル専用の学習ツールであり、SSRの複雑さが不要なため |
| ofetch | Nuxtが標準採用するHTTPクライアント。2xx以外で自動的に例外(`FetchError`)を投げるため、手動の`response.ok`判定が不要 |
| Vitest | 既存のバックエンドpytestと同様、fetchをモックしたユニットテストが書きやすい |
| Ant Design Vue 4 + `@ant-design-vue/nuxt` | コンポーネント一式（Card, List, Alert, Button等）をCSSをほぼ自作せずに統一感のある見た目で組める。Nuxtモジュールがコンポーネントの自動インポートまで面倒を見てくれる |
| node:26-slim (Docker) | 2026年10月時点でActive LTS入りしたNode.js 26系を使用。ホストの`node --version`（v26.9.0）とも揃えた |

## 動作確認結果

- `npm run typecheck`（`nuxt typecheck`）: 型エラーなし
- `npm run build`（`nuxt build`）: ビルド成功（`.output/`出力まで確認）
- `npm run test`（vitest）: `sendChatMessage`の正常系・異常系2件、PASS
- `docker compose up -d --build`: `api`・`frontend`ともに起動（`docker compose ps`でUp確認）
- `curl http://127.0.0.1:5173/api/health` → `{"status":"ok"}`（Bedrock不使用、プロキシ疎通の確認）
- `curl -X POST http://127.0.0.1:5173/api/chat`（ユーザー承認の上で実施）→ `amazon.nova-lite-v1:0`から実際の応答・トークン数を取得（200 OK）
- 既存の`pytest`（バックエンド, 5件）: 変更なし、引き続き全件PASS
- ブラウザでの目視確認: ユーザー自身が`http://127.0.0.1:5173`で確認し、「問題なく表示・動作している」ことを確認済み（Ant Design Vue導入後の見た目も「問題なく、このままでよい」と確認済み）

## 発生した問題と対処

1. **React版からNuxt版への作り直し**: 実装後にユーザーからVue/Nuxtへの変更依頼があり、未コミットだった`frontend/`（React版）を削除し、Nuxtで再実装した（git履歴には一切影響なし）
2. **`vue-tsc`とTypeScript 7系の非互換**: `nuxt typecheck`実行時に`ERR_PACKAGE_PATH_NOT_EXPORTED`エラーが発生。`vue-tsc@3.3.13`が、TypeScript 7系で変更されたパッケージの`exports`構造に未対応だったことが原因。`package.json`の`overrides`で`typescript`を`^5.7.3`に固定して解決
3. **Node型定義の不足**: `nuxt.config.ts`で`process.env`を使った際に`Cannot find name 'process'`エラー。`@types/node`を追加して解決
4. **vitestモックの不備**: `fetch`のモックに`mockResolvedValue`で同じ`Response`インスタンスを使い回していたため、2回目のテストで「Body is unusable（ボディ読み取り済み）」エラーが発生。`mockImplementation`で呼び出しごとに新しい`Response`を生成するよう修正
5. **既知の未解決事項**: `npm audit`で`node-forge`経由の高深刻度脆弱性7件を検出（Nuxtの開発用HTTPSリスナー機能`listhen`の依存先）。修正にはNuxtの破壊的バージョンアップが必要なため、本STEPでは見送り。ローカル専用・HTTP限定の学習環境のため実害は低いと判断し、既知の課題として記録するに留める
6. **デザイン改善（Ant Design Vue導入）**: 実装完了後にユーザーから見た目の改善依頼があり、`ant-design-vue`と`@ant-design-vue/nuxt`を追加導入。`ChatInput.vue`/`MessageList.vue`/`app.vue`をAnt Designのコンポーネント（`a-card`, `a-list`, `a-alert`, `a-textarea`等）で書き直した。型チェック・ビルド・テストが引き続き通ることを確認し、ユーザー自身の目視確認でも問題なしだった

## GitHub公開対象

- `frontend/`配下のソースコード一式（`node_modules/`, `.nuxt/`, `.output/`は`frontend/.gitignore`で除外済み）
- `compose.yaml`, `README.md`の更新分
- 本メモ（`docs/article-notes/step4.md`）
- `.env`・AWS認証情報は引き続き非公開（ルートの`.gitignore`で除外済み、本STEPでの変更なし）

## 今後の検証テーマ

- React版とVue(Nuxt)版、同一要件を実装した際の開発体験・コード量・型安全性の比較
- Nuxtのディレクトリベース自動インポート（components/composables）が可読性・保守性に与える影響の検証
- `npm audit`で検出された間接依存の脆弱性を、どこまで許容しどこから対応すべきかの判断基準の整理
- 複数ターンの会話履歴をBedrockに送る場合の設計（トークン数増加とコストのトレードオフ、要約による圧縮など）
- NuxtのSSRモードを有効化した場合の構成変化（Bedrock呼び出しをサーバーサイドのみに限定する設計の検討）
