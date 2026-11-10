# -*- coding: utf-8 -*-
"""
🧠 Claude API 공용 창구 (2026-11-02, 사용자: Max 플랜 API 크레딧 $100 활용).

  call(tag, system, user, ...) 하나로 모든 기능이 쓴다 — 사용액 장부·월 한도·거절(refusal) 처리를 한곳에서.
  ★키: telegram_config.ANTHROPIC_API_KEY (문서·메모에 적지 않는다). 없으면 Unavailable.
  ★월 한도(MONTH_CAP, 달러): 넘으면 CapReached — 호출하는 쪽이 '판단 없음'으로 처리한다(선물 AI는 신규 진입만 멈추고 손절은 코드가 계속).
  ★SDK: VPS가 Python 3.9라 anthropic 0.x(0.125). effort·구조화 출력·fallbacks는 extra_body로 보낸다.
  장부: 모의투자데이터/AI/usage-YYYYMM.jsonl (호출마다 토큰·달러).
"""
import io
import json
import os
import threading
from datetime import datetime

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "모의투자데이터", "AI")
OPUS, SONNET, HAIKU = "claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5"
PRICE = {  # 달러 / 100만 토큰: (입력, 출력, 캐시 읽기) — 캐시 쓰기는 입력 × 1.25
    OPUS: (4.0, 20.0, 0.20), SONNET: (2.0, 10.0, 0.20), HAIKU: (0.10, 0.50, 0.01),
    "claude-opus-5": (5.0, 25.0, 0.50), "claude-opus-4-8": (5.0, 25.0, 0.50),
}
MONTH_CAP = {"total": 45.0, "fo": 30.0, "tg": 6.0, "cds": 4.0, "dart": 2.0, "weekly": 3.0, "research": 5.0, "kic": 3.0}   # 한 달 상한(달러) — 전체 / 기능별
LIFETIME_CAP = 95.0   # ★절대 상한(달러, 장부 전체 누적) — 사용자 "절대 100불 이상 못 쓰게"(2026-11-02). 장부는 추정치라 $100보다 5 낮게.
#   호출 전에 '이번 호출 최악 비용'(입력 추정 + max_tokens 전부 출력)을 더해 넘으면 호출 자체를 안 한다. 최종 안전장치는 Console 한도.
ONLY_HOST = "quant-a1"  # 장부가 한 곳에만 쌓이게 VPS에서만 호출(PC에서 부르면 Unavailable)
HOURS = ("0900", "1530")  # ★장중에만 호출(사용자 2026-11-02 "장중에만 거래가 가능하니 장중에만 API가 돌게") — 평일 한국 시간, 휴장일은 부르는 쪽이 거른다
_lock = threading.Lock()
_client = None


class Unavailable(Exception):
    pass


class CapReached(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        try:
            from telegram_config import ANTHROPIC_API_KEY
        except Exception:
            ANTHROPIC_API_KEY = ""
        if not ANTHROPIC_API_KEY:
            raise Unavailable("ANTHROPIC_API_KEY 없음")
        import anthropic
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=180.0, max_retries=2)
    return _client


def _ledger():
    return os.path.join(DIR, f"usage-{datetime.now():%Y%m}.jsonl")


def spent_all():
    """장부 전체(모든 달) 누적 달러."""
    tot = 0.0
    try:
        for f in os.listdir(DIR):
            if f.startswith("usage-") and f.endswith(".jsonl"):
                tot += sum(json.loads(x)["usd"] for x in io.open(os.path.join(DIR, f), encoding="utf-8") if x.strip())
    except FileNotFoundError:
        pass
    return round(tot, 4)


def spent(tag=None):
    """이번 달 쓴 돈(달러). tag 주면 그 기능만."""
    try:
        rows = [json.loads(x) for x in io.open(_ledger(), encoding="utf-8") if x.strip()]
    except Exception:
        return 0.0
    return round(sum(r["usd"] for r in rows if tag is None or r["tag"] == tag), 4)


def _cost(model, u):
    pi, po, pc = PRICE.get(model, PRICE[OPUS])
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    return (u.input_tokens * pi + cw * pi * 1.25 + cr * pc + u.output_tokens * po) / 1e6


def call(tag, system, user, model=OPUS, effort="medium", schema=None, max_tokens=16000, tools=None, anytime=False):
    """한 번 묻고 답 받기. schema(JSON Schema)를 주면 dict, 아니면 str. 거절이면 None.
    system은 캐시(5분)에 올린다 — 같은 기능의 반복 호출은 고정 지시문 비용이 약 1/10."""
    import socket
    from datetime import timezone, timedelta
    kst = datetime.now(timezone(timedelta(hours=9)))
    if not anytime and (kst.weekday() >= 5 or not HOURS[0] <= kst.strftime("%H%M") <= HOURS[1]):   # anytime: KIC 공모전 파일럿 07:00 판정만(사용자 2026-11-09 "3번으로 진행", 11/13까지)
        raise Unavailable(f"장중({HOURS[0][:2]}:{HOURS[0][2:]}~{HOURS[1][:2]}:{HOURS[1][2:]} 평일)에만 API 호출")
    if socket.gethostname().split(".")[0] != ONLY_HOST:
        raise Unavailable(f"API 호출은 VPS({ONLY_HOST})에서만 — 장부를 한 곳에 모으기 위해")
    cap = MONTH_CAP.get(tag)
    pi, po, _ = PRICE.get(model, PRICE[OPUS])
    worst = (len(system) + len(user)) / 2 * pi * 1.25 / 1e6 + max_tokens * po / 1e6   # 한글 약 2자/토큰으로 넉넉히
    if tools:
        worst += 0.10 + 60000 * pi / 1e6               # 웹 검색: 검색료 + 결과 본문 입력(넉넉히)
    with _lock:
        if spent_all() + worst >= LIFETIME_CAP:
            raise CapReached(f"절대 상한 ${LIFETIME_CAP:.0f}에 닿음(누적 ${spent_all():.2f} + 이번 최대 ${worst:.2f})")
        if spent() >= MONTH_CAP["total"] or (cap is not None and spent(tag) >= cap):
            raise CapReached(f"{tag} 월 한도 도달(전체 ${spent():.2f} / {tag} ${spent(tag):.2f})")
    c = _get_client()
    oc = {"effort": effort}
    if schema:
        oc["format"] = {"type": "json_schema", "schema": schema}
    extra = {"output_config": oc}
    kw = dict(model=model, max_tokens=max_tokens,
              system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
              messages=[{"role": "user", "content": user}])
    if tools:                                          # 예: 웹 검색 [{"type": "web_search_20260209", "name": "web_search", "max_uses": 4}] — 검색 1천 회당 $10 별도
        kw["tools"] = tools
    if model in (OPUS, SONNET):                        # 안전 분류기 거절 시 서버가 다른 모델로 이어 답한다
        extra["fallbacks"] = "default"
        r = c.beta.messages.create(betas=["server-side-fallback-2026-07-01"], extra_body=extra, **kw)
    else:
        r = c.messages.create(extra_body=extra, **kw)
    usd = _cost(getattr(r, "model", model), r.usage)
    st = getattr(r.usage, "server_tool_use", None)
    usd += (getattr(st, "web_search_requests", 0) or 0) * 0.01 if st else 0   # 웹 검색 1회 $0.01
    os.makedirs(DIR, exist_ok=True)
    with _lock, io.open(_ledger(), "a", encoding="utf-8") as f:
        f.write(json.dumps({"t": datetime.now().strftime("%m-%d %H:%M:%S"), "tag": tag, "model": getattr(r, "model", model),
                            "in": r.usage.input_tokens, "out": r.usage.output_tokens,
                            "cache_r": getattr(r.usage, "cache_read_input_tokens", 0) or 0,
                            "usd": round(usd, 5), "stop": r.stop_reason}, ensure_ascii=False) + "\n")
    if r.stop_reason == "refusal":
        return None
    text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
    if not schema:
        return text
    try:
        return json.loads(text)
    except Exception:
        return None
