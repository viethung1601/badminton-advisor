# badminton-advisor

# Who are the users of BADMINTON ADVISOR?
# For Beginner, Intermediate and Advanced Players, who want to upgrade Badminton's Gears but still consider which racket, shoes or shuttles are suitable for them. 

# How can the users give filter to the app? 
# Self-estimate Badminton's level (in the future the app will include also the function, that users can import their videos to let the app estimate), Play-style (aggressive attack, attack, control, defense, balance...), budget, power of grip, colors, etc...

# What do the users claim from the app? 
# 3 best options for each item, that users want to ask for recommendations

# Judge the limit:
# Recommender là content-based ranking (khoảng cách Manhattan có trọng số), không huấn luyện từ dữ liệu.
# Trọng số và ngưỡng min_score do mình đặt dựa trên hiểu biết cầu lông, chưa được kiểm chứng bằng phản hồi người dùng.
# Dữ liệu nhỏ (26 vợt): một số tổ hợp level × style × balance còn trống, khi đó status = "approximate".
# Nhiều vợt có thể hoà điểm 1.0; thứ tự hiện chỉ theo giá tăng dần.

## Đánh giá agent

Bộ test `src/eval_agent.py`: 18 câu hỏi, 6 nhóm (đủ thông tin, thiếu thông tin,
hỏi theo tên vợt, khoảng giá trị, ngân sách quá thấp, lạc đề), mỗi câu chạy 5 lần.
Kiểm tra theo dữ kiện, không so từng chữ: tool có được gọi không, tham số đúng không,
tên vợt và con số trong câu trả lời có nằm trong kết quả tool (hoặc câu hỏi) không.

**Kết quả:** 90/90 lần chạy đạt. Lỗi thật chưa chắc bằng 0; với 90 lần chạy chỉ có thể
nói tỉ lệ lỗi trên bộ câu này thấp (khoảng dưới 3%).

**Lỗi tìm thấy và đã sửa nhờ bộ test:**
- Ngân sách thấp: bot tự nêu mức ngân sách không có trong dữ liệu (~9% số lần, nhóm E).
  Sửa theo 3 vòng: dặn trong prompt, đưa giá thấp nhất vào kết quả tool, rồi đưa cả
  thông tin vợt đó (level, style, is_exact) để bot không gọi vợt gần đúng là "phù hợp".
- Tra theo tên: tool tìm hụt khi người dùng gõ kèm hãng. Sửa truy vấn SQL.

**Giới hạn:**
- "Đủ gần" dựa trên MIN_SCORE = 0.5 và trọng số do tác giả tự đặt, không phải sự thật khách quan.
  Với ngưỡng này, vợt cho trình độ thấp hơn có thể lọt vào mục "gần nhất" của người chơi nâng cao.
- Script kiểm tra con số và tên vợt, chưa kiểm tra lời mô tả. Lỗi diễn đạt (như gọi vợt
  gần đúng là "phù hợp") chỉ phát hiện khi đọc câu trả lời thật.

## đánh giá model embedding cho câu trả lời dạng text
  - Truy xuất: 10/11 trên bộ 11 câu tự viết. Lỗi còn lại: ‘nhẹ đầu hợp với ai’ đưa k02 xuống hạng 5.”