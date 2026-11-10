# -*- coding: utf-8 -*-
"""RSI 백테스트(2026-11-09, KIC 공모전 6장): NVIDIA 10-Q(2025-05-29) H20 실제 비용 45억 달러를 현재 규칙이 놓치는지 →
AI Agent 원인 분석·수정안 → (사람 승인) → 수정 규칙으로 재판정. 결과는 data/rsi_bt.jsonl.
사용: python rsi_bt.py before | analyze | after"""
import io, json, os, re, sys, time, hashlib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agent"))   # 저장소 구조: agent/thesis_guard_pilot.py
import thesis_guard_pilot as P

BASE = "https://www.sec.gov/Archives/edgar/data/1045810/000104581025000116"
F = {"acc": "0001045810-25-000116", "tk": "NVDA", "cik": 1045810, "form": "10-Q", "items": "",
     "accepted": "2025-05-29 05:32", "url": BASE + "/nvda-20250427.htm"}
TRUTH = {"assumptions": ["A3", "B1"], "action": "재검토",
         "must_quote_has": "4.5 billion",
         "why": "H20 수출 규제로 실제 비용(재고·구매 약정) 45억 달러 계상 — A3 '수출 규제로 인한 비용·재고 계상', B1 '예상 상한과 실제 계상액 분리'"}
OUT = "rsi_bt.jsonl"


def score(rec):
    cards = rec.get("cards", [])
    hit = [c for c in cards if c["action"] == "재검토" and any(a in c["assumption"] for a in TRUTH["assumptions"])
           and TRUTH["must_quote_has"] in c.get("quote", "") and c.get("quote_ok")]
    return {"pass": bool(hit), "n_cards": len(cards), "hit_cards": len(hit)}


def before():
    msg = P._judge([F], "🧪 RSI 백테스트 Before — 현재 규칙(공시 앞 40,000자)", {"cut": "rsi-before", "n": 1, "accs": [F["acc"]]}, OUT)
    rec = P._rows(OUT)[-1]
    rec["score"] = score(rec)
    print(msg); print("채점", rec["score"])
    io.open(P._p("rsi_before.json"), "w", encoding="utf-8").write(json.dumps(rec, ensure_ascii=False))


ANALYZE_SYS = """너는 공시 판정 에이전트의 '자기 개선(RSI)' 담당이다. 놓친 사례를 보고 원인을 찾고, 검색·수집 규칙의 수정안을 낸다.
규칙: 수정안은 사람이 승인해야만 적용된다. 판정 기준(가정 장부)이나 사람의 판단은 바꾸지 말고 '무엇을 읽고 어떻게 찾는가'만 고쳐라.
비용(읽는 글자 수 상한 40,000자/공시)을 늘리는 것보다 같은 비용 안에서 더 관련 있는 부분을 읽는 방법을 우선하라. 한국어로 답하라."""
ANALYZE_SCHEMA = {"type": "object", "additionalProperties": False,
                  "required": ["cause", "proposal", "how", "expected_effect", "risk", "cost_impact"],
                  "properties": {k: {"type": "string"} for k in ["cause", "proposal", "how", "expected_effect", "risk", "cost_impact"]}}


def analyze():
    import llm
    rec = json.loads(io.open(P._p("rsi_before.json"), encoding="utf-8").read())
    full = P._docs(F)
    pos = {kw: [m.start() for m in re.finditer(re.escape(kw), full)][:5] for kw in ["H20", "4.5 billion", "excess inventory", "export"]}
    user = (f"[사례] {F['tk']} {F['form']} 접수 {F['accepted']} KST\n[정답 세트] {json.dumps(TRUTH, ensure_ascii=False)}\n"
            f"[현재 규칙] 공시 원문을 HTML에서 글자만 뽑아 앞에서부터 {P.PER_DOC:,}자만 모델에 넣는다(공시당 상한). 8-K는 본문+EX-99 첨부, 10-Q/10-K는 본문만.\n"
            f"[코드가 잰 사실] 원문 전체 {len(full):,}자. 키워드 첫 위치(글자 번째): {json.dumps(pos, ensure_ascii=False)}\n"
            f"[가정 장부]\n{P.LEDGER}\n[실제 판정 결과] {json.dumps(rec.get('cards'), ensure_ascii=False)}\n[채점] {json.dumps(rec['score'], ensure_ascii=False)}\n"
            "왜 놓쳤는지(cause), 무엇을 바꿀지(proposal, 한 문장), 구체적으로 어떻게(how), 기대 효과, 위험, 비용 영향을 써라.")
    out = llm.call("kic", ANALYZE_SYS, user, schema=ANALYZE_SCHEMA, max_tokens=2500, anytime=True)
    use = json.loads(io.open(llm._ledger(), encoding="utf-8").read().strip().splitlines()[-1])
    row = {"cut": "rsi-analyze", "proposal": out, "usd": use["usd"], "tok_in": use["in"], "tok_out": use["out"], "model": use["model"],
           "approved": None}
    row["hash"] = hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    P._add(OUT, row)
    io.open(P._p("rsi_proposal.json"), "w", encoding="utf-8").write(json.dumps(row, ensure_ascii=False))
    print(json.dumps(row, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"before": before, "analyze": analyze}[sys.argv[1]]()
