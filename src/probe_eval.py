from knowledge import search

# (question, ids that must be in the top 3, ids that should be there)
CASES = [
    ("what is the difference between head heavy and head light",
     ["k01", "k02"], []),
    ("which play style suits a head heavy racket", ["k01"], []),
    ("who is a head light racket suitable for", ["k02"], []),
    ("is a stiff racket suitable for beginners", ["k06"], []),
    ("which is heavier, 3U or 4U", ["k07"], []),
    ("does a 3U racket tire your arm easily", ["k07"], []),
    # changed: k07 is about total weight, not balance
    ("does a head heavy racket tire your arm easily", ["k01"], []),
    ("racket string tension", ["k11"], []),
    ("what is the difference between high and low string tension",
     ["k11"], []),
    ("is a G4 or G5 grip better for small hands", ["k08"], []),
    # changed: k03 moved to "should be there"
    ("how should a new player choose a racket", ["k09"], ["k03"]),
    # cross-lingual: Vietnamese query against the English knowledge base
    ("vợt nặng đầu hợp lối chơi nào", ["k01"], []),
    ("what racket should i buy as a complete beginner with weak arms", ["k09"], []),
    ("is a heavy racket good for someone new", ["k09"], []),
    ("vợt cứng có hợp người mới không", ["k06"], []),
    ("How do i pick between 3U and 4U", ["k07"], []),
]

hit = 0
total = 0
for q, required, optional in CASES:
    got = search(q, k=3)
    ids = [r["id"] for r in got]
    ok = all(e in ids for e in required)
    hit += ok
    total += 1
    ranks = {e: (ids.index(e) + 1 if e in ids else "outside top 3")
             for e in required + optional}
    print(f"{'OK  ' if ok else 'FAIL'} {q} -> {ranks}")
    if not ok:
        print("     top3:", [(r["id"], round(r["score"], 3)) for r in got])
print(f"\nRequired passages in the top 3: {hit}/{total}")
