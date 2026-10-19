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

## Ask an expert (n8n + Discord)

Users can send a question to a human expert from the web page. The question goes through n8n into a private Discord channel.

```
Browser ("Send to expert" button)
  -> POST /ask-expert (FastAPI)
  -> n8n webhook /webhook/ask-expert
  -> HTTP Request -> Discord #expert-inbox
```

The expert answers publicly in `#hỏi-đáp` and tags the asker (this step is manual).

### Run n8n

```bash
docker run -d --name n8n -p 5678:5678 \
  -e GENERIC_TIMEZONE=Europe/Berlin \
  -e TZ=Europe/Berlin \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

The volume keeps workflows when the container is stopped or removed. Open http://localhost:5678.

### Import the workflow

1. In n8n: menu `...` -> **Import from File** -> `n8n/ask-expert.workflow.json`.
2. Open the **HTTP Request** node and replace `https://discord.com/api/webhooks/REDACTED` with the webhook URL of your own Discord channel.
3. **Save**, then switch the workflow to **Active**.

### Configuration

In `.env` (not committed):

```
N8N_WEBHOOK_URL=http://localhost:5678/webhook/ask-expert
```

FastAPI always calls `/webhook/` (the workflow must be Active), never `/webhook-test/`.

### Design decisions

- Sending a message out is triggered by a **user click**, not by an LLM tool, so prompt injection cannot make the system send messages on its own.
- The server accepts only a numeric Discord ID (17-20 digits) and builds the profile link itself; n8n receives only `question`, `discord_id` and `discord_url`.
- `allowed_mentions: {parse: []}` blocks @everyone/@role pings.
- Question text is not logged.

### Known limitations

- The Discord ID is typed by the user and **not verified** (verification would need Discord OAuth2).
- Chat sessions live in RAM: lost on restart, no multi-worker setup.
- No authentication; the 3-questions-per-session limit can be bypassed by creating a new session.
- The local n8n webhook is not authenticated.
- The expert's reply path back to the user is manual.

## đo câu trả lời của agent có đúng hay không dựa trên nguồn kiến thức được định nghĩa trong knowledge.csv
- Nhóm A-F: 95/95 sau khi thêm RAG (cùng mốc trước RAG, nên không hồi quy trên bộ này).
- Nhóm G: 40/40 trên 8 câu x 5 lượt, sau các chỉnh sửa k02, k09 và mô tả tool.
- Truy xuất riêng (probe_eval): 10/11, lỗi còn lại là “nhẹ đầu hợp với ai” đưa k02 xuống hạng 5.
- Lưu ý: D2 dao động 7/10 đến 10/10 giữa các lần chạy, kể cả trước RAG. Chỉ có mốc “trước/sau” cho G3, các nhóm khác không có mốc trước.
- Tổng kết: 135/135 không có nghĩa lỗi = 0, nguồn là blog của các shops, chưa có người dùng thật

