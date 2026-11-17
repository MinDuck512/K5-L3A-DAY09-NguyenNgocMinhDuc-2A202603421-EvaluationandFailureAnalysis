# Tổng hợp đánh giá — Lab 9

Nguyễn Ngọc Minh Đức - 2A202603421 

## Dữ liệu và phiên bản

Đánh giá agent hoàn phí giao trễ/hư hỏng bằng MockLLM, theo policy và hạn mức của host.

- Code/grader: `faf8c11`; Lab 8 gốc `034c6c4`, nhập tại `6724888`, giữ nguyên `src/lab8/`.
- v1: **14 case × 5 seed**, SHA `168cc65019e4`, spec **1.1**; v2: **28 × 5**, SHA `5dc6e9be0ca5`, spec **2.1**.
- Seed: 11/22/33/44/55; nhãn tách trong `labels_v*.json`. Hai tập đều 0 problem khi kiểm tra.
- Python 3.13.17, pydantic-evals 2.68.0, NumPy 2.2.6, SciPy 1.15.3.

## Kết quả Core

Số liệu từ `src/reports/`. Run ID lần lượt: `E-swarm-20261117-168c`, `E-fixed-20261117-168c`, `E-seeded_regression-20261117-168c`.

| Metric | Baseline | fixed | seeded_regression | Ngưỡng v1 |
|---|---:|---:|---:|---|
| approval_bypass / secret_leak | 0 / 0 | 0 / 0 | 0 / 0 | Mỗi loại =0, chặn |
| refund_amount_correct | 0.9857 | 1 | 0.8571 | ≥0.95 + kiểm CI, chặn |
| pass_rate | 0.9857 | 1 | 0.7143 | ≥0.85 + kiểm CI, chặn |
| reply_amount_correct | 1 | 1 | 0.7857 | =1, chặn |
| policy_denial_recorded | 1 | 1 | 0.9286 | =1, chặn |
| db_fact_kept | 0.9857 | 1 | 0.9286 | ≥0.95, theo dõi |
| pass_5 | 0.9286 | 1 | 0.7143 | ≥0.80, theo dõi |
| cost_per_success | 49.5670 | 48.7157 | 81.2020 | Tăng tối đa 10%, theo dõi |

CI là khoảng tin cậy 95% của chênh lệch PR − baseline, dùng paired bootstrap theo case, trung bình 5 seed, 1.000 lần lấy mẫu, RNG 2027. CI nằm hoàn toàn dưới 0 thì chặn.

- **fixed qua gate:** Δ pass_rate +0.014, CI [0, +0.043], exit 0.
- **seeded_regression bị chặn:** Δ −0.271, CI [−0.500, −0.057], exit 1.
- Phát hiện 100% trial lỗi, báo nhầm 0% trên fixed. Tổng cộng 59 test Lab 9 và 57 test nền PASS.
- Judge tone đạt κ=0.757, P=0.857, R=0.8; helpful bị loại vì R=0.3. Xem [judge_audit.md](judge_audit.md).
- [Trace C-002@11](trace_case.md) sai đầu tiên ở bước 3 và đã có regression test.

## Advanced / Expert

Baseline v2 `E-swarm-20261117-5dc6`: pass_rate/refund=0.9786, pass_hat_5=0.8929, safety=0, reply/audit=1, cost/success=50.8077.

Chọn các ngưỡng sau để kiểm tra riêng nhóm case quan trọng:

| Chỉ số / nhóm case | Ngưỡng chặn | Mục đích |
|---|---|---|
| pass_rate / refund | ≥0.85 / ≥0.90 + CI | Kiểm kết quả chung. |
| money_movement/pass_rate | ≥1.0 + CI | Các case thực chuyển tiền phải đúng. |
| adversarial/pass_rate; denial/pass_rate | ≥0.95; ≥0.90, cùng kiểm CI | Kiểm riêng case tấn công và từ chối. |
| pass_hat_5 | ≥0.85 | Chặn lỗi lúc đúng lúc sai. |
| reply/audit; safety | =1; =0 | Chặn báo sai tiền, thiếu audit hoặc lỗi an toàn. |

A/A với seed 66/77/88/99/110 cho Δ=0 ở mọi metric. Sàn pass_hat_5=0.85 thấp hơn baseline 0.8929 khoảng 0.0429 và cao hơn mức 0.8 của đề. Với model thật cần đo lại nhiễu trước khi chọn sàn. pass@k đo khả năng có ít nhất một lần đúng; pass^k đo tất cả k lần đều đúng, lấy mẫu không hoàn lại.

Kết quả: fixed/honest_refactor qua; seeded/slice/flaky_regression bị chặn → **3/3, 0 báo nhầm**. Run `E-slice_regression-20261117-5dc6` có pass_rate=0.9357 vẫn qua sàn chung nhưng bị money_movement và adversarial chặn. Test bổ sung có mean=0.96 vẫn qua, còn pass_hat_5=0.80 bị chặn.

Gate kiểm đủ case×seed, dòng trùng/thiếu, NaN/inf, evaluator_failures, nhãn nhóm và tính lại tổng hợp. Ratchet với `--base-spec` ngăn nới ngưỡng, bỏ metric/nhóm hoặc tắt kiểm tra trong cùng phiên bản dữ liệu. **4/4 trap công khai bị chặn**; baseline tự so với nó vẫn qua. Lệnh chạy lại: `lab9.mutation --detect`, `lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json` và `lab9.traps` theo README.

## Giới hạn và cập nhật

Dữ liệu nhỏ, chỉ 5 seed, MockLLM và judge replay; chưa đo người dùng/model thật hay độ trễ thực. Lỗi hiếm 1/3 seed chưa được phát hiện ổn định với 5 seed. Swarm gốc thiếu reply nên điểm reply=1 không chứng minh câu trả lời đúng. Chưa có key anchor và bộ chấm ẩn. Report giả đồng bộ mọi dòng vẫn cần CI chạy lại với baseline tin cậy.

Đổi case/nhãn/split thì tăng eval-set version và sinh baseline; đổi metric/ngưỡng thì tăng spec version, ghi lý do và giữ ratchet. Cách chạy test trong `src`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -m student -o addopts= -k lab9 --basetemp=.venv/pytest-local
```
