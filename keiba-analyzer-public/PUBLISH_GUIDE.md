# GitHub公開手順

このフォルダは、元のPrivateリポジトリとは別の**新規Publicリポジトリ**として公開してください。

## 1. ローカル確認

```bash
python scripts/check_public_safety.py
python -m unittest discover -s tests -v
python examples/run_demo.py
```

## 2. Gitの公開情報を確認

コミットには作成者名とメールアドレスが記録されます。初回コミット前に、公開してよい表示名とメール設定へ変更してください。

```bash
git init
git config --local user.name "<公開用の表示名>"
git config --local user.email "<公開用のメールアドレス>"
git config --local --list
```

個人メールを公開したくない場合は、GitHubのアカウント設定で案内される非公開用メールアドレスを使用してください。

## 3. 初回コミット

```bash
git add .
git status
git diff --cached --stat
git diff --cached
git commit -m "Add public portfolio edition"
git branch -M main
```

`git status` にDB、CSV、HTML、`.env`、ログ、ブラウザプロファイルが表示された場合は、コミットせずに除外してください。

## 4. GitHubで新規Publicリポジトリを作成

推奨リポジトリ名：

```text
keiba-analyzer-public
```

GitHub側ではREADME等を自動生成せず、空のリポジトリとして作成すると競合を避けられます。

## 5. リモートへ送信

GitHubが表示する新規リポジトリのURLを使用します。

```bash
git remote add origin <新規PublicリポジトリのURL>
git push -u origin main
```

## 6. 公開後の最終確認

ログアウト状態またはプライベートブラウズでPublicリポジトリを開き、次を確認します。

- READMEが最初に表示される
- 実名、個人メール、学校情報、ローカルパスがない
- DB、CSV、HTML、Cookie、トークンがない
- `python scripts/check_public_safety.py` が成功する
- `python -m unittest discover -s tests -v` が成功する

問題がなければ、リポジトリのトップURLを応募フォームへ入力します。
