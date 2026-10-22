"""MCP server cho Badminton Advisor: bọc các hàm có sẵn thành tool.
Chạy bằng stdio. KHÔNG print() ra stdout (stdout là kênh giao thức)."""
from shoe_recommender import recommend_shoes, find_shoe, GENDERS
from clean_shoes import ALLOWED as SHOE_ALLOWED
from recommender import recommend, find_racket
from clean_rackets import ALLOWED
from knowledge import search_knowledge
from mcp.server.fastmcp import FastMCP
import sys
import json

_real_stdout = sys.stdout
sys.stdout = sys.stderr  # mọi print trong lúc import đi vào stderr


sys.stdout = _real_stdout

ENUM = {k: list(ALLOWED[k])
        for k in ("level", "play_style", "balance", "stiffness")}

mcp = FastMCP("badminton-advisor")


def _check_enum(col, value):
    if value is not None and value not in ENUM[col]:
        raise ValueError(
            f"{col}={value!r} không hợp lệ, cho phép: {ENUM[col]}")


def _need_name(name, what):
    name = str(name).strip()
    if not name:
        raise ValueError(f"thiếu tên {what}")
    return name


@mcp.tool(
    name="recommend_racket",
    description=(
        "Gợi ý vợt cầu lông từ cơ sở dữ liệu của cửa hàng. Đây là NGUỒN DUY NHẤT để chọn vợt. "
        "Chỉ gọi khi đã biết level, play_style và max_price (EUR); thiếu thì hỏi lại người dùng, không đoán. "
        f"level: {ENUM['level']}. play_style: {ENUM['play_style']} "
        "(attack=tấn công, speed=nhanh/phản tạt, control=kiểm soát, allround=đa dụng). "
        f"balance: {ENUM['balance']}, stiffness: {ENUM['stiffness']}: chỉ điền khi người dùng nói rõ. "
        "Chỉ nhắc đến vợt có trong kết quả. Đọc trường status: exact = khớp hoàn toàn; "
        "approximate = chỉ gần đúng, phải nêu điểm lệch;"     "no_good_match / no_rackets_in_budget = nói thẳng là không có vợt trong ngân sách. "
        "Nếu cheapest_match là đối tượng: nêu đúng name, price_eur, level, play_style của nó; "
        "nếu is_exact là false thì nói rõ đó chỉ là vợt gần nhất, không gọi là 'phù hợp', rồi hỏi người dùng "
        "có muốn nâng ngân sách không. Nếu cheapest_match là null thì nói cửa hàng chưa có vợt nào đủ gần "
        "ở mọi mức giá. Không nêu con số ngân sách nào khác."
    ),
)
def tool_recommend_racket(level: str, play_style: str, max_price: float,
                          balance: str | None = None, stiffness: str | None = None) -> dict:
    for col, v in (("level", level), ("play_style", play_style),
                   ("balance", balance), ("stiffness", stiffness)):
        _check_enum(col, v)
    result = recommend(level=level, play_style=play_style, max_price=float(max_price),
                     balance=balance, stiffness=stiffness)
    return json.loads(json.dumps(result,ensure_ascii=False))

@mcp.tool(
    name="find_racket",
    description=(
        "Tra thông tin một cây vợt cụ thể theo tên (giá, trình độ, lối chơi...) trong cơ sở dữ liệu "
        "cửa hàng, ví dụ 'Astrox 99 Pro'. Chỉ nói thông tin có trong kết quả; status not_found nghĩa là "
        "cửa hàng không có vợt đó, không đoán từ kiến thức bên ngoài. Không dùng để gợi ý vợt theo nhu cầu."
    ),
)
def tool_find_racket(name: str) -> dict:
    return find_racket(_need_name(name, "vợt"))


@mcp.tool(
    name="search_knowledge",
    description=(
        "Tra cứu kiến thức cầu lông từ kho tài liệu đã kiểm soát: balance (head heavy/light), độ cứng "
        "đũa vợt, 3U/4U, cỡ cán G, độ căng cước, lời khuyên theo trình độ. Dùng cho câu hỏi giải thích "
        "hoặc khái niệm. CHỈ dùng nội dung trong passages trả về và nói rõ đó là thông tin theo nguồn "
        "(source_url). status no_relevant_knowledge thì nói thẳng kho chưa có thông tin này. "
        "Không dùng để tra giá/tên vợt cụ thể (dùng find_racket) hay gợi ý vợt theo ngân sách (dùng recommend_racket)."
    ),
)
def tool_search_knowledge(query: str) -> dict:
    q = str(query).strip()
    if not q:
        raise ValueError("thiếu query")
    result = search_knowledge(q)
    if result.get("status") == "error":
        raise ValueError(str(result))
    return result


@mcp.tool(
    name="recommend_shoes",
    description=(
        "Gợi ý giày cầu lông từ cơ sở dữ liệu của cửa hàng. Đây là NGUỒN DUY NHẤT để chọn giày. "
        "Chỉ gọi khi đã biết gender (men/women) và size_eu; thiếu thì hỏi lại, không đoán. "
        "Nếu người dùng nói size theo hệ khác (UK, US, cm) thì hỏi size EU, không tự quy đổi. "
        "prefer_light, width, max_price chỉ điền khi người dùng nói rõ. "
        f"width: {sorted(SHOE_ALLOWED['width'])} (narrow=hẹp, standard=chuẩn, wide=rộng). "
        "Chỉ nhắc đến giày có trong kết quả. Nếu excluded_no_data không rỗng, nêu tên các đôi đó và lý do "
        "chưa xếp. Khi nói về độ nhẹ, nêu số gram kèm size đo và nhắc cân nặng chỉ gần đúng. "
        "status no_shoes_for_size = không có giày cho giới tính và size đó; "
        "no_data_for_criteria = thiếu dữ liệu cho tiêu chí đã chọn."
        "Giày unisex đã nằm sẵn trong kết quả, không cần hỏi thêm."
    ),
)
def tool_recommend_shoes(gender: str, size_eu: float, prefer_light: bool = False,
                         width: str | None = None, max_price: float | None = None) -> dict:
    if gender not in GENDERS:
        raise ValueError(f"gender phải là một trong {sorted(GENDERS)}")
    if width is not None and width not in SHOE_ALLOWED["width"]:
        raise ValueError(
            f"width={width!r} không hợp lệ, cho phép: {sorted(SHOE_ALLOWED['width'])}")
    return recommend_shoes(gender=gender, size_eu=float(size_eu), prefer_light=bool(prefer_light),
                           width=width, max_price=float(max_price) if max_price is not None else None)


@mcp.tool(
    name="find_shoe",
    description=(
        "Tra thông tin một đôi giày cụ thể theo tên (giá, giới tính, khoảng size EU, cân nặng, form) "
        "trong cơ sở dữ liệu cửa hàng, ví dụ 'Subaxia GT'. Chỉ nói thông tin có trong kết quả; "
        "status not_found = cửa hàng không có đôi đó; trường null = chưa có dữ liệu, hãy nói đúng như vậy. "
        "Cân nặng luôn kèm weight_ref_size_eu. Không dùng để gợi ý giày theo nhu cầu (dùng recommend_shoes)."
    ),
)
def tool_find_shoe(name: str) -> dict:
    return find_shoe(_need_name(name, "giày"))


if __name__ == "__main__":
    mcp.run()  # mặc định: stdio
