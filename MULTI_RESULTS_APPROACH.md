# 複数検索結果の実装アプローチ

## 問題
検索結果取得件数を5に設定しても1件しか表示されない

## 根本原因
- `search_engine.py`の`search_single_keyword`メソッドが複数の結果を取得してもAPIの最初の結果のみを返している
- 現在のアーキテクチャは1つのキーワードあたり1つの`SearchResult`オブジェクトを想定している

## 解決アプローチ

### アプローチ1: Google API のnumパラメータを使用（推奨）
Google Search APIのnumパラメータを使用して一度に複数の結果を取得し、それらを個別の`SearchResult`として処理

### アプローチ2: startパラメータを使用 
Google APIのstartパラメータを使用して、異なるページから結果を取得

### アプローチ3: SearchEngineの修正
`search_single_keyword`メソッドを修正して複数の`SearchResult`のリストを返すように変更

## 実装方針
現在のアーキテクチャとの互換性を保つため、アプローチ1を採用し、`SearchWorker`で複数の結果を個別に処理する
