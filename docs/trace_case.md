# Phân tích lỗi C-002, seed 11

Em chọn lỗi **FM-03: tin ticket hơn DB** để tìm bước sai đầu tiên.

| Nội dung | Kết quả |
|---|---|
| Case | `seeded_regression C-002@11`; trace `R-seeded_regression-C-002-s11`. |
| Report | `E-seeded_regression-20261117-168c`; đối chứng `E-fixed-20261117-168c`. |
| Lỗi | Ledger và reply đều là 20.000đ, trong khi nhãn đúng là 0. `db_fact_kept`, `refund_amount_correct`, `pass_rate` đều FAIL. |
| Bước sai đầu tiên | **Bước 3 `model_override`**: đổi số ngày trễ từ 2 trong DB thành 5 theo ticket. |
| Vì sao là đầu tiên | Bước 1 chuyển đúng claim, bước 2 đọc đúng DB. Sau bước 3, agent mới tính và báo hoàn sai tiền. |
| So với fixed | Cùng case và seed, fixed giữ trễ 2 ngày, không hoàn tiền, ledger bằng 0 và PASS. |

Test `test_trace_case_ticket_override_is_the_first_visible_wrong_step` trong `src/tests/test_lab9_submission.py` kiểm tra đúng bước 3 và ledger 20.000/0 của hai bản. Test hiện PASS: bản lỗi bị phát hiện, fixed xử lý đúng.

Chạy lại trong `src`:

```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k ticket_override --basetemp=.venv/pytest-local
```

Kết luận: phải giữ dữ kiện từ DB khi ticket mâu thuẫn. Trace chỉ cho thấy các bước được ghi lại, không chứng minh quá trình suy nghĩ bên trong model.
