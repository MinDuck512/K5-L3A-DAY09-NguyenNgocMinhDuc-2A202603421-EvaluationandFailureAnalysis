# Trace case — C-002, seed 11

| Mục | Kết quả thực tế |
|---|---|
| Trial lỗi | `seeded_regression C-002@11`, trace `R-seeded_regression-C-002-s11`; report `E-seeded_regression-20261117-168c`. |
| Triệu chứng | Ledger hoàn 20.000đ trong khi nhãn yêu cầu 0; reply cũng nói đã hoàn 20.000đ. `db_fact_kept`, `refund_amount_correct` và `pass_rate` FAIL. |
| Bước sai đầu tiên | Event **#3 `model_override`**: delay từ DB là 2 bị thay thành 5 theo ticket. FM-03 `ticket_trust`. |
| Vì sao là đầu tiên | #1 handoff đúng claim; #2 investigator đọc đúng delay=2. Đến #3 mới thay dữ kiện đáng tin. #4 quote 20.000 và #5 reply là hậu quả sau đó. |
| Đối chứng | `fixed C-002@11` không có model_override, dùng delay=2, không hoàn tiền; ledger 0 và Lab 8 PASS. Report `E-fixed-20261117-168c`. |
| Regression test | `src/tests/test_lab9_submission.py::test_trace_case_ticket_override_is_the_first_visible_wrong_step`: kiểm tra variant lỗi FAIL, fixed PASS, ledger lần lượt 20.000/0 và chỉ event #3 là override. Test đã chạy PASS. |
| Giới hạn | Đây là bước sai đầu tiên quan sát được trong trace; không suy diễn suy nghĩ nội bộ hay bước không được ghi. |

Trong `src`:

```powershell
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= -k ticket_override --basetemp=.venv/pytest-local
```

Test bắt lại hành vi lỗi trên biến thể được cung cấp; không sửa agent để làm test xanh. Tiền được kiểm bằng ledger và nhãn, không dựa vào độ trôi chảy của reply.
