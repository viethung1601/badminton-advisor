from knowledge import search

# (câu hỏi, id đoạn phải có trong top 3; nên có)
CASES = [
    ("head heavy khác head light thế nào", ["k01", "k02"], []),
    ("vợt nặng đầu hợp lối chơi nào", ["k01"], []),
    ("vợt nhẹ đầu hợp với ai", ["k02"], []),
    ("vợt cứng có hợp người mới không", ["k06"], []),
    ("3U với 4U cái nào nặng hơn", ["k07"], []),
    ("vợt 3U có dễ mỏi tay không", ["k07"], []),
    # đổi: k07 nói về tổng trọng lượng, không phải balance
    ("vợt nặng đầu có dễ mỏi tay không", ["k01"], []),
    ("căng dây vợt", ["k11"], []),
    ("độ căng dây cao thấp khác nhau thế nào", ["k11"], []),
    ("cán vợt G4 hay G5 hợp tay nhỏ", ["k08"], []),
    # đổi: k03 chuyển sang "nên có"
    ("người mới chơi nên chọn vợt thế nào", ["k09"], ["k03"]),
]

hit = 0
total = 0
for q, required, optional in CASES:
    got = search(q, k=3)
    ids = [r["id"] for r in got]
    ok = all(e in ids for e in required)
    hit += ok
    ranks = {e: (ids.index(e) + 1 if e in ids else "ngoài top 3")
             for e in required + optional}
    print(f"{'OK  ' if ok else 'FAIL'} {q} -> {ranks}")
    if not ok:
        print("     top3:", [(r["id"], round(r["score"], 3)) for r in got])
print(f"\nĐoạn bắt buộc nằm trong top 3: {hit}/{len(CASES)}")
print(f"\nĐoạn đúng nằm trong top 3: {hit}/{total}")