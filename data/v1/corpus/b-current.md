# SYNTHETIC b-current source version 2

## encoding

Supplier B supplies UTF-8 original bytes. Preserve the original file, declared encoding and line endings.

## mapping

SKU maps to sku, ProductName to name and AvailableQuantity to on_hand in the seeded synthetic contract. Only these three targets are allowed; quantities are integers from 0 through 1000000.

## approval

A draft is not approval. A human uses the existing authenticated OPERATOR workflow. Preview receipts expire after 600 seconds. 提案は承認ではありません。

## pending

HTTP 202 means accepted/staged, not completed. Inspect the current job state. Do not automatically resend after a lost response.

## freshness

A filename or three-column file cannot prove business freshness. The operator must establish what the quantities mean and when they were observed.

## escalation

The current synthetic procedure is to clarify an unknown header with the supplier contact before saving a mapping.

