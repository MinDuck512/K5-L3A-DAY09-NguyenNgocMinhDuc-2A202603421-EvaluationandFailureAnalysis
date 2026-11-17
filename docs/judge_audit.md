# Đánh giá judge

Dùng hai CSV công khai, mỗi tập 100 dòng, với FAIL là lớp dương. Điều kiện đạt: κ≥0.6, Precision≥0.8, Recall≥0.7.

| Judge | TP / FP / FN / TN | Precision | Recall | κ | Kết luận |
|---|---|---|---|---|---|
| tone_ok | 24 / 4 / 6 / 66 | 0.857 | 0.800 | 0.757 | Đủ dùng để chấm giọng điệu. |
| helpful | 9 / 0 / 21 / 70 | 1.000 | 0.300 | 0.375 | Không dùng làm gate vì bỏ sót 21 lỗi. |

Tỉ lệ lỗi quan sát là 0.28/0.09; Rogan–Gladen hiệu chỉnh cả hai về 0.30. Precision cao chưa đủ nếu Recall thấp.

## Các trường hợp bất đồng

Giữ nhãn người có sẵn trong CSV làm chuẩn để đối chiếu, không coi đây là dữ liệu mới tự gán nhãn.

| Case | Judge / người | Nhận xét và cách sửa rubric |
|---|---|---|
| H-008 | PASS / FAIL | “Em/anh… rồi nha, check” quá thân mật; thêm ví dụ xưng hô phù hợp. |
| H-029 | PASS / FAIL | “Không cần nhắn thêm” mang tính ra lệnh; cần xét cả câu. |
| H-042 | FAIL / PASS | Câu ngắn nhưng đủ tiền và thời gian nhận; không bắt buộc xin lỗi dài. |
| H-051 | FAIL / PASS | Từ “refund” được chấp nhận; không tự động loại câu có tiếng Anh. |
| HL-015 | PASS / FAIL | Reply 55.000đ, ledger 40.000đ; kiểm tiền bằng code. |

Chọn tone_ok để chấm giọng điệu, loại helpful khỏi gate; tiền và phê duyệt luôn kiểm bằng code. Kết quả mới chỉ dựa trên CSV replay công khai, cần thêm nhãn người độc lập để kiểm chứng.

Chạy `python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5` trong `src` nhận exit 0. Đổi sang `judge_helpful_public.csv` nhận exit 1 đúng kỳ vọng.
