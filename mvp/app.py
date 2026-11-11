# -*- coding: utf-8 -*-
"""Thesis Fit MVP — 인터뷰 → 설정 초안 → SEC 공시 수집 → 검색·AI 판정 → 출처 대조 → 개인 메모리 → RSI.

  실행:  python app.py            → http://127.0.0.1:8770  (서버 안에서만 열림. 밖에서는 SSH 터널로 본다)
  필요:  requests, anthropic, 그리고 Claude 호출 창구 llm.py (환경 변수 QD_PATH 폴더 또는 ../agent/llm.py)
         SEC는 연락처가 든 User-Agent를 요구한다 → 환경 변수 SEC_USER_AGENT="이름 이메일"

  한 화면에서 도는 흐름
    ① 인터뷰       답변과 '내 투자 근거' 글을 Claude가 읽어 설정 초안(대상·투자 근거·검색어·주기)을 만든다
    ② 수집         SEC EDGAR API로 대상 종목의 새 공시(8-K·10-Q·10-K)를 가져온다 / 시연용 과거 공시 3건
    ③ 검색·판정    원문을 읽을 범위를 고르고(BM25 검색) Claude가 투자 근거별로 판정한다. 지난 의견(개인 메모리)을 함께 준다
    ④ 출처 대조    Claude가 가져온 인용 문장이 원문에 그대로 있는지 프로그램 코드가 확인한다. 판정 기록은 해시로 봉인
    ⑤ RSI          읽지 않은 구간에 근거가 남아 있으면 Claude가 원인을 돌아보고 설정을 스스로 고친 뒤 다시 판정한다

  투자 조언이 아니다. 판정은 '재검토 필요 / 의견 갱신 / 영향 없음' 제안까지만 한다."""
import hashlib
import html
import io
import json
import math
import os
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "agent"))
sys.path.insert(0, os.environ.get("QD_PATH", os.path.expanduser("~/quant_dashboard")))

KST = timezone(timedelta(hours=9))
PORT = int(os.environ.get("TF_PORT", "8770"))
DATA = os.path.join(HERE, "data")
DB = os.path.join(DATA, "memory.db")
UA = {"User-Agent": os.environ.get("SEC_USER_AGENT", "ThesisFit MVP contact@example.com")}
FORMS = ("8-K", "10-Q", "10-K")
CIK = {"NVDA": 1045810, "GOOGL": 1652044, "MSFT": 789019, "AMZN": 1018724, "AVGO": 1730168, "MU": 723125,
       "META": 1326801, "AMD": 2488, "WMT": 104169, "PG": 80424, "KO": 21344}
NAMES = {"NVDA": "NVIDIA", "GOOGL": "Alphabet", "MSFT": "Microsoft", "AMZN": "Amazon", "AVGO": "Broadcom", "MU": "Micron",
         "META": "Meta", "AMD": "AMD", "WMT": "Walmart", "PG": "P&G", "KO": "Coca-Cola"}
DEMO = [  # 시연용 과거 공시(기획서 5쪽 NVIDIA H20 사례) — 접수 시각은 한국 시간
    {"acc": "0001045810-25-000082", "tk": "NVDA", "form": "8-K", "items": "7.01", "accepted": "2025-04-16 06:22"},
    {"acc": "0000002488-25-000039", "tk": "AMD", "form": "8-K", "items": "7.01", "accepted": "2025-04-16 22:03"},
    {"acc": "0001045810-25-000116", "tk": "NVDA", "form": "10-Q", "items": "", "accepted": "2025-05-29 05:32"},
]
BUDGET, FRONT, CHUNK = 40000, 8000, 1200       # 한 공시에서 Claude에게 보내는 글자 상한 / 항상 읽는 앞부분 / 검색 단위
_LOCK = threading.Lock()


def now():
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")


# ── 개인 메모리 (SQLite) ─────────────────────────────────────────────
def db():
    os.makedirs(DATA, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript("""
    create table if not exists profile(id integer primary key, version integer, body text, at text);
    create table if not exists profile_hist(version integer, body text, why text, at text);
    create table if not exists filings(acc text primary key, tk text, form text, items text, accepted text, url text, src text, chars integer);
    create table if not exists opinions(id integer primary key autoincrement, at text, acc text, tk text, form text, thesis_id text,
        action text, summary text, quote text, quote_ok integer, figures text, next text, read_mode text, version integer, hash text);
    create table if not exists runs(id integer primary key autoincrement, at text, kind text, acc text, usd real, sec real, tok_in integer, tok_out integer, note text);
    create table if not exists rsi(id integer primary key autoincrement, at text, acc text, body text);
    create table if not exists feedback(id integer primary key autoincrement, at text, body text);
    create table if not exists last(id integer primary key, body text);
    """)
    return c


def get_profile(c):
    r = c.execute("select * from profile where id=1").fetchone()
    return (json.loads(r["body"]), r["version"]) if r else (None, 0)


def save_profile(c, p, why):
    _, v = get_profile(c)
    v += 1
    body = json.dumps(p, ensure_ascii=False)
    c.execute("insert or replace into profile(id, version, body, at) values(1,?,?,?)", (v, body, now()))
    c.execute("insert into profile_hist values(?,?,?,?)", (v, body, why, now()))
    c.commit()
    return v


# ── Claude 호출 (비용·시간을 개인 메모리에 함께 남긴다) ───────────────
def ask(kind, system, user, schema, acc="", max_tokens=6000):
    import llm
    t0 = time.time()
    out = llm.call("kic", system, user, schema=schema, max_tokens=max_tokens, anytime=True)
    use = json.loads(io.open(llm._ledger(), encoding="utf-8").read().strip().splitlines()[-1])
    sec = round(time.time() - t0, 1)
    with _LOCK:
        c = db()
        c.execute("insert into runs(at, kind, acc, usd, sec, tok_in, tok_out, note) values(?,?,?,?,?,?,?,?)",
                  (now(), kind, acc, use["usd"], sec, use["in"], use["out"], use.get("model", "")))
        c.commit()
    return out, {"usd": use["usd"], "sec": sec, "tok_in": use["in"], "tok_out": use["out"]}


# ── ① 인터뷰 → 설정 초안 ────────────────────────────────────────────
INTERVIEW_SYS = """너는 KIC(한국투자공사) 주식 운용역 한 사람을 위한 '공시 점검 에이전트'의 설정을 짜 주는 AI다.
운용역의 인터뷰 답변과, 운용역이 직접 쓴 '내 투자 근거' 글을 읽고 설정 초안을 만든다.
규칙:
- tickers: 아래 지원 종목 중 운용역의 관심 분야·투자 근거에 맞는 것만 고른다. 지원 종목: """ + ", ".join(f"{k}({v})" for k, v in NAMES.items()) + """
- theses: 운용역의 투자 근거를 3~6개로 정리한다. 운용역이 쓴 뜻을 바꾸지 말고, 글에 없는 근거를 지어내지 마라.
  id는 T1, T2 … / text는 한국어 한 문장 / recheck는 '무엇이 공시에 나오면 다시 봐야 하는지'(한국어, 구체적 조건)
  / mode는 '속보'(급히 알아야 함) 또는 '심층'(아침 리서치에서 보면 됨) / tickers는 그 근거와 관련된 종목.
- keywords: SEC 공시 원문(영어)에서 찾을 영어 검색어 8~15개. 근거의 재검토 조건이 원문에 나타날 때 쓰일 낱말·구(예: 'export license', 'capital expenditures').
- research_time은 'HH:MM', flash_minutes는 속보 확인 주기(분, 정수).
- note: 초안을 만들며 운용역에게 확인받고 싶은 점 한두 문장(한국어). 없으면 빈 문자열.
매매를 권하지 마라."""
PROFILE_SCHEMA = {"type": "object", "additionalProperties": False,
                  "required": ["field", "tickers", "theses", "keywords", "research_time", "flash_minutes", "note"],
                  "properties": {
                      "field": {"type": "string"}, "tickers": {"type": "array", "items": {"type": "string"}},
                      "theses": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                                 "required": ["id", "text", "recheck", "mode", "tickers"],
                                 "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "recheck": {"type": "string"},
                                                "mode": {"type": "string", "enum": ["속보", "심층"]},
                                                "tickers": {"type": "array", "items": {"type": "string"}}}}},
                      "keywords": {"type": "array", "items": {"type": "string"}},
                      "research_time": {"type": "string"}, "flash_minutes": {"type": "integer"}, "note": {"type": "string"}}}


def interview(a):
    user = ("[인터뷰 답변]\n관심 분야와 투자 근거: %s\n심층 리서치를 받을 때: %s\n속보 확인 주기: %s\n\n[운용역이 쓴 내 투자 근거]\n%s"
            % (a.get("field", ""), a.get("when", ""), a.get("flash", ""), (a.get("thesis") or "(첨부 없음)")[:6000]))
    out, use = ask("인터뷰", INTERVIEW_SYS, user, PROFILE_SCHEMA)
    if not out:
        raise RuntimeError("설정 초안을 만들지 못했습니다")
    out["tickers"] = [t for t in out["tickers"] if t in CIK]
    out["read"] = {"mode": "front", "budget": BUDGET}     # 처음엔 '앞에서부터 읽기' — 모자라면 RSI가 고친다
    return {"draft": out, "use": use}


# ── ② 수집 (SEC EDGAR API) ──────────────────────────────────────────
def _acc_dir(cik, acc):
    return "https://www.sec.gov/Archives/edgar/data/%d/%s" % (cik, acc.replace("-", ""))


def collect_live(tickers, per=2):
    """대상 종목마다 최근 공시 per건(8-K·10-Q·10-K)을 submissions API에서 가져온다."""
    c, new = db(), 0
    for tk in tickers:
        r = requests.get("https://data.sec.gov/submissions/CIK%010d.json" % CIK[tk], headers=UA, timeout=20).json()["filings"]["recent"]
        n = 0
        for i, form in enumerate(r["form"]):
            if form not in FORMS:
                continue
            acc = r["accessionNumber"][i]
            t = datetime.strptime(r["acceptanceDateTime"][i][:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).astimezone(KST)
            cur = c.execute("insert or ignore into filings(acc, tk, form, items, accepted, url, src) values(?,?,?,?,?,?,?)",
                            (acc, tk, form, r["items"][i], t.strftime("%Y-%m-%d %H:%M"), _acc_dir(CIK[tk], acc) + "/" + r["primaryDocument"][i], "실시간"))
            new += cur.rowcount
            n += 1
            if n >= per:
                break
        time.sleep(0.25)                                   # SEC 요청 한도(초당 10회)보다 한참 낮게
    c.commit()
    return new


def collect_demo():
    """시연용 과거 공시 3건 — 본문 파일 이름은 공시 폴더 목록(index.json)에서 찾는다."""
    c, new = db(), 0
    for f in DEMO:
        base = _acc_dir(CIK[f["tk"]], f["acc"])
        items = requests.get(base + "/index.json", headers=UA, timeout=20).json()["directory"]["item"]
        main = [x["name"] for x in items if re.match(r"^[a-z]+-\d{8}\.htm$", x["name"])]
        if not main:
            main = [x["name"] for x in items if x["name"].endswith(".htm") and not re.search(r"ex|index|^R\d", x["name"], re.I)]
        cur = c.execute("insert or ignore into filings(acc, tk, form, items, accepted, url, src) values(?,?,?,?,?,?,?)",
                        (f["acc"], f["tk"], f["form"], f["items"], f["accepted"], base + "/" + main[0], "시연"))
        new += cur.rowcount
        time.sleep(0.25)
    c.commit()
    return new


def _clean(url):
    h = requests.get(url, headers=UA, timeout=40).text
    h = re.sub(r"(?is)<ix:header>.*?</ix:header>", " ", h)                  # 숨은 회계 태그
    h = re.sub(r"(?is)<div[^>]*display:\s*none[^>]*>.*?</div>", " ", h)
    h = re.sub(r"(?is)<(script|style).*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def fetch_text(f):
    """공시 원문 글자 — 8-K는 본문 + 첨부 보도자료(EX-99)까지."""
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
            out.append(_clean(u))
            time.sleep(0.25)
        except Exception:
            pass
    return " ".join(out)


# ── ③ 검색: 읽을 범위 고르기 ─────────────────────────────────────────
def _tok(s):
    return re.findall(r"[a-z0-9$%.]+", s.lower())


def bm25_passages(text, keywords, budget=BUDGET, front=FRONT):
    """앞 front자는 항상 읽고, 나머지는 CHUNK자 단위로 잘라 검색어 BM25 점수가 높은 조각부터 budget까지 고른다.
    반환 (Claude에게 줄 글, 고른 구간 [(시작, 끝, 점수)])."""
    rest = text[front:]
    chunks = [(front + i, rest[i:i + CHUNK]) for i in range(0, len(rest), CHUNK)]
    if not chunks:
        return text[:budget], []
    terms = [k.lower().strip() for k in keywords if k.strip()]
    low = [c.lower() for _, c in chunks]
    n, avg = len(chunks), sum(len(x) for x in low) / max(1, len(low))
    score = [0.0] * n
    for t in terms:
        tf = [x.count(t) for x in low]
        df = sum(1 for v in tf if v)
        if not df:
            continue
        idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
        for i, v in enumerate(tf):
            if v:
                score[i] += idf * v * 2.2 / (v + 1.2 * (0.25 + 0.75 * len(low[i]) / avg))
    for i, x in enumerate(low):                             # 금액이 든 조각은 조금 더 쳐 준다(근거가 될 숫자)
        if score[i] and re.search(r"\$\s?\d[\d.,]*\s*(billion|million)", x):
            score[i] *= 1.3
    left, pick = budget - front, []
    for i in sorted(range(n), key=lambda k: score[k], reverse=True):
        if score[i] <= 0 or left < CHUNK:
            break
        pick.append(i)
        left -= len(chunks[i][1])
    pick.sort()
    spans, parts = [], ["[원문 위치 0~%s] %s" % (format(front, ","), text[:front])]
    for i in pick:
        a = chunks[i][0]
        b = a + len(chunks[i][1])
        if spans and a == spans[-1][1]:
            spans[-1][1] = b
            spans[-1][2] = max(spans[-1][2], round(score[i], 2))
        else:
            spans.append([a, b, round(score[i], 2)])
    for a, b, _ in spans:
        parts.append("[원문 위치 %s~%s] %s" % (format(a, ","), format(b, ","), text[a:b]))
    return " ".join(parts), spans


def unread_evidence(text, read_upto, keywords):
    """앞에서부터 read_upto자만 읽었을 때, 읽지 않은 뒤쪽에 '검색어 + 금액'이 함께 나오는 곳을 찾는다 (RSI 발동 조건)."""
    hits = []
    for k in keywords:
        k = k.lower().strip()
        if not k:
            continue
        for m in re.finditer(re.escape(k), text[read_upto:].lower()):
            p = read_upto + m.start()
            near = text[max(read_upto, p - 300):p + 300]
            if re.search(r"\$\s?\d[\d.,]*\s*(billion|million)", near, re.I):
                hits.append({"pos": p, "kw": k})
                break
    return hits


# ── ③ AI 판정 ───────────────────────────────────────────────────────
JUDGE_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["cards"], "properties": {"cards": {
    "type": "array", "items": {"type": "object", "additionalProperties": False,
                               "required": ["thesis_id", "action", "summary", "quote", "figures", "next"],
                               "properties": {"thesis_id": {"type": "string"},
                                              "action": {"type": "string", "enum": ["재검토 필요", "의견 갱신", "영향 없음"]},
                                              "summary": {"type": "string"}, "quote": {"type": "string"},
                                              "figures": {"type": "string"}, "next": {"type": "string"}}}}}}


def judge_system(p):
    rows = "\n".join("| %s | %s | %s | %s |" % (t["id"], t["text"], t["recheck"], t["mode"]) for t in p["theses"])
    return """너는 KIC 주식 운용역 한 사람의 '공시 점검 에이전트'다. 담당 분야: %s.
SEC 공시 원문을 운용역의 투자 근거와 대조해, 공시가 어떤 투자 근거에 걸리는지 판정한다.
규칙:
- 투자 근거를 뒤집거나 매매를 권하지 않는다. 할 일은 '재검토 필요 / 의견 갱신 / 영향 없음' 제안뿐이다.
- 재검토 조건에 실제로 걸릴 때만 '재검토 필요'. 관련은 있지만 조건에 못 미치면 '의견 갱신'. 어느 근거와도 무관하면 thesis_id '-' 로 '영향 없음' 카드 1장만.
- 한 공시가 여러 투자 근거에 걸리면 근거마다 카드를 낸다(최대 3장).
- quote: 원문에서 글자 그대로 복사한 영어 문장 하나(15~60단어). 원문에 없는 문장을 만들지 마라. 근거가 없으면 빈 문자열.
- figures: 금액·비율은 원문 그대로, 단위(million/billion)를 지킨다. 'up to'(예상 상한)와 실제 발생액을 구분해 적는다. 없으면 빈 문자열.
- [개인 메모리]에 같은 투자 근거의 지난 의견이 있으면 이어받아라: 지난 의견의 예상치가 이번 공시에서 실제 값으로 확인됐는지 summary에 밝힌다.
- summary는 한국어 1~2문장, next는 다음에 확인할 것(한국어 한 문장).
- [원문 위치 a~b] 표시는 원문의 어느 구간인지 알려 주는 표지일 뿐이다. 인용에 넣지 마라.
투자 근거 목록:
| ID | 투자 근거 | 다시 볼 조건 | 실행 모드 |
%s""" % (p.get("field", ""), rows)


def norm(s):
    return re.sub(r"[^a-z0-9%$.]+", " ", s.lower()).strip()


def judge_once(c, f, p, version, text, kind):
    mode = p.get("read", {}).get("mode", "front")
    if mode == "search" and len(text) > BUDGET:
        body, spans = bm25_passages(text, p["keywords"])
        read_note = "검색으로 고른 구간 %d곳 + 앞 %s자 (원문 %s자 중 %s자)" % (len(spans), format(FRONT, ","), format(len(text), ","), format(len(body), ","))
    else:
        body, spans = text[:BUDGET], []
        read_note = "앞에서부터 %s자 (원문 %s자)" % (format(min(len(text), BUDGET), ","), format(len(text), ","))
    mem = c.execute("select at, tk, form, thesis_id, action, summary, figures from opinions where thesis_id != '-' and acc != ? order by id desc limit 8", (f["acc"],)).fetchall()
    fb = c.execute("select body from feedback order by id desc limit 3").fetchall()
    memo = "\n".join("- (%s) %s %s → %s [%s] %s %s" % (m["at"][:10], m["tk"], m["form"], m["thesis_id"], m["action"], m["summary"], m["figures"]) for m in mem) or "(지난 의견 없음)"
    if fb:
        memo += "\n운용역 코멘트: " + " / ".join(x["body"] for x in fb)
    user = "[개인 메모리 — 지난 의견]\n%s\n\n[이번 공시] %s %s %s · 접수 %s (한국 시간) · %s\n%s" % (
        memo, f["tk"], NAMES.get(f["tk"], ""), f["form"], f["accepted"], f["acc"], body or "(원문을 받지 못함)")
    out, use = ask(kind, judge_system(p), user, JUDGE_SCHEMA, acc=f["acc"])
    cards = (out or {}).get("cards") or []
    src = norm(text)
    for k in cards:                                         # ④ 출처 대조 — 인용이 원문에 그대로 있는지 코드가 확인
        q = norm(k.get("quote", ""))
        k["quote_ok"] = bool(q) and q in src
    rec = {"acc": f["acc"], "version": version, "read": read_note, "cards": cards, "use": use, "at": now()}
    rec["hash"] = hashlib.sha256(json.dumps(rec, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    with _LOCK:
        for k in cards:
            c.execute("insert into opinions(at, acc, tk, form, thesis_id, action, summary, quote, quote_ok, figures, next, read_mode, version, hash) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                      (rec["at"], f["acc"], f["tk"], f["form"], k["thesis_id"], k["action"], k["summary"], k["quote"], int(k["quote_ok"]),
                       k["figures"], k["next"], mode, version, rec["hash"]))
        c.commit()
    rec["spans"] = spans
    return rec


# ── ⑤ RSI: 스스로 돌아보고 설정을 고친 뒤 다시 판정 ──────────────────
RETRO_SYS = """너는 공시 점검 에이전트의 자기 개선(RSI) 담당이다. 방금 한 판정을 돌아보고, 정보를 놓쳤을 위험이 있으면 '원문을 읽는 방식'을 고친다.
- 투자 근거나 판정 기준은 바꾸지 않는다. 바꿀 수 있는 것은 읽는 방식(read_mode)과 검색어(add_keywords)뿐이다.
- read_mode: 'front' = 앞에서부터 정해진 글자 수만 읽기, 'search' = 앞부분 조금 + 검색어 점수가 높은 구간을 골라 읽기(읽는 양은 같다).
- add_keywords: 이번 공시에서 놓칠 뻔한 내용을 다음에 찾게 해 줄 영어 검색어 0~4개. 이미 있는 검색어는 넣지 마라.
- cause, change, expected는 한국어 한 문장씩. 운용역이 읽고 바로 이해할 쉬운 말로."""
RETRO_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["cause", "read_mode", "add_keywords", "change", "expected"],
                "properties": {"cause": {"type": "string"}, "read_mode": {"type": "string", "enum": ["front", "search"]},
                               "add_keywords": {"type": "array", "items": {"type": "string"}},
                               "change": {"type": "string"}, "expected": {"type": "string"}}}


def run(acc):
    """공시 1건: 판정 → (필요하면) RSI 회고 → 설정 자동 수정 → 재판정."""
    c = db()
    p, version = get_profile(c)
    if not p:
        raise RuntimeError("먼저 인터뷰로 설정을 만들어 주세요")
    f = c.execute("select * from filings where acc=?", (acc,)).fetchone()
    if not f:
        raise RuntimeError("공시를 찾을 수 없습니다")
    f = dict(f)
    text = fetch_text(f)
    c.execute("update filings set chars=? where acc=?", (len(text), acc))
    c.commit()
    first = judge_once(c, f, p, version, text, "판정")
    out = {"first": first, "rsi": None, "second": None, "chars": len(text)}
    miss = unread_evidence(text, BUDGET, p["keywords"]) if p.get("read", {}).get("mode") == "front" and len(text) > BUDGET else []
    if miss:
        note = ("원문은 %s자인데 앞에서부터 %s자만 읽었다. 읽지 않은 뒤쪽에서 검색어와 금액이 함께 나오는 곳: %s.\n"
                "방금 판정: %s\n현재 검색어: %s" % (
                    format(len(text), ","), format(BUDGET, ","),
                    ", ".join("'%s' (원문 %s번째 글자 부근)" % (h["kw"], format(h["pos"], ",")) for h in miss[:6]),
                    json.dumps([{k: v for k, v in x.items() if k in ("thesis_id", "action", "summary", "figures")} for x in first["cards"]], ensure_ascii=False),
                    ", ".join(p["keywords"])))
        retro, use = ask("RSI 회고", RETRO_SYS, note, RETRO_SCHEMA, acc=acc, max_tokens=2000)
        if retro:
            before = dict(p.get("read", {}))
            p["read"] = {"mode": retro["read_mode"], "budget": BUDGET}
            added = [k for k in retro["add_keywords"] if k.lower() not in [x.lower() for x in p["keywords"]]][:4]
            p["keywords"] = p["keywords"] + added
            v2 = save_profile(c, p, "RSI 자동 수정: " + retro["change"])
            second = judge_once(c, f, p, v2, text, "RSI 재판정")
            rsi = {"at": now(), "acc": acc, "tk": f["tk"], "form": f["form"], "unread": miss[:6], "retro": retro, "added": added,
                   "read_before": before, "read_after": p["read"], "version": [version, v2], "use": use,
                   "before": [{k: x[k] for k in ("thesis_id", "action", "figures", "quote_ok")} for x in first["cards"]],
                   "after": [{k: x[k] for k in ("thesis_id", "action", "figures", "quote_ok")} for x in second["cards"]]}
            c.execute("insert into rsi(at, acc, body) values(?,?,?)", (rsi["at"], acc, json.dumps(rsi, ensure_ascii=False)))
            c.commit()
            out.update(rsi=rsi, second=second)
    out.update(tk=f["tk"], form=f["form"], accepted=f["accepted"])
    c.execute("insert or replace into last(id, body) values(1,?)", (json.dumps(out, ensure_ascii=False),))   # 화면을 새로 열어도 마지막 판정이 보이게
    c.commit()
    return out


# ── 화면에 줄 상태 ──────────────────────────────────────────────────
def state():
    c = db()
    p, v = get_profile(c)
    rows = lambda q, *a: [dict(r) for r in c.execute(q, a).fetchall()]
    judged = {r["acc"] for r in c.execute("select distinct acc from opinions")}
    fl = rows("select * from filings order by accepted desc")
    for f in fl:
        f["judged"] = f["acc"] in judged
        f["name"] = NAMES.get(f["tk"], f["tk"])
    cost = c.execute("select coalesce(sum(usd),0) u, count(*) n, coalesce(sum(sec),0) s from runs").fetchone()
    last = c.execute("select body from last where id=1").fetchone()
    return {"profile": p, "version": v, "filings": fl,
            "opinions": rows("select * from opinions order by id desc limit 60"),
            "rsi": [json.loads(r["body"]) for r in c.execute("select body from rsi order by id desc limit 10")],
            "hist": rows("select version, why, at from profile_hist order by version desc limit 10"),
            "runs": rows("select at, kind, acc, usd, sec, tok_in, tok_out from runs order by id desc limit 30"),
            "feedback": rows("select at, body from feedback order by id desc limit 5"),
            "cost": {"usd": round(cost["u"], 4), "calls": cost["n"], "sec": round(cost["s"], 1)},
            "last": json.loads(last["body"]) if last else None, "names": NAMES, "budget": BUDGET}


# ── HTTP ────────────────────────────────────────────────────────────
class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj, ctype="application/json; charset=utf-8"):
        body = obj if isinstance(obj, bytes) else json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, open(os.path.join(HERE, "index.html"), "rb").read(), "text/html; charset=utf-8")
        elif path == "/api/state":
            self._send(200, state())
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0]
        try:
            n = int(self.headers.get("Content-Length") or 0)
            req = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            if path == "/api/interview":
                res = interview(req)
            elif path == "/api/profile":
                p = req["profile"]
                p.setdefault("read", {"mode": "front", "budget": BUDGET})
                res = {"version": save_profile(db(), p, req.get("why") or "운용역이 설정을 확정")}
            elif path == "/api/collect":
                p, _ = get_profile(db())
                res = {"new": collect_demo() if req.get("mode") == "demo" else collect_live((p or {}).get("tickers") or [])}
            elif path == "/api/judge":
                res = run(req["acc"])
            elif path == "/api/feedback":
                c = db()
                c.execute("insert into feedback(at, body) values(?,?)", (now(), str(req.get("text", ""))[:500]))
                c.commit()
                res = {"ok": True}
            elif path == "/api/reset":
                c = db()
                for t in ("profile", "profile_hist", "filings", "opinions", "rsi", "feedback", "last"):      # AI 사용 기록(runs)은 남긴다
                    c.execute("delete from " + t)
                c.commit()
                res = {"ok": True}
            else:
                self._send(404, {"error": "not found"})
                return
            self._send(200, res)
        except Exception as e:
            self._send(200, {"error": "%s: %s" % (type(e).__name__, e)})


if __name__ == "__main__":
    print("Thesis Fit MVP  http://127.0.0.1:%d" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
