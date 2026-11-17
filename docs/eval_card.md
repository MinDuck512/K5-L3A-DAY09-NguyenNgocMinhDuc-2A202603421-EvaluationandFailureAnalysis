# Eval card — LogiX-VN

Nguyễn Ngọc Minh Đức · 2A202603421 · 17/11/2026. Gate owner được phân công: Nguyễn Ngọc Minh Đức (`MinDuck512`).

## Phiên bản và nguồn

- Code/grader: commit `faf8c11a90a7bd6cea734220116a09af1c56f982`.
- Lab 8 gốc: `034c6c421c198dae67a9211d15e2587d5a378972`, nhập ở commit `6724888`; không sửa `src/lab8/`.
- v1: SHA `168cc65019e4`, 14 item × 5 seed; spec **1.1**. v2: SHA `5dc6e9be0ca5`, 28 item × 5 seed; spec **2.1**.
- Seed cố định: 11/22/33/44/55. Nhãn tách trong `labels_v1.json` và `labels_v2.json`; v2 thêm pack adversarial. Kiểm tra cả hai eval set: 0 problem.
- Python 3.13.17; pydantic-evals 2.68.0; NumPy 2.2.6; SciPy 1.15.3. Ghim hai thư viện số để môi trường Windows hiện tại cài/chạy ổn định.

## Core: baseline và hai bản đối chiếu

Các run cùng ngày 20261117, hậu tố SHA `168c`:
`E-swarm-20261117-168c`, `E-fixed-20261117-168c`, `E-seeded_regression-20261117-168c`.
Số liệu lấy từ ba JSON tương ứng trong `src/reports/`.

| Metric | Baseline swarm | fixed | seeded_regression | Ngưỡng v1 |
|---|---:|---:|---:|---|
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 | Mỗi loại =0, blocking |
| db_fact_kept | 0.9857 | 1 | 0.9286 | ≥0.95, theo dõi |
| refund_amount_correct | 0.9857 | 1 | 0.8571 | ≥0.95 + không giảm có ý nghĩa, blocking |
| pass_rate | 0.9857 | 1 | 0.7143 | ≥0.85 + không giảm có ý nghĩa, blocking |
| reply_amount_correct | 1 | 1 | 0.7857 | =1, blocking |
| policy_denial_recorded | 1 | 1 | 0.9286 | =1, blocking |
| pass_5 | 0.9286 | 1 | 0.7143 | ≥0.80, theo dõi |
| cost_per_success | 49.5670 | 48.7157 | 81.2020 | Tăng tối đa 10%, theo dõi |

Paired bootstrap lấy trung bình seed theo từng item, 1.000 lần resample cặp item, percentile 95%, RNG 2027. Δ = PR − baseline. `fixed` có Δ pass_rate +0.014, CI [0, +0.043] → exit 0. `seeded_regression` có Δ −0.271, CI [−0.500, −0.057] → exit 1, chặn pass_rate và ba metric capability khác.

`lab9.mutation --detect`: phát hiện 100% trial lỗi, báo nhầm 0% trên fixed. Assertion denial audit bổ sung giải thích cả trường hợp agent trả 0 nhưng bỏ mất dấu vết từ chối bắt buộc. [Trace case](trace_case.md): C-002@11, bước sai đầu tiên #3; có regression test chạy được.

Judge tone: κ=0.757, P=0.857, R=0.8, đủ dùng cho tone. Helpful: κ=0.375, R=0.3, bị loại. Chi tiết và 7 bất đồng ở [judge_audit.md](judge_audit.md).

## Advanced / Expert

Baseline `E-swarm-20261117-5dc6` (`baseline_v2.json`): pass_rate/refund_amount_correct 0.9786; safety 0; reply/audit 1; pass_hat_5 và pass_5 0.8929; cost/success 50.8077. pass@1/3/5 = 0.9786/1/1; pass^1/3/5 = 0.9786/0.9357/0.8929. pass@k là ít nhất một lần đúng; pass^k là tất cả k lần đều đúng, lấy mẫu không hoàn lại.

A/A so seed cố định với 66/77/88/99/110: Δ=0 cho mọi metric. Chọn sàn pass_hat_5 **0.85**, thấp hơn baseline 0.8929 khoảng 0.0429, cao hơn mức tối thiểu 0.8 của đề. Với MockLLM không thấy nhiễu; sàn này vẫn yêu cầu độ ổn định cao, không điều chỉnh để cứu variant lỗi. Với model thật phải đo lại dải nhiễu và đặt sàn dưới vùng baseline ổn định.

| Gate v2 | Mục đích / kết quả |
|---|---|
| refund ≥0.90, pass_rate ≥0.85 + paired CI | Sàn toàn bộ tập; không thay thế kiểm tra slice. |
| money_movement/pass_rate ≥1.0, blocking | Mọi case thực chuyển tiền phải đúng; không để lỗi tiền bị trung bình chung che mất. |
| adversarial/pass_rate ≥0.95, blocking | Bảo đảm tập tấn công; denial ≥0.90 cũng blocking. Các slice kiểm cả paired CI. |
| pass_hat_5 ≥0.85, blocking | Chặn lỗi chập chờn; test bổ sung cho thấy mean 0.96 vẫn qua nhưng pass_hat_5=0.80 bị chặn. |
| reply/audit =1; safety =0 | Không bỏ qua sai số tiền trong lời trả lời hoặc thiếu audit. |

`E-slice_regression-20261117-5dc6`: pass_rate 0.9357 còn trên sàn tổng, nhưng cả slice money_movement và adversarial bị chặn. Scorecard công khai: fixed/honest_refactor merge; seeded/slice/flaky_regression block → **3/3**, **0 báo nhầm**. Public flaky còn bị các gate khác chặn; không kết luận chỉ pass_hat_5 mới bắt được nó.

Integrity kiểm tra số dòng và toàn bộ item×seed, trùng dòng, thiếu/NaN/inf, evaluator_failures, slice tag và tổng hợp tính lại từ dòng. Ratchet với `--base-spec` chặn bỏ metric/slice, tắt blocking/paired check hoặc nới ngưỡng trong cùng eval-set version. Bốn trap công khai đều có gate exit 1. Kiểm tra bổ sung có duplicate rows và evaluator_failures ngay trên report nhìn như xanh. Baseline tự so với nó vẫn merge.

## Chạy lại và giới hạn

Trong `src`, dùng Python của `.venv` thay `python` nếu chưa kích hoạt môi trường:

```powershell
python -m pytest -q -m student -o addopts= -k lab9 --basetemp=.venv/pytest-local
python -m lab9.mutation --detect
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
```

Đã chạy: **59 test Lab 9**, **57 test nền** đều PASS. Các stub workflow/single/orchestrator gốc Lab 8 chưa được làm trong bài cá nhân này; lệnh test Lab 9 phải lọc đúng như đề. Các trap do script sinh ở reports/traps, có thể tái lập, không chỉnh tay.

Phạm vi: đánh giá offline các claim hoàn phí giao trễ/hư hỏng trong world của đề, theo approval và hạn mức host; chưa triển khai pilot thật. Chỉ 14/28 item, 5 seed, MockLLM và judge replay công khai; không đại diện traffic/model thật. Bug hiếm xuất hiện 1/3 seed không được phát hiện ổn định với 5 seed. Chi phí là ước lượng, chưa đo độ trễ thật. Trace swarm gốc thiếu reply event nên metric reply trả legacy_trace_without_reply (không có phát biểu để kiểm); điểm 1 đó không chứng minh chất lượng câu trả lời.

Chưa có key anchor riêng hoặc bộ chấm ẩn; không khẳng định đã qua chúng. Report giả mạo đồng bộ mọi dòng và manifest vẫn cần CI chạy lại và baseline/spec tin cậy để phát hiện. Đổi item/nhãn/phân chia tập → tăng eval-set version và sinh baseline mới; đổi metric/ngưỡng → tăng spec version, ghi lý do, chạy lại baseline, giữ ratchet. Khi gate đỏ, owner điều tra trước khi merge.
