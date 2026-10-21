"""Agent tối giản: LLM hiểu câu hỏi -> gọi recommend() -> diễn đạt kết quả."""
import json
import os

from dotenv import load_dotenv
import anthropic

from knowledge import search_knowledge
from config import ROOT
from clean_rackets import ALLOWED
from recommender import recommend, find_racket
from clean_shoes import ALLOWED as SHOE_ALLOWED
from shoe_recommender import recommend_shoes, GENDERS

load_dotenv(ROOT / ".env")
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_STEPS = 5  # chặn vòng lặp vô hạn

client = anthropic.Anthropic()  # tự đọc ANTHROPIC_API_KEY từ môi trường

# Giá trị hợp lệ lấy từ ALLOWED: một nguồn sự thật duy nhất
ENUM = {k: list(ALLOWED[k]) for k in ("level", "play_style", "balance", "stiffness")}

TOOLS = [{
    "name": "recommend_racket",
    "description": (
        "Gợi ý vợt cầu lông từ cơ sở dữ liệu của cửa hàng. Đây là NGUỒN DUY NHẤT "
        "để chọn vợt. Chỉ gọi khi đã biết level, play_style và ngân sách. "
        "Nếu thiếu một trong ba, hãy hỏi lại người dùng thay vì đoán. "
        "balance và stiffness chỉ điền khi người dùng nói rõ."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "level": {"type": "string", "enum": ENUM["level"],
                      "description": "Trình độ người chơi."},
            "play_style": {"type": "string", "enum": ENUM["play_style"],
                           "description": "Lối chơi: attack=tấn công, speed=nhanh/phản tạt, "
                                          "control=kiểm soát, allround=đa dụng."},
            "max_price": {"type": "number", "description": "Ngân sách tối đa, đơn vị EUR."},
            "balance": {"type": "string", "enum": ENUM["balance"],
                        "description": "Điểm cân bằng. Bỏ trống nếu người dùng không nói."},
            "stiffness": {"type": "string", "enum": ENUM["stiffness"],
                          "description": "Độ cứng thân vợt. Bỏ trống nếu không nói."},
        },
        "required": ["level", "play_style", "max_price"],
    },
    },
     {
    "name": "search_knowledge",
    "description": (
        "Tra cứu kiến thức cầu lông từ kho tài liệu đã kiểm soát: balance "
        "(head heavy/light), độ cứng đũa vợt, 3U/4U, cỡ cán G, độ căng cước, "
        "lời khuyên theo trình độ. Dùng cho câu hỏi giải thích hoặc khái niệm. "
        "KHÔNG dùng để tra giá/tên vợt cụ thể (dùng find_racket) và không dùng "
        "để gợi ý vợt theo ngân sách (dùng recommend_racket)."
     ),
     "input_schema": {
         "type": "object",
        "properties": {
           "query": {
                 "type": "string",
                 "description": "Câu hỏi của người dùng, giữ nguyên cách gọi (ví dụ 'nặng đầu', 'head heavy')",
             }
         },
         "required": ["query"],
     },
     },
    {
    "name": "find_racket",
    "description": (
        "Tra thông tin một cây vợt cụ thể theo tên (giá, trình độ, lối chơi...) "
        "trong cơ sở dữ liệu cửa hàng. Dùng khi người dùng hỏi về một vợt có tên. "
        "Không dùng để gợi ý vợt theo nhu cầu."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Tên vợt, ví dụ 'Astrox 99 Pro'."}},
        "required": ["name"],
    },
    },
        {
    "name": "recommend_shoes",
    "description": (
        "Gợi ý giày cầu lông từ cơ sở dữ liệu của cửa hàng. Đây là NGUỒN DUY NHẤT để chọn giày. "
        "Chỉ gọi khi đã biết giới tính (men/women) và size EU. Thiếu một trong hai thì hỏi lại, không đoán. "
        "Nếu người dùng nói size theo hệ khác (UK, US, cm) thì hỏi size EU, không tự quy đổi. "
        "prefer_light và width chỉ điền khi người dùng nói rõ."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "gender": {"type": "string", "enum": sorted(GENDERS), "description": "men hoặc women."},
            "size_eu": {"type": "number", "description": "Size giày hệ EU, ví dụ 42 hoặc 42.5."},
            "prefer_light": {"type": "boolean", "description": "true nếu người dùng ưu tiên giày nhẹ."},
            "width": {"type": "string", "enum": sorted(SHOE_ALLOWED["width"]),
                      "description": "Form: narrow=hẹp, standard=chuẩn, wide=rộng (bàn chân to ngang)."},
            "max_price": {"type": "number", "description": "Ngân sách tối đa, EUR. Bỏ trống nếu không nói."},
        },
        "required": ["gender", "size_eu"],
    },
    }
]

    


SYSTEM = """Bạn là tư vấn viên vợt và giày cầu lông vui tính. Trả lời bằng ngôn ngữ người dùng đang dùng. .
Quy tắc:
1. Chỉ nhắc đến vợt có trong kết quả của công cụ recommend_racket. Không bịa vợt, giá hay thông số.
2. Thiếu level, play_style hoặc ngân sách thì hỏi lại, chỉ hỏi một câu ngắn. Đừng đoán.
3. Đọc trường status và nói đúng sự thật:
   - exact: vợt khớp hoàn toàn.
   - approximate: nói rõ là chỉ gần đúng, nêu điểm lệch (dùng trường note/reason).
   - no_good_match / no_rackets_in_budget:  nói thẳng là không có. Nếu cheapest_match là một đối tượng, được nêu đúng name, price_eur, level, play_style của nó. Nếu is_exact là false, phải nói rõ đó chỉ là vợt gần nhất (gọi level/play_style thật của nó, không gọi là "phù hợp"), rồi hỏi người dùng có muốn nâng ngân sách không. Nếu cheapest_match là null thì nói cửa hàng chưa có vợt nào đủ gần ở mọi mức giá. Không nêu con số ngân sách nào khác.
4. Ngắn gọn, mỗi vợt một dòng kèm lý do.
5. Khi người dùng hỏi về một vợt cụ thể theo tên (giá, thông số), gọi find_racket. Chỉ nói thông tin có trong kết quả. status not_found thì nói thẳng là cửa hàng không có vợt đó, không đoán từ kiến thức bên ngoài.
6. Câu hỏi giải thích hoặc khái niệm về vợt (head heavy/light, độ cứng, 3U/4U, cỡ cán, độ căng cước, nên chọn loại nào theo trình độ): gọi search_knowledge và CHỈ dùng nội dung trong passages trả về. Không thêm kiến thức ngoài.
7. Nếu status là no_relevant_knowledge, hoặc các đoạn không thật sự nói về điều được hỏi (chỉ cùng chủ đề), nói thẳng là kho kiến thức chưa có thông tin này. Không tự trả lời bằng kiến thức chung.
8. Khi trả lời từ passages, nói đây là thông tin theo nguồn (tên trang trong source_url), không trình bày như sự thật tuyệt đối.
9. Gợi ý giày: gọi recommend_shoes. Cần giới tính (men/women) và size EU; thiếu thì hỏi một câu ngắn, đừng đoán. Giày unisex đã nằm sẵn trong kết quả.
10. Chỉ nhắc đến giày có trong kết quả recommend_shoes. status no_shoes_for_size: nói thẳng là không có giày cho giới tính và size đó, không nêu giày khác. status no_data_for_criteria: nói là thiếu dữ liệu cho tiêu chí đã chọn.
11. Nếu excluded_no_data không rỗng, nêu tên các đôi đó và lý do chưa xếp.
12. Khi nói về độ nhẹ, nêu số gram và size đo (trong reason), không chỉ nói điểm; nhắc là cân nặng chỉ gần đúng (theo note). Nếu note nói chưa có tiêu chí mềm thì nói các đôi đang xếp theo giá.
13. Chưa có công cụ tra giày theo tên. Hỏi về một đôi cụ thể thì chỉ dùng thông tin nếu nó nằm trong kết quả recommend_shoes, nếu không thì nói chưa hỗ trợ tra giày theo tên. Người hỏi cả vợt và giày thì xử lý từng phần với công cụ riêng.
"""


def run_tool(name: str, args: dict) -> tuple[str, bool]:
    """Chạy tool thật. Trả (nội dung_json, is_error). Kiểm tra đầu vào trước khi gọi."""
    if name == "find_racket":
        n = str(args.get("name", "")).strip()
        if not n:
            return json.dumps({"error": "thiếu tên vợt"}), True
        try:
            return json.dumps(find_racket(n), ensure_ascii=False), False
        except Exception as e:
            return json.dumps({"error": str(e)}), True

    if name == "search_knowledge":
        q = str(args.get("query", "")).strip()
        if not q:
            return json.dumps({"error": "thiếu query"}), True
        result = search_knowledge(q)
        return json.dumps(result, ensure_ascii=False), result.get("status") == "error"

    if name == "recommend_shoes":
        if args.get("gender") not in GENDERS:
            return json.dumps({"error": f"gender phải là một trong {sorted(GENDERS)}"}), True
        w = args.get("width")
        if w is not None and w not in SHOE_ALLOWED["width"]:
            return json.dumps({"error": f"width={w!r} không hợp lệ, cho phép: {sorted(SHOE_ALLOWED['width'])}"}), True
        try:
            mp = args.get("max_price")
            result = recommend_shoes(
                gender=args["gender"], size_eu=float(args["size_eu"]),
                prefer_light=bool(args.get("prefer_light", False)), width=w,
                max_price=float(mp) if mp is not None else None,
            )
        except Exception as e:
            return json.dumps({"error": str(e)}), True
        return json.dumps(result, ensure_ascii=False), False
    if name != "recommend_racket":
        return json.dumps({"error": f"tool lạ: {name}"}), True
    
    for col in ("level", "play_style", "balance", "stiffness"):
        v = args.get(col)
        if v is not None and v not in ENUM[col]:
            return json.dumps({"error": f"{col}={v!r} không hợp lệ, cho phép: {ENUM[col]}"}), True
    try:
        result = recommend(
            level=args["level"], play_style=args["play_style"],
            max_price=float(args["max_price"]),
            balance=args.get("balance"), stiffness=args.get("stiffness"),
        )
    except Exception as e:  # trả lỗi về cho LLM thay vì làm sập chương trình
        return json.dumps({"error": str(e)}), True
    return json.dumps(result, ensure_ascii=False), False


def chat_turn(messages: list) -> str:
    """Một lượt hội thoại: lặp đến khi LLM trả lời bằng chữ."""
    for _ in range(MAX_STEPS):
        resp = client.messages.create(
            model=MODEL, max_tokens=1000, system=SYSTEM,
            tools=TOOLS, messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return "".join(b.text for b in resp.content if b.type == "text")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                print(f"  [tool] {block.name}({json.dumps(block.input, ensure_ascii=False)})")
                content, is_err = run_tool(block.name, block.input)
                if block.name == "search_knowledge":
                    print("  [passages]", [p["id"] for p in json.loads(content).get("passages", [])])
                tool_results.append({"type": "tool_result", "tool_use_id": block.id,
                                     "content": content, "is_error": is_err})
        messages.append({"role": "user", "content": tool_results})
    return "(Dừng: vượt số bước tối đa.)"


if __name__ == "__main__":
    print("Badminton advisor. Gõ 'q' để thoát.")
    history: list = []  # giữ lịch sử để agent hỏi lại và nhớ câu trả lời
    while True:
        text = input("\nBạn: ").strip()
        if text.lower() in ("q", "quit", "exit"):
            break
        history.append({"role": "user", "content": text})
        print("Bot:", chat_turn(history))