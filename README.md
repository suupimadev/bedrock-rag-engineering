# bedrock-rag-engineering

Amazon Bedrock・Docker・Terraformを学びながら、生成AI/RAG（Retrieval-Augmented Generation）システムを構築する学習兼ポートフォリオリポジトリです。

## 目的

- Amazon Bedrockを用いた生成AIアプリケーション開発の実践
- RAGシステムの設計・実装・評価を通じた理解の深化
- Terraformによるインフラのコード化（IaC）とDockerによる再現可能な実行環境の構築
- 学んだ内容を技術記事とコードとしてGitHubで公開し、第三者が再現できる形で共有

## 使用予定技術

- **AI/ML**: Amazon Bedrock（Claude, Titan等）, Knowledge Bases for Amazon Bedrock
- **インフラ**: Terraform, AWS（S3, Lambda, OpenSearch Serverless等）
- **コンテナ**: Docker, Docker Compose
- **言語**: Python
- **CI/CD**: GitHub Actions
- **評価**: RAG評価フレームワーク（検索精度・生成品質の評価指標）

## 学習ロードマップ

1. **環境構築フェーズ**
   - ローカル開発環境・GitHubリポジトリの整備（本ステップ）
   - Docker環境の構築
2. **Bedrock基礎フェーズ**
   - Bedrockモデル呼び出し（Converse API等）の実装
   - プロンプト設計の基礎
3. **RAG構築フェーズ**
   - ドキュメントの取り込み・チャンク分割・embedding作成
   - ベクトル検索の実装（Knowledge Bases for Amazon Bedrock等）
   - 検索結果を用いた回答生成パイプライン構築
4. **IaC化フェーズ**
   - Terraformによるインフラ定義（S3, IAM, OpenSearch Serverless等）
   - 環境の再現性確保
5. **評価・改善フェーズ**
   - RAGの評価指標設計・実装（evaluation/配下）
   - 評価結果の記録・比較（results/配下）
6. **発信フェーズ**
   - 技術記事の執筆・公開（docs/配下に下書きを管理）

## ディレクトリ構造

```
bedrock-rag-engineering/
├── app/                   # アプリケーション本体（API、UI等）
├── docker/                # Dockerfile、docker-compose等
├── terraform/             # AWSインフラのTerraformコード
├── rag/                   # RAGパイプライン（取り込み・検索・生成ロジック）
├── evaluation/            # RAG評価用スクリプト・指標
├── datasets/              # 学習・評価用データセット
├── docs/                  # 技術記事の下書き・設計ドキュメント
├── results/               # 評価結果・実験ログ
├── tests/                 # テストコード
├── .github/workflows/     # GitHub Actions CI/CD定義
├── README.md
├── .gitignore
└── .env.example
```

## セットアップ

```bash
cp .env.example .env
# .env に実際の値を設定（このファイルはgit管理対象外）
```

## Docker + FastAPI アプリの起動

開発用APIサーバーをDocker上で起動します（`127.0.0.1`のみに公開、ホストからは外部アクセス不可）。

### ビルド

```bash
docker compose build
```

Dockerfile(`docker/Dockerfile`)の手順に従い、依存関係とアプリコードを含むイメージを作成します。

### 起動

```bash
docker compose up
```

バックグラウンドで起動する場合は `docker compose up -d` を使用します。起動後、以下で動作確認できます。

```bash
curl http://127.0.0.1:8000/health
# => {"status":"ok"}

curl http://127.0.0.1:8000/
# => {"name":"bedrock-rag-engineering","version":"0.1.0"}
```

### 停止

```bash
docker compose down
```

コンテナを停止・削除します（ビルド済みイメージは残ります）。

### テスト

コンテナを使わず、ローカルのPython仮想環境でテストを実行する場合:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

## Amazon Bedrock連携 (POST /chat)

`/chat`エンドポイントは、受け取ったメッセージをAmazon Bedrock Converse APIに渡し、AIの回答を返します。

### 事前準備

1. AWS CLIでSSOログイン: `aws sso login --profile <プロファイル名>`
2. 短期的なSTS認証情報を発行し、`.env`に貼り付ける

   ```bash
   aws configure export-credentials --profile <プロファイル名> --format env-no-export
   ```

   出力された`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN`の3行を`.env`に貼り付けます。これらは数時間で失効するため、`UnauthorizedSSOTokenError`等が出たら`aws sso login`からやり直してください。

3. `.env`に以下も設定
   - `AWS_REGION`: Bedrockを利用するリージョン（例: `ap-northeast-1`）
   - `BEDROCK_MODEL_ID`: 呼び出すモデルID、または推論プロファイルID（例: `jp.anthropic.claude-haiku-5-5`）
   - `BEDROCK_MAX_TOKENS`: 1回の応答で生成する最大トークン数（コスト上限の目安にもなる）

認証情報は、発行のたびに期限が切れる**短期的なSTS認証情報を環境変数として**コンテナに渡します。ホストの`~/.aws`ディレクトリ自体はコンテナにマウントせず、長期アクセスキーも使いません。

> **設計変更の経緯**: 当初は`~/.aws`を読み取り専用でマウントする方式を試しましたが、SSOトークンの自動更新時にboto3がキャッシュファイルへの書き込みを試み、読み取り専用の制約と衝突してエラーになることが判明したため、この方式に変更しました。

### 呼び出し例

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは"}'
# => {"reply": "...", "model_id": "jp.anthropic.claude-haiku-5-5", "input_tokens": ..., "output_tokens": ...}
```

### 利用可能なモデルの確認

```bash
aws bedrock list-foundation-models --profile <プロファイル名> --region ap-northeast-1
aws bedrock list-inference-profiles --profile <プロファイル名> --region ap-northeast-1
```

モデルIDはコードに固定せず、必ず上記コマンドで現在利用可能なものを確認し、`.env`の`BEDROCK_MODEL_ID`で指定してください。

### IAM権限について

`/chat`の実行には最低限 `bedrock:InvokeModel`（Converse APIを含む）権限が必要です。学習用のSSOプロファイルにAdministratorAccess等の広い権限が付与されている場合でも、本番相当の利用では以下のように**呼び出すモデル/推論プロファイルのARNに絞った最小権限ポリシー**を使うことを推奨します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:ap-northeast-1:<account-id>:inference-profile/jp.anthropic.claude-haiku-5-5"
    }
  ]
}
```

## フロントエンド (Vue + Nuxt + TypeScript)

`frontend/`に、ブラウザからBedrockとチャットできる画面があります（Nuxt 4のSPAモード + Ant Design Vueで構築）。

### 起動

```bash
docker compose up -d
```

`api`と`frontend`の両方が起動します。ブラウザで `http://127.0.0.1:5173` を開いてください。

- フロントエンドはNuxtの開発サーバーをコンテナ内で実行しています（`npm run dev`）
- 画面からのAPIリクエストは `/api/chat` → Nitroのdevプロキシ機能 → コンテナ間通信（`http://api:8000/chat`）という経路でFastAPIに届きます
- ブラウザがBedrockやAWS認証情報に直接触れることはありません（`frontend`コンテナにAWS関連の環境変数は一切渡していません）

### コード変更時の注意

volumeによるホットリロードは設定していないため、`frontend/app`配下を変更した場合は再ビルドが必要です。

```bash
docker compose up -d --build frontend
```

### 会話履歴の扱いについて（重要な制約）

画面には過去のやり取りが**表示**されますが、これは画面上の見た目だけです。`POST /chat`は単発質問のみに対応しているため、**Bedrockへは常に最新の1メッセージのみを送信し、過去の会話履歴は送信しません**。複数ターンにまたがる文脈を踏まえた回答は、現時点ではできません。

### フロントエンドの開発・テスト

```bash
cd frontend
npm install
npm run typecheck  # TypeScriptの型チェック (nuxt typecheck)
npm run build       # 本番ビルド
npm test            # vitestによるAPI連携のモックテスト
```

### 既知の課題

`npm audit`で、Nuxtの開発用HTTPSリスナー機能（`listhen`）が依存する`node-forge`に高深刻度の脆弱性が報告されています。修正にはNuxtの破壊的バージョンアップが必要なため、現時点では未対応です。本アプリはローカル限定・HTTP通信のみのため実害は低いと判断していますが、将来的にNuxtのメジャーバージョンアップ時に解消される見込みです。

## ライセンス

未定（検討中）
