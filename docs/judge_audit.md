# Judge audit

FAIL là lớp dương. Kết quả từ hai CSV replay công khai, mỗi tập 100 dòng; không phải nhãn mới do người làm bài tự thu thập.

| Judge | TP / FP / FN / TN | Precision | Recall | κ | Quyết định |
|---|---|---|---|---|---|
| tone_ok | 24 / 4 / 6 / 66 | 0.857 | 0.800 | 0.757 | Đạt κ≥0.6, P≥0.8, R≥0.7; dùng đánh giá giọng điệu. |
| helpful | 9 / 0 / 21 / 70 | 1.000 | 0.300 | 0.375 | Không đạt; không dùng làm gate. |

Tỉ lệ FAIL quan sát tone/helpful là 0.28/0.09; Rogan–Gladen hiệu chỉnh đều về 0.30. Precision cao của helpful không bù được 21 lỗi bị bỏ sót. Số tiền đúng phải được kiểm bằng code.

## Đọc lại 7 bất đồng

“Người” là nhãn chuẩn có sẵn trong CSV. Các kết luận dưới đây đối chiếu câu trả lời với nhãn và ghi chú của tập đó.

| Case | Judge / người | Kết luận và điều chỉnh rubric |
|---|---|---|
| H-008 | PASS / FAIL | Theo nhãn người: “em/anh… rồi nha, check” quá thân mật. Nêu ví dụ xưng hô chuyên nghiệp, không chỉ kiểm sự thân thiện. |
| H-017 | PASS / FAIL | Theo nhãn người: “Dạ, bạn ơi… rồi nha” chưa phù hợp. Không dùng từ “Dạ” làm điều kiện đủ để PASS. |
| H-029 | PASS / FAIL | Theo nhãn người: “không cần nhắn thêm” mang tính ra lệnh. Đánh giá toàn câu, kể cả vế sau lời mở đầu lịch sự. |
| H-042 | FAIL / PASS | Theo nhãn người: câu ngắn vẫn đủ thông tin hoàn tiền và thời gian về tài khoản. Không bắt buộc xin lỗi dài. |
| H-051 | FAIL / PASS | Theo nhãn người: thuật ngữ “refund” được chấp nhận. Không tự động FAIL khi có từ tiếng Anh. |
| HL-015 | PASS / FAIL | Theo nhãn người: reply 55.000đ, ledger 40.000đ. Tách “đúng tiền” thành assertion code. |
| HL-016 | PASS / FAIL | Theo nhãn người: lời xin lỗi dài vẫn báo 55.000đ thay vì 35.000đ. Không dùng độ dài/lịch sự thay tính đúng. |

Chạy lại: `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` (exit 0); đổi sang `judge_helpful_public.csv` nhận exit 1 đúng kỳ vọng. Chưa thay dữ liệu replay để báo số đẹp hơn. Muốn kiểm chứng rubric mới cần tập nhãn người độc lập, chưa công khai.
