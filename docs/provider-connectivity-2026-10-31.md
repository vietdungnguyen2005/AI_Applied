# Provider connectivity snapshot - 2026-10-31

Historical connectivity and pricing snapshot, not product-quality evaluation. See the [current project](../README.md) for the P03 service.

Kiểm tra kết nối VyceAI và OpenRouter bằng các khóa lưu trong `.env`.

## Chạy lại

Yêu cầu Python 3.9+ với dữ liệu timezone (nếu thiếu, cài `tzdata`). Sao chép `.env.example` thành `.env`, điền khóa rồi chạy:

```powershell
python scripts/check_api.py
```

Script lấy danh sách model và gọi ngắn hai model VyceAI được chủ tài khoản xác nhận miễn phí, cùng `openrouter/free`. Script không sử dụng GitHub PAT, không tự gọi model trả phí và không in khóa. Mỗi lần chạy tiêu thụ quota miễn phí. Kết quả được ghi vào `reports/api-check.json`; chạy lại rồi commit nếu muốn cập nhật snapshot.

## Kết quả kiểm tra ngày 31/10/2026

- VyceAI: `/v1/models` HTTP 200; 8 model được liệt kê.
- VyceAI `glm-5.3-flash`: HTTP 200, trả `OK`.
- VyceAI `beam-1.0`: HTTP 200, trả `OK`.
- OpenRouter: `/api/v1/models` và `/api/v1/key` HTTP 200.
- OpenRouter `openrouter/free`: HTTP 200, trả `OK`, model được chọn là `nvidia/nemotron-3-ultra-550b-a55b:free`, `usage.cost = 0`.
- Lần thử riêng `gpt-6-luna` trước đó: HTTP 429 `rate_limit_exceeded`; chưa xác nhận được chat thành công cho model này. Không thử chat các model trả phí khác.

HTTP 200 của danh sách model không chứng minh mọi model đều gọi được. Chỉ các model có kết quả chat ở trên đã được thử. HTTP 429 cho biết bị giới hạn tại thời điểm thử, chưa đủ để kết luận khóa sai hoặc hết tiền.

## Giá và quyền truy cập VyceAI

Giá USD/1 triệu token đầu vào và đầu ra. Nguồn giá văn bản: bảng dashboard do chủ tài khoản cung cấp trong chat ngày 31/10/2026. Chủ tài khoản cho biết số dư $40; script chưa xác minh số dư hoặc mức trừ tiền thực tế của VyceAI. API danh sách model không trả giá token cho model văn bản.

| Model ID | Đầu vào | Đầu ra | Ghi chú |
| --- | ---: | ---: | --- |
| `glm-5.3-flash` | $0 | $0 | Chủ tài khoản xác nhận free; chat thành công |
| `beam-1.0` | $0 | $0 | Chủ tài khoản xác nhận free; chat thành công |
| `claude-sonnet-4-6` | $3 | $15 | Trừ số dư theo giá dashboard |
| `gpt-6-luna` | $2 | $2 | Dashboard hiển thị quota ngày còn 50M; lần thử gặp 429 |
| `deepseek-v4.1` | $0.15 | $0.60 | Dashboard ghi miễn phí cho Lite/Pro; cần xác nhận gói tài khoản để áp dụng |
| `agnes-3.0-flash` | $0.05 | $0.15 | Dashboard ghi miễn phí cho Lite/Pro; cần xác nhận gói tài khoản để áp dụng |
| `deepseek-v4-flash-lr` | Chưa rõ | Chưa rõ | API có liệt kê; chưa có giá được xác nhận |
| `grok-imagine-2` | — | — | API công bố $0.50/ảnh; chưa thử tạo ảnh |

Tín dụng tặng hoặc số dư $40 không đồng nghĩa các model tính phí có giá $0. Miễn phí theo gói Lite/Pro là quyền lợi có điều kiện.

## Model miễn phí trên OpenRouter

Snapshot API trả 16 model có hậu tố `:free`, đều có `pricing.prompt = 0` và `pricing.completion = 0`:

- `recursive/flint-v1.0:free`
- `xingchen-agi/xing4.0-29b-a4b:free`
- `nvidia/nemotron-3.5-super-vl:free`
- `dots-studio/dots-3-note-preview:free`
- `liquid/lfm-2.5-2.6b:free`
- `nvidia/nemotron-3.5-lightning:free`
- `thinkingmachines/inkling-small:free`
- `poolside/laguna-s-2.1:free`
- `thinkingmachines/inkling:free`
- `poolside/laguna-xs-2.1:free`
- `cohere/north-mini-code:free`
- `nvidia/nemotron-3.5-content-safety:free`
- `nvidia/nemotron-3-ultra-550b-a55b:free`
- `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free`
- `google/gemma-4-26b-a4b-it:free`
- `google/gemma-4-31b-it:free`

Ngoài ra có `openrouter/free`, tự chọn một model miễn phí phù hợp. Đây là model dùng trong lần kiểm tra thành công. Danh sách công bố không đảm bảo từng model luôn có capacity; chưa thử riêng toàn bộ model.

`google/lyria-3-pro-preview` và `google/lyria-3-clip-preview` cũng có giá token đầu vào/đầu ra bằng 0 trong API, nhưng là model âm nhạc, không có hậu tố `:free`. Chưa đủ bằng chứng để kết luận tổng chi phí tạo âm nhạc bằng 0; không đưa vào danh sách chat miễn phí.

Khóa hiện báo `is_free_tier = true`. Lúc kiểm tra ban đầu còn 50/50 lượt; snapshot lưu sau lần chat đầu tiên nên quota trước lần chat cuối còn 49/50. Hai lần chat OpenRouter đều trả HTTP 200; lần đầu chỉ sinh reasoning vì giới hạn 64 token, lần sau trả `OK` với giới hạn 512 token. Mỗi lần thử có thể tính quota.

Theo tài liệu OpenRouter: các biến thể `:free` có giới hạn 20 yêu cầu/phút, 50 yêu cầu/ngày khi tổng tiền mua credits dưới $10; nâng lên 1.000 yêu cầu/ngày khi đủ điều kiện mua credits. Model miễn phí vẫn có thể trả 429 do tải của nhà cung cấp. Không thêm model trả phí vào fallback nếu cần giữ chi phí bằng 0.

Nguồn chính thức:

- https://openrouter.ai/api/v1/models
- https://openrouter.ai/pricing
- https://openrouter.ai/docs/api-reference/limits
- https://openrouter.ai/collections/free-models
- https://vyceai.com/v1/models
- https://vyceai.com/

## Bảo mật

`.env` bị loại khỏi Git. `.env.example` chỉ chứa tên biến và giá trị rỗng. Báo cáo chỉ lưu metadata model, trạng thái HTTP, câu trả lời kiểm tra và usage; không lưu khóa hoặc toàn bộ thông tin tài khoản.
