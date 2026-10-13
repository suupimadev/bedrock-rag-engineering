# bedrock-rag-engineering

Amazon Bedrock・Docker・Terraformを学びながら、生成AI/RAG（Retrieval-Augmented Generation）システムを構築する学習兼ポートフォリオリポジトリです。

## 目的

- Amazon Bedrockを用いた生成AIアプリケーション開発の実践
- RAGシステムの設計・実装・評価を通じた理解の深化
- Terraformによるインフラのコード化（IaC）とDockerによる再現可能な実行環境の構築
- 学んだ内容を技術記事とコードとしてGitHubで公開し、第三者が再現できる形で共有
- 将来的に Japan AWS Top Engineers（AI/ML Data Engineer）を目指すための実績作り

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
   - Japan AWS Top Engineers応募に向けた実績整理

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

## ライセンス

未定（検討中）
