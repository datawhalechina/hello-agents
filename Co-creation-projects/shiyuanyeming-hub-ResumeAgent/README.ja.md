# ResumeAgent

[中文](README.md) · **日本語** · [English](README.en.md)

ResumeAgent は、根拠を先に整理する中国語・日本語・英語対応の履歴書メンターです。最初から文章を飾るのではなく、一度に一つだけ質問し、実際に行ったことや本人の貢献を引き出します。内容は本人が確認してから職務経歴書へ反映されます。

![ResumeAgent の2カラムワークベンチ](docs/assets/resume-agent-workbench.png)

## 使い方の流れ

1. 実際の経歴を一つ選ぶと、メンターが現在最も不足している証拠の観点を一つだけ質問します。
2. モデルが回答を候補事実として整理します。確認または却下でき、未確認の内容は文書に入りません。
3. 事実ベースは、背景、本人の責任、行動、方法、結果、裏付け・数値の6観点で証拠を保存します。
4. 応募先の JD ごとにバージョンを作り、使う経歴と中国語・日本語・英語のテンプレートを選びます。
5. 同じ画面でプレビューと編集を行い、HTML、Markdown、DOCX、PDF に出力します。

質問が続く場合は、直接質問から想起の手掛かり、代替となる証拠へ段階的に切り替わります。「今は思い出せない」を明示的に2回選ぶと、その不足項目をスキップします。質問する観点、確認規則、バージョン分離、レンダリングは決定的なコードで制御し、LLM は候補事実の抽出と質問文の作成だけを担います。

## 現在利用できる機能

- 白を基調とした2カラムの FastAPI ワークベンチ：面談、事実ベース、JD カスタマイズ、ツール、文書プレビュー。
- 複数の候補者プロフィール、経歴、応募バージョンを管理。再読み込み後も現在のセッション、選択、サーバー側の編集稿を復元。
- 6観点の証拠進捗と一問ずつの面談。候補事実の確認・却下、推定・機密フラグに対応。
- 確認済み事実だけをレンダリングし、事実ベース更新後は古いバージョンに更新警告を表示。
- 中国語・日本語・英語ごとの見出し、レイアウト、各3種類のスタイル。事実本文は自動翻訳しません。
- ビジュアルまたは Markdown で編集してサーバーに保存。自動生成版へいつでも戻せます。
- HTML、Markdown、DOCX、PDF 出力と、西暦・和暦の変換ツール。
- 一問制約、事実の観点、証拠保持、ハルシネーション防止などを確認する、バージョン管理された合成評価データ。

## アーキテクチャ

```text
Browser (vanilla ES modules)
            │ same-origin JSON API
FastAPI ─── application services ─── deterministic planner / renderer
            │                              │
          SQLite                      HelloAgents adapters
     facts, sessions, versions       fact audit + question wording
```

標準 UI にフロントエンドのビルド工程はありません。SQLite がローカルの事実、セッション、バージョン、編集稿を永続化し、レンダラーは対象バージョンで選ばれた経歴の確認済み事実だけを読み取ります。

主なディレクトリ：

```text
resume_agent/api/             FastAPI エントリと API
resume_agent/application/     面談・事実ベース・バージョンのユースケース
resume_agent/domain/          ドメインモデルと6観点の品質ゲート
resume_agent/agents/          HelloAgents アダプターとプロンプト
resume_agent/rendering/       3言語テンプレートと出力処理
resume_agent/web/             素の HTML/CSS/JavaScript ワークベンチ
tests/                        Python とブラウザクライアントのテスト
evaluation/                   合成メンター評価データとレポート出力先
```

## クイックスタート

Python 3.10 以上が必要です。PDF 出力に限り、Google Chrome または Microsoft Edge をローカルにインストールしてください。

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[agents,web]'
cp .env.example .env
uvicorn resume_agent.api.main:app --reload
```

<http://127.0.0.1:8000/> を開きます。OpenAPI ドキュメントは <http://127.0.0.1:8000/docs> です。

`.env.example` の値はプレースホルダーです。メンター面談を有効にするには、OpenAI 互換モデルの実際の設定へ置き換えてください。プレースホルダーのまま、または設定を省略した場合はオフラインモードになります。

| 変数 | 用途 | 既定値 |
| --- | --- | --- |
| `LLM_MODEL_ID` | モデル ID | 必須（メンターモード） |
| `LLM_API_KEY` | API キー。`DEEPSEEK_API_KEY` も利用可能 | 必須（メンターモード） |
| `LLM_BASE_URL` | OpenAI 互換の HTTP(S) URL | 必須（メンターモード） |
| `LLM_TIMEOUT` | リクエストのタイムアウト（秒） | `60` |
| `LLM_TEMPERATURE` | 事実抽出の temperature | `0.2` |
| `LLM_MAX_TOKENS` | 1リクエストの最大 token 数 | `2048` |
| `RESUME_AGENT_DB` | SQLite ファイルのパス | `data/resume_agent.db` |

モデル設定はサーバー側だけで読み込まれます。起動時にモデルへ自動リクエストは行いません。`GET /capabilities` でメンターと出力機能の状態を確認できますが、API キーやプロバイダーの完全な URL は返しません。

## テスト

```bash
pip install -e '.[dev]'
.venv/bin/python -m pytest -q
node --test tests/web/*.test.mjs
```

モデル設定後は、合成メンター評価も実行できます。

```bash
resume-agent-eval --repeats 3 --fail-under 0.90
```

## プライバシーとローカルデータ

- データは既定でローカルの SQLite に保存され、API キーはサーバー環境変数にだけ置かれます。
- ブラウザストレージに残すのはファイル、経歴、バージョン、言語、タブなどの選択 ID のみです。回答、事実、編集稿、API キーは保存しません。
- 履歴書内容を扱う HelloAgents インスタンスでは、trace、session、skills、todo、devlog、subagent の永続化を既定で無効にしています。
- `.env`、SQLite データベース、仮想環境、ローカルキャッシュはリポジトリから除外されます。コミットや共有の前に、出力ファイルに個人情報が含まれていないか確認してください。

## 現在の制限

- ローカルの単一ユーザー向け MVP です。ホスティング、認証、複数ユーザー権限、クラウド上のデータ分離はありません。インターネットへ直接公開しないでください。
- メンターの質問と候補事実の抽出には利用可能な LLM が必要です。LLM がなくても、ファイル、事実、バージョン、プレビュー、編集、出力はオフラインで利用できます。
- 3言語テンプレートは文書構造と見出しをローカライズしますが、確認済み事実を自動翻訳しません。応募前に対象言語の内容を入力または確認してください。
- 日本語 Web 版が現在生成するのは `職務経歴書` です。個人情報、写真、学歴、資格欄を含む完全な JIS `履歴書` はまだモデル化されていません。
- PDF 出力はローカルの Chrome または Edge に依存します。ブラウザがない場合も HTML、Markdown、DOCX は利用できます。
- 既存履歴書の PDF/DOCX 取り込み、チーム共同作業、本番デプロイ設定はまだありません。

## オープンソースの由来とライセンス

本プロジェクトは [Datawhale HelloAgents](https://github.com/datawhalechina/hello-agents) チュートリアルの共同制作として始まり、現在は単独で動作するポートフォリオプロジェクトとして継続開発しています。

本プロジェクトはチュートリアル上流の [CC BY-NC-SA 4.0](LICENSE) を継承し、原プロジェクトのクレジットを保持します。
