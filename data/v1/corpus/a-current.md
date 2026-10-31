# SYNTHETIC a-current source version 2

## encoding

Supplier A の原本は CP932 です。改行やバイト列を変えず、指定された文字コードを使用します。

## mapping

商品コードは sku、商品名は name、在庫数は on_hand に対応します。許可される対象はこの三つだけです。数量は整数 0 から 1000000 までです。

## approval

提案は承認ではありません。人が既存の OPERATOR ワークフローで確認します。プレビュー receipt の有効期間は 600 秒です。

## pending

HTTP 202 は受付・ステージングです。完了は inspection の現在の状態で確認します。タイムアウト後に自動再送しません。

## freshness

ファイル名や三つの列から数量の業務上の鮮度を証明することはできません。原本の意味と時点を人が確認します。

## escalation

現在の模擬手順では、不明な列の意味は supplier contact に確認してからマッピングを保存します。

