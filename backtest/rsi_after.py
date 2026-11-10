# -*- coding: utf-8 -*-
"""RSI 백테스트 After(2026-11-09): 사용자 승인(두 방식 비교) 후 같은 NVIDIA 10-Q를 다시 판정.
A = 전체 원문(자르지 않음) / B = AI Agent 수정안(숨김 XBRL 제거 + 앞 8,000자 + 가정 장부 키워드 주변 구간, 합계 40,000자)."""
import html, io, json, os, re, sys, time, hashlib
import requests
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))   # 저장소 구조: agent/thesis_guard_pilot.py
import thesis_guard_pilot as P
from rsi_bt import F, OUT, score

KW = ["export", "license", "H20", "excess inventory", "purchase obligation", "charge", "billion", "Data Center", "outlook"]


def judge_text(label, text, extra):
    import llm
    part = f"### {F['acc']} | {F['tk']} {F['form']} items= 접수 {F['accepted']} KST\n{text}"
    t0 = time.time()
    out = llm.call("kic", P.SYSTEM, "공시마다 카드 1장씩 판정하라.\n\n" + part, schema=P.SCHEMA, max_tokens=8000, anytime=True) or {"cards": []}
    use = json.loads(io.open(llm._ledger(), encoding="utf-8").read().strip().splitlines()[-1])
    cards = out.get("cards") or []
    src = P._norm(text)
    for c in cards:
        q = P._norm(c.get("quote", ""))
        c["quote_ok"] = bool(q) and q in src
    rec = {"cut": label, "n": 1, "accs": [F["acc"]], "cards": cards, "usd": use["usd"], "tok_in": use["in"], "tok_out": use["out"],
           "model": use["model"], "sec": round(time.time() - t0, 1), "chars": len(text), **extra}
    rec["score"] = score(rec)
    rec["hash"] = hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    P._add(OUT, rec)
    print(f"\n===== {label}  글자 {len(text):,} · 입력 {use['in']:,}/출력 {use['out']:,} 토큰 · ${use['usd']:.3f} · {rec['sec']}초 · 채점 {rec['score']}")
    for c in cards:
        print(f"[{c['action']}·{c['grade']}] {c['assumption']} | 인용 {'일치' if c['quote_ok'] else ('불일치' if c['quote'] else '없음')}\n  {c['summary']}\n  \"{c['quote'][:160]}\"")
    return rec


def clean_text(url):
    h = requests.get(url, headers=P.UA, timeout=30).text
    h = re.sub(r"(?is)<ix:header>.*?</ix:header>", " ", h)                  # 숨김 XBRL 블록
    h = re.sub(r"(?is)<div[^>]*display:\s*none[^>]*>.*?</div>", " ", h)
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def windows(t, budget=40000, front=8000, half=1500):
    hits = sorted((m.start(), kw) for kw in KW for m in re.finditer(re.escape(kw), t, re.I))
    if not hits:
        return t[:budget], 0
    spans = []
    for p, _ in hits:
        a, b = max(front, p - half), min(len(t), p + half)
        if b <= a:
            continue
        if spans and a <= spans[-1][1]:
            spans[-1][1] = max(spans[-1][1], b)
        else:
            spans.append([a, b])

    def sc(sp):
        seg = t[sp[0]:sp[1]]
        kinds = {kw for kw in KW if re.search(re.escape(kw), seg, re.I)}
        bonus = 3 if re.search(r"\$?\d[\d.,]*\s*(billion|million)", seg) and len(kinds) >= 2 else 0
        return (len(kinds) + bonus) / max(1.0, (sp[1] - sp[0]) / 3000)
    left = budget - front
    pick = []
    for sp in sorted(spans, key=sc, reverse=True):
        ln = sp[1] - sp[0]
        if ln > left:
            sp = [sp[0], sp[0] + left]; ln = left
        if ln <= 200:
            break
        pick.append(sp); left -= ln
    pick.sort()
    body = " ".join(f"[원문 위치 {a:,}~{b:,}] {t[a:b]}" for a, b in pick)
    return f"[원문 위치 0~{front:,}] {t[:front]} {body}", len(pick)


if __name__ == "__main__":
    appr = {"cut": "rsi-approval", "approved": True, "by": "사용자(운용역 역할)", "at": "2026-11-09",
            "note": "AI 수정안(B) 승인 + 전체 원문(A)도 함께 비교하라고 지시. 사유: 속도보다 정확도가 중요"}
    appr["hash"] = hashlib.sha256(json.dumps(appr, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    P._add(OUT, appr)
    full = P._docs(F)
    judge_text("rsi-after-A-전체원문", full, {"rule": "전체 원문, 자르지 않음"})
    t = clean_text(F["url"])
    wt, n = windows(t)
    print(f"\n(B 준비) 숨김 XBRL 제거 후 {len(t):,}자 → 앞 8,000자 + 구간 {n}개, 합계 {len(wt):,}자 · '4.5 billion' 포함: {'4.5 billion' in wt}")
    judge_text("rsi-after-B-키워드구간", wt, {"rule": "숨김 XBRL 제거 + 앞 8,000자 + 키워드 주변 ±1,500자, 합계 ≤40,000자", "windows": n})
