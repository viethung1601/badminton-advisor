"""Sinh lại baseline từ code CŨ (commit trước refactor). Chỉ chạy được khi còn recommender.py,
shoe_recommender.py, catalog.py. Chạy từ thư mục gốc: python tests/make_baseline.py"""
import json, sys, itertools
from pathlib import Path
root = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(root / "src"))
import recommender as R, shoe_recommender as S, catalog as C

def clean(x): return json.loads(json.dumps(x, default=float, ensure_ascii=False))
out = {"recommend_racket": [], "find_racket": [], "recommend_shoes": [], "find_shoe": [],
       "list_rackets": [], "list_shoes": []}

for lv, st, price, (bal, stf) in itertools.product(
        ["beginner","intermediate","advanced"], ["attack","speed","control","allround"],
        [0, 20, 40, 60, 100, 200, 1000],
        [(None,None),("head_heavy",None),(None,"stiff"),("even","medium")]):
    a = dict(level=lv, play_style=st, max_price=float(price), balance=bal, stiffness=stf)
    out["recommend_racket"].append({"args": a, "result": clean(R.recommend(**a))})
for n in ["Astrox 99 Pro","axforce","li-ning","zzz","%","_","  Sabre  ",""]:
    out["find_racket"].append({"args": {"name": n}, "result": clean(R.find_racket(n))})

for g, sz, pl, w, mp in itertools.product(["men","women"], [36,38,40,42,42.5,44,50],
        [False, True], [None,"narrow","standard","wide"], [None,100,200]):
    a = dict(gender=g, size_eu=float(sz), prefer_light=pl, width=w, max_price=mp)
    out["recommend_shoes"].append({"args": a, "result": clean(S.recommend_shoes(**a))})
for n in ["Subaxia GT","yonex","zzz","%","SHB"]:
    out["find_shoe"].append({"args": {"name": n}, "result": clean(S.find_shoe(n))})

rk = [dict(), dict(sort="price_desc"), dict(sort="name"), dict(q="ax"), dict(q="%"), dict(q="_"),
      dict(brands=["Yonex"]), dict(brands=["Yonex","Li-Ning"]),
      dict(filters={"level":["beginner"]}), dict(filters={"play_style":["attack","speed"]}),
      dict(filters={"balance":["head_heavy"],"stiffness":["stiff","medium"]}),
      dict(filters={"weight_class":["4U"]}), dict(min_price=50, max_price=100),
      dict(limit=5, offset=5), dict(limit=3, offset=100)]
for kw in rk: out["list_rackets"].append({"args": kw, "result": clean(C.list_rackets(**kw))})
sk = [dict(), dict(sort="price_desc"), dict(sort="name"), dict(sort="weight_asc"),
      dict(filters={"gender":["men"]}), dict(filters={"width":["wide","standard"]}),
      dict(size_eu=42.0), dict(max_weight_g=330.0), dict(q="sub"), dict(brands=["Yonex"]),
      dict(min_price=100, max_price=170), dict(limit=2, offset=2)]
for kw in sk: out["list_shoes"].append({"args": kw, "result": clean(C.list_shoes(**kw))})

p = root / "tests" / "golden" / "baseline.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print({k: len(v) for k, v in out.items()}, "->", p)
