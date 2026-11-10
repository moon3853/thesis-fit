# -*- coding: utf-8 -*-
"""
Thesis Guard 파일럿 (2026-11-09 ~ 11-13, VPS) — 기획서 MVP의 SEC 부분만 일주일 돌려 본다.

  poll  : 5분마다(cron). 8개사 SEC 공시(8-K·10-Q·10-K) 새 접수분을 장부에 기록.
          8-K Item 4.02·2.06이면 판정 없이 즉시 텔레그램 경보(빠른 길, 규칙).
  judge : 화~금 07:00 KST(cron). 직전 기준 시각 이후 접수분을 Claude로 가정별 판정(느린 길)
          → 인용문을 원문과 코드로 대조 → 판정 해시 봉인 → 07:30 전에 텔레그램 카드. 토큰·비용 기록.
  report: 주간 요약(공시 수·경보·판정·인용 검증·토큰·비용).

  범위 밖(기획서 확장): GDELT(T0·A4 뉴스), DART(A5), 비교군 A·B·C, 변형 공시 시험.
  Claude 호출은 ~/quant_dashboard/llm.py(장부·한도 공용, tag "kic", anytime=True — 이번 주만 07:00 예외).
"""
import hashlib
import html
import io
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

QD = os.environ.get("QD_PATH", os.path.expanduser("~/quant_dashboard"))   # 시범 운영 때 llm.py 위치(VPS)
sys.path.insert(0, QD)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # 저장소 안의 agent/llm.py

KST = timezone(timedelta(hours=9))
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
START = datetime(2026, 11, 9, 7, 0, tzinfo=KST)   # 첫 묶음 = 11/09 07:00 이후 접수분
END = datetime(2026, 11, 14, 0, 0, tzinfo=KST)    # 이번 주만
UA = {"User-Agent": os.environ.get("SEC_USER_AGENT", "ThesisFit pilot contact@example.com")}   # SEC는 연락처가 든 User-Agent를 요구한다 — 실제 연락처는 환경 변수로
FORMS = ("8-K", "10-Q", "10-K")                    # 8-K/A·Form 4 등은 제외(기획서와 같음)
FAST_ITEMS = ("4.02", "2.06")                      # 즉시 경보: 재무제표 신뢰 불가·중대한 손상
CIK = {"NVDA": 1045810, "GOOGL": 1652044, "MSFT": 789019, "AMZN": 1018724,
       "AVGO": 1730168, "MU": 723125, "META": 1326801, "AMD": 2488}
PER_DOC, TOTAL = 40000, 200000                     # 원문 글자 상한(공시당 / 묶음 전체) — 비용 상한

LEDGER = """| ID | 가정 | 재검토 조건 | 등급 |
| A1 | 하이퍼스케일러 AI 투자가 2027년에도 늘어난다 (GOOGL·MSFT·AMZN·META capex) | 연간 capex 가이던스 하향 또는 '감속' 문구, 분기 capex 전분기 대비 감소 + 가이던스 하향 | 핵심 |
| A2 | 메모리 업황이 기준선 위에 있다 (MU 다음 분기 매출 가이던스 중간값) | 가이던스 중간값이 직전 가이던스·컨센서스 하회, 총이익률 가이던스 하락 | 핵심 |
| A3 | GPU 수요가 공급을 넘는다 (NVDA 데이터센터 매출·가이던스) | 데이터센터 매출 전분기 대비 감소, 가이던스 하향, 수출 규제로 인한 비용·재고 계상 | 핵심 |
| A4 | HBM 해자가 유지된다 | AMD·Broadcom 공시에서 HBM 공급처 변화 언급 | 핵심 |
| B1 | 수출 규제가 실적을 깎지 않는다 | 수출 허가·규제 비용 언급 시 예상 상한과 실제 계상액 분리 기록 | 출근 전 |
| C* | 그 밖의 공시 | 임원 변경·자사주 등 — CEO·CFO 변경만 '출근 전'으로 승격 | 참고 |"""

SYSTEM = """너는 KIC 주식운용역(AI 반도체·메모리 밸류체인 담당)의 '투자 가정 재검토' 에이전트다.
밤사이 SEC 공시 원문을 사용자의 가정 장부와 대조해, 공시마다 어떤 가정에 걸리는지 판정한다.
규칙:
- 가정을 뒤집거나 매매를 권하지 않는다. 할 일은 '재검토 / 카드 갱신 / 알림 없음' 제안뿐이다.
- 재검토 조건에 실제로 걸릴 때만 '재검토'. 관련은 있지만 조건 미충족이면 '카드 갱신', 무관하면 '알림 없음'(가정 C*).
- quote는 원문에서 그대로 복사한 영어 문장(15~60단어) 하나. 원문에 없는 문장을 만들지 마라. 근거가 없으면 빈 문자열.
- 숫자는 원문 그대로 옮기고 단위(million/billion)를 지켜라. 'up to'와 'incurred'처럼 상한과 실제를 구분하라.
- summary는 한국어 1~2문장.
가정 장부:
""" + LEDGER

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["cards"], "properties": {"cards": {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
        "required": ["accession", "assumption", "action", "grade", "summary", "quote"],
        "properties": {"accession": {"type": "string"}, "assumption": {"type": "string"},
                       "action": {"type": "string", "enum": ["재검토", "카드 갱신", "알림 없음"]},
                       "grade": {"type": "string", "enum": ["즉시", "핵심", "출근 전", "참고"]},
                       "summary": {"type": "string"}, "quote": {"type": "string"}}}}}}


def now():
    return datetime.now(KST)


def _p(name):
    return os.path.join(DATA, name)


def _rows(name):
    try:
        return [json.loads(x) for x in io.open(_p(name), encoding="utf-8") if x.strip()]
    except FileNotFoundError:
        return []


def _add(name, row):
    os.makedirs(DATA, exist_ok=True)
    with io.open(_p(name), "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def tg(text):
    try:
        from telegram_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
        for i in range(0, len(text), 3800):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                          data={"chat_id": TELEGRAM_CHAT_ID, "text": text[i:i + 3800], "disable_web_page_preview": "true"}, timeout=15)
    except Exception as e:
        print("tg fail", e)


def _url(cik, acc, doc):
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc.replace('-', '')}/{doc}"


# ── poll ───────────────────────────────────────────────────────────
def poll():
    seen = {r["acc"] for r in _rows("filings.jsonl")}
    for tk, cik in CIK.items():
        try:
            r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=UA, timeout=20).json()["filings"]["recent"]
        except Exception as e:
            print("sec fail", tk, e)
            continue
        for i, form in enumerate(r["form"]):
            acc = r["accessionNumber"][i]
            acc_t = datetime.strptime(r["acceptanceDateTime"][i][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(KST)
            if acc_t < START:
                break                                   # 최신순 — 시작 전이면 그 회사는 끝
            if form not in FORMS or acc in seen:
                continue
            items = r["items"][i]
            row = {"acc": acc, "tk": tk, "cik": cik, "form": form, "items": items,
                   "accepted": acc_t.strftime("%Y-%m-%d %H:%M"), "found": now().strftime("%Y-%m-%d %H:%M"),
                   "url": _url(cik, acc, r["primaryDocument"][i])}
            _add("filings.jsonl", row)
            seen.add(acc)
            hit = [x for x in FAST_ITEMS if x in items.split(",")]
            if form == "8-K" and hit:
                lag = (now() - acc_t).total_seconds() / 60
                tg(f"⚡ Thesis Guard 즉시 경보(파일럿) — {tk} 8-K Item {','.join(hit)}\n"
                   f"접수 {row['accepted']} KST · 감지까지 {lag:.0f}분\n{row['url']}\n(판정 없이 규칙으로 바로 보냄 · 투자 조언 아님)")
                _add("alerts.jsonl", dict(row, lag_min=round(lag, 1)))
        time.sleep(0.3)                                 # SEC 초당 10회 제한보다 한참 낮게


# ── judge ──────────────────────────────────────────────────────────
def _text(url):
    h = requests.get(url, headers=UA, timeout=30).text
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def _docs(f):
    """8-K는 본문 + EX-99(실적 보도자료 등), 나머지는 본문만."""
    urls = [f["url"]]
    if f["form"] == "8-K":
        try:
            base = f["url"].rsplit("/", 1)[0]
            items = requests.get(base + "/index.json", headers=UA, timeout=20).json()["directory"]["item"]
            urls += [base + "/" + x["name"] for x in items if re.search(r"ex-?99", x["name"], re.I) and x["name"].lower().endswith((".htm", ".html"))][:2]
        except Exception:
            pass
    out = []
    for u in urls:
        try:
            out.append(_text(u))
            time.sleep(0.3)
        except Exception:
            pass
    return " ".join(out)


def _norm(s):
    return re.sub(r"[^a-z0-9%$.]+", " ", s.lower()).strip()


def judge():
    cut = now().replace(hour=7, minute=0, second=0, microsecond=0)
    prev = max([datetime.strptime(j["cut"], "%Y-%m-%d %H:%M").replace(tzinfo=KST) for j in _rows("judgments.jsonl")] + [START])
    batch = [f for f in _rows("filings.jsonl") if prev.strftime("%Y-%m-%d %H:%M") <= f["accepted"] < cut.strftime("%Y-%m-%d %H:%M")]
    head = f"🛡️ Thesis Guard 07:00 판정(파일럿) — {prev:%m/%d %H:%M}~{cut:%m/%d %H:%M} 접수 {len(batch)}건"
    rec = {"cut": cut.strftime("%Y-%m-%d %H:%M"), "n": len(batch), "accs": [f["acc"] for f in batch]}
    if not batch:
        rec.update(cards=[], usd=0, tok_in=0, tok_out=0)
        rec["hash"] = hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        _add("judgments.jsonl", rec)
        tg(head + "\n밤사이 감시 대상 공시 없음 → LLM 호출 안 함($0)\n투자 조언 아님")
        return
    msg = _judge(batch, head, rec, "judgments.jsonl")
    if msg:
        tg(msg)


def test(tk):
    """시험: 그 회사의 가장 최근 8-K 한 건으로 같은 판정 과정을 돌린다(텔레그램 안 보냄, test.jsonl에 저장)."""
    cik = CIK[tk]
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=UA, timeout=20).json()["filings"]["recent"]
    i = r["form"].index("8-K")
    acc = r["accessionNumber"][i]
    acc_t = datetime.strptime(r["acceptanceDateTime"][i][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(KST)
    f = {"acc": acc, "tk": tk, "cik": cik, "form": "8-K", "items": r["items"][i], "accepted": acc_t.strftime("%Y-%m-%d %H:%M"),
         "url": _url(cik, acc, r["primaryDocument"][i])}
    print(_judge([f], f"🧪 시험 판정 — {tk} 8-K {f['accepted']} items={f['items']}", {"cut": "test", "n": 1, "accs": [acc]}, "test.jsonl"))


def _judge(batch, head, rec, out_file):
    import llm
    texts, parts, left = {}, [], TOTAL
    for f in batch:
        t = _docs(f)[:min(PER_DOC, max(left, 0))]
        left -= len(t)
        texts[f["acc"]] = t
        parts.append(f"### {f['acc']} | {f['tk']} {f['form']} items={f['items']} 접수 {f['accepted']} KST\n{t or '(원문을 받지 못함)'}")
    t0 = time.time()
    try:
        out = llm.call("kic", SYSTEM, "공시마다 카드 1장씩 판정하라.\n\n" + "\n\n".join(parts),
                       schema=SCHEMA, max_tokens=8000, anytime=True) or {"cards": []}
    except Exception as e:
        return head + f"\n판정 실패: {e}\n투자 조언 아님"
    use = json.loads(io.open(llm._ledger(), encoding="utf-8").read().strip().splitlines()[-1])   # 방금 쓴 한 줄
    cards = out.get("cards") or []
    for c in cards:                                     # 인용문은 코드로 원문 대조(사람 우선 — 사실은 코드가 확인)
        q, src = _norm(c.get("quote", "")), _norm(texts.get(c.get("accession"), ""))
        c["quote_ok"] = bool(q) and q in src
    rec.update(cards=cards, usd=use["usd"], tok_in=use["in"], tok_out=use["out"], sec=round(time.time() - t0, 1))
    rec["hash"] = hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()   # 판정 봉인
    _add(out_file, rec)
    order = {"재검토": 0, "카드 갱신": 1, "알림 없음": 2}
    lines = [head]
    tk = {f["acc"]: f"{f['tk']} {f['form']}" for f in batch}
    for c in sorted(cards, key=lambda c: order.get(c["action"], 3)):
        mark = "✅인용 일치" if c["quote_ok"] else ("⚠️인용 불일치" if c["quote"] else "—근거 없음")
        lines.append(f"\n[{c['action']}·{c['grade']}] {tk.get(c['accession'], c['accession'])} → {c['assumption']}\n{c['summary']}\n{mark}")
    ok = sum(c["quote_ok"] for c in cards if c["quote"])
    lines.append(f"\n인용 검증 {ok}/{sum(1 for c in cards if c['quote'])} · 토큰 입력 {use['in']:,}/출력 {use['out']:,} · ${use['usd']:.3f} · {rec['sec']}초"
                 f"\n봉인 {rec['hash'][:12]} · 투자 조언 아님")
    return "\n".join(lines)


# ── report ─────────────────────────────────────────────────────────
def report():
    fs, al, js = _rows("filings.jsonl"), _rows("alerts.jsonl"), _rows("judgments.jsonl")
    cards = [c for j in js for c in j.get("cards", [])]
    q = [c for c in cards if c.get("quote")]
    by = {}
    for f in fs:
        by[f["tk"]] = by.get(f["tk"], 0) + 1
    night = sum(1 for f in fs if f["accepted"][11:13] >= "22" or f["accepted"][11:13] < "07")
    txt = (f"📊 Thesis Guard 파일럿 주간 요약 ({START:%m/%d}~{now():%m/%d})\n"
           f"공시 {len(fs)}건 ({', '.join(f'{k} {v}' for k, v in sorted(by.items())) or '없음'}) · 밤·새벽 접수 {night}건\n"
           f"즉시 경보 {len(al)}건" + (f" (감지 평균 {sum(a['lag_min'] for a in al) / len(al):.0f}분)" if al else "") + "\n"
           f"판정 {len(js)}회 · 카드 {len(cards)}장 (재검토 {sum(c['action'] == '재검토' for c in cards)}) · 인용 일치 {sum(c['quote_ok'] for c in q)}/{len(q)}\n"
           f"토큰 입력 {sum(j.get('tok_in', 0) for j in js):,} / 출력 {sum(j.get('tok_out', 0) for j in js):,} · 비용 ${sum(j.get('usd', 0) for j in js):.3f}\n투자 조언 아님")
    print(txt)
    return txt


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "poll"
    if mode != "report" and now() >= END:
        sys.exit(0)                                     # 파일럿 종료 — cron이 남아 있어도 아무것도 안 함
    if mode == "report" and len(sys.argv) > 2 and sys.argv[2] == "tg":
        tg(report())
    else:
        {"poll": poll, "judge": judge, "report": report, "test": lambda: test(sys.argv[2])}[mode]()
