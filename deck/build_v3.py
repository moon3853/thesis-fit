# -*- coding: utf-8 -*-
"""KIC 예선 기획서 v3 — 친구 수정본(3장 Truth Social)을 바탕으로 사용자 피드백(2026-11-09) 반영.
  4장 AI 인터뷰형 서비스 · 5장 흐름도 · 6장 Agentic Hybrid RAG + 사람 승인형 RSI · 7장 데이터
  8장 3주 계획(마지막 3일 비교 실험) · 9장 개인화→리서치→매매 확장. 3장은 손대지 않는다.
사용: python build_v3.py 친구수정본.pptx out.pptx"""
import os

_here = os.path.dirname(os.path.abspath(__file__))
_helpers = open(os.path.join(_here, "build_kic.py"), encoding="utf-8").read().split(
    "# ---------------------------------------------------------------- 2. Summary")[0]
exec(_helpers)

GREY_L = RGBColor(0xB7, 0xC3, 0xD3)
GREEN = RGBColor(0x2E, 0x7D, 0x32)
ORANGE_F = RGBColor(0xD9, 0x6C, 0x2C)   # 사람 단계 채움색


def head(sl, title, sub):
    box(sl, 0.85, 1.80, 11.7, 0.48, [(title, {"s": 19, "b": True, "c": NAVY})], m=0.02, anchor="m")
    box(sl, 0.85, 2.26, 11.7, 0.34, [(sub, {"s": 10.5, "c": GREY})], m=0.02, anchor="t")


def set_cell(tbl, r, c, segs, size=11.5):
    tf = tbl.cell(r, c).text_frame
    p0 = tf.paragraphs[0]
    for x in list(p0.runs):
        p0._p.remove(x._r)
    for extra in tf.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    for seg in segs:
        r_ = p0.add_run(); r_.text = seg[0]
        _font(r_, size, seg[1], seg[2] if len(seg) > 2 else INK)
    end = p0._p.find(qn("a:endParaRPr"))
    if end is not None:
        p0._p.remove(end)


def wipe(sl, keep=10):
    """양식 도형(앞 10개: 머리글·장 제목·쪽 번호)만 남기고 내용 도형을 지운다."""
    for sh in list(sl.shapes)[keep:]:
        drop(sh)


def label(sl, x, y, w, text, c=NAVY, s=10):
    box(sl, x, y, w, 0.28, [(text, {"s": s, "b": True, "c": c})], m=0.02, anchor="m")


# ================================================================ 1. 표지 — 서비스명(사용자 2026-11-10: 두 이름을 섞은 3번)
NAME = "공시로 내 투자 근거를 점검하는 개인 맞춤 에이전트"
for _sh in S[0].shapes:
    if not _sh.has_text_frame:
        continue
    _tx = _sh.text_frame.text
    _new = {"공시 기반 투자 가정 재검토 에이전트": NAME,
            "운용역마다 자기 가정으로 설계하는 공시 감시 에이전트": "AI 인터뷰로 운용역마다 맞춰 만드는 AI Agent"}.get(_tx)
    if _new:
        _sh.text_frame.paragraphs[0].runs[0].text = _new

# 팀명(사용자 2026-11-10: Thesis Guard → Thesis Fit, 투자 근거 + 개인 맞춤)
_ct = [sh for sh in S[0].shapes if sh.has_table][0].table
_r = _ct.cell(0, 1).text_frame.paragraphs[0].runs
_r[0].text = "Thesis Fit"
for _x in _r[1:]:
    _x.text = ""

# ================================================================ 2. Summary
s = S[1]
tbl = [sh for sh in s.shapes if sh.has_table][0].table
rows = {
    0: [(NAME, True, NAVY)],
    1: [("KIC 주식 운용역. ", True), ("밤사이 공시·뉴스가 몰려, 출근 전 판단 시각까지 내 투자 근거 기준으로 정리하기 어렵다. KIC 보유 상위 8개사의 최근 1년 공시 136건 중 75%가 한국 시간 밤~새벽(22:00~06:59)에 나왔다.", False)],
    2: [("AI Agent가 운용역을 인터뷰해(관심 분야·판단 시각·경보 주기) 그 사람의 정보 처리 에이전트를 짜 준다. ", True),
        ("에이전트는 공시·뉴스를 모으고, 근거가 부족하면 스스로 다시 검색해 투자 근거별로 '재검토 필요' 여부를 원문 근거와 함께 정리한다. ", False),
        ("RSI(재귀적 자기 개선) + 사람 최종 승인: 놓친 사건은 AI Agent가 원인을 분석해 수정안을 내고, 사람이 승인해야만 반영된다.", True)],
    3: [("데이터  ", True, BLUE), ("MVP는 SEC 미국 공시(수시 공시 8-K, 분기 보고서 10-Q, 연간 보고서 10-K)와 KIC 13F(보유 종목 공시). 확장은 SNS 공개 게시물(X·Truth Social 등, 감지용)·DART(한국 전자공시)·블룸버그 등 기관 계약 피드 — 모두 약관·API 계약 범위 안에서.\n", False),
        ("기술  ", True, BLUE), ("키워드+의미 하이브리드 검색(Agentic Hybrid RAG), 판정·승인 기록을 남기는 내부 DB(SQLite), 모델 교체형.", True)],
    4: [("출근 전에 정리는 끝. 운용역이 판단에만 집중할 수 있게.", True),
        ("\n① 밤사이 몰리는 공시(8종목 기준 75%, 연 102건)를 07:30 전에 정리\n② 약 15만 자 분기 보고서를 약 10초 만에 판정하고 핵심 문장만 인용\n③ 놓친 내용은 RSI로 원인을 고쳐 다시 찾음(백테스트)   ④ 급한 공시는 5분 이내 경보\n⑤ 예상치와 실제치를 구분해 같은 보고서에 이어서 기록", False)],
}
for i, segs in rows.items():
    set_cell(tbl, i, 1, segs, 11.5)

# ================================================================ 4. ② 서비스 제안·차별성 — 인터뷰 장면(레퍼런스: Nature 2026 PHA Fig.1b 구도)
PANEL = RGBColor(0xF3, 0xF5, 0xF8)
MINT = RGBColor(0xDD, 0xEE, 0xE2)
HL = RGBColor(0xFF, 0xF1, 0xC9)        # 결과물 강조(형광펜)


def shp(sl, kind, x, y, w, h, fill=None, line=None, lw=1.0):
    sh = sl.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line; sh.line.width = Pt(lw)
    sh.shadow.inherit = False
    return sh


def person(sl, x, y, sc=1.0, color=ORANGE_F):
    """사람 아이콘: 머리(원) + 어깨(둥근 사각형). (x, y) = 왼쪽 위."""
    shp(sl, MSO_SHAPE.OVAL, x + 0.16 * sc, y, 0.26 * sc, 0.26 * sc, fill=color)
    b = shp(sl, MSO_SHAPE.ROUND_2_SAME_RECTANGLE, x, y + 0.29 * sc, 0.58 * sc, 0.27 * sc, fill=color)
    b.adjustments[0] = 0.5


def robot(sl, x, y, sc=1.0):
    """에이전트 아이콘(레퍼런스의 로봇): 안테나 + 머리 + 눈 + 입 + 귀."""
    shp(sl, MSO_SHAPE.OVAL, x + 0.36 * sc, y, 0.1 * sc, 0.1 * sc, fill=NAVY)
    shp(sl, MSO_SHAPE.RECTANGLE, x + 0.395 * sc, y + 0.09 * sc, 0.03 * sc, 0.12 * sc, fill=NAVY)
    hd = shp(sl, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.08 * sc, y + 0.2 * sc, 0.66 * sc, 0.56 * sc, fill=WHITE, line=NAVY, lw=1.75)
    hd.adjustments[0] = 0.25
    shp(sl, MSO_SHAPE.ROUNDED_RECTANGLE, x + 0.17 * sc, y + 0.3 * sc, 0.48 * sc, 0.3 * sc, fill=MINT)
    for ex in (0.27, 0.47):
        shp(sl, MSO_SHAPE.OVAL, x + ex * sc, y + 0.38 * sc, 0.08 * sc, 0.08 * sc, fill=NAVY)
    shp(sl, MSO_SHAPE.RECTANGLE, x + 0.33 * sc, y + 0.67 * sc, 0.16 * sc, 0.025 * sc, fill=NAVY)
    for ex in (0.0, 0.74):
        shp(sl, MSO_SHAPE.ROUNDED_RECTANGLE, x + ex * sc, y + 0.36 * sc, 0.08 * sc, 0.22 * sc, fill=MINT, line=NAVY, lw=1.0)


def bars(sl, x, y, c=BLUE):
    for k, hh in enumerate((0.12, 0.2, 0.28)):
        shp(sl, MSO_SHAPE.RECTANGLE, x + k * 0.1, y + 0.28 - hh, 0.07, hh, fill=c)


s = S[3]; wipe(s)


def thin_link(x1, y1, x2, y2, color=GREY_L, w=1.5):
    cn = s.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    cn.line.color.rgb = color; cn.line.width = Pt(w)
    te = etree.SubElement(cn.line._get_or_add_ln(), qn("a:tailEnd")); te.set("type", "triangle"); te.set("w", "sm"); te.set("len", "sm")


head(s, "질문에 답하면, 내 업무에 맞춘 에이전트가 만들어진다",
     "운용역은 설계하지 않는다. AI Agent가 인터뷰로 초안을 만들고, 운용역은 고치고 승인만 한다.")
# 패널 배경 + 단계 이름
shp(s, MSO_SHAPE.ROUNDED_RECTANGLE, 0.85, 2.66, 11.7, 2.42, fill=PANEL).adjustments[0] = 0.06
for x_, w_, t_ in ((0.95, 2.45, "① 운용역의 요청"), (3.75, 4.6, "② AI 인터뷰"), (8.7, 3.75, "③ 나만의 에이전트 (초안)")):
    box(s, x_, 2.72, w_, 0.28, [(t_, {"s": 10.5, "b": True, "c": NAVY, "al": PP_ALIGN.CENTER})], m=0.02, anchor="m")
# ① 사람 + 말풍선
person(s, 1.83, 3.08, 1.1)
box(s, 0.98, 3.75, 2.4, 0.26, [("반도체 담당 운용역", {"s": 9, "c": GREY, "al": PP_ALIGN.CENTER})], m=0.02, anchor="m")
bub = box(s, 1.0, 4.08, 2.35, 0.82, [("“출근 전에 내 종목 소식만,\n내 투자 근거 기준으로\n정리해 줘”", {"s": 10, "al": PP_ALIGN.CENTER})],
          fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.06, anchor="m")
thin_link(3.4, 3.87, 3.72, 3.87)
# ② 로봇 + 질문·답 3쌍
robot(s, 3.85, 3.42, 1.0)
box(s, 3.75, 4.3, 1.05, 0.26, [("AI Agent", {"s": 9, "b": True, "c": NAVY, "al": PP_ALIGN.CENTER})], m=0.02, anchor="m")
qa = [("관심 분야와 투자 근거는?", "반도체·AI 인프라 (근거: 빅테크 AI 투자)"),
      ("언제 정리해 드릴까요?", "매일 07:30, 또는 '지금 조사해'"),
      ("급한 소식은 얼마나 자주?", "5분이면 충분, 장중엔 1분")]
for k, (q, a) in enumerate(qa):
    y_ = 3.08 + k * 0.62
    box(s, 4.95, y_, 3.4, 0.27, [[("Q  ", True, BLUE), (q, False)]], fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.08, size=9.5, anchor="m")
    box(s, 5.3, y_ + 0.29, 3.05, 0.27, [[("A  ", True, ORANGE), (a, False)]], fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.08, size=9.5, anchor="m")
thin_link(8.4, 3.87, 8.7, 3.87)
# ③ 결과 카드 (형광펜 강조 = 인터뷰 답이 들어간 자리)
shp(s, MSO_SHAPE.ROUNDED_RECTANGLE, 8.72, 3.05, 3.72, 1.92, fill=WHITE, line=NAVY, lw=1.25).adjustments[0] = 0.06
cfg = [("대상", "NVIDIA·Micron 등 ", "8개사", ""),
       ("검색어", "", "capex·가이던스·수출 규제·HBM", ""),
       ("출처", "SEC 공시 ", "+ SNS·블룸버그", "(확장)"),
       ("정리", "", "매일 07:30", " · 즉시 경보 5분"),
       ("비용", "공시 확인 무료 · AI 판정 ", "건당 $0.04", "")]
paras = []
for k_, a_, h_, z_ in cfg:
    paras.append(([(k_ + "   ", True, BLUE), (a_, False), (h_, True, NAVY), (z_, False, GREY)], {"sa": 3}))
cb = box(s, 8.82, 3.12, 3.55, 1.4, [(a, dict(o, sa=5)) for a, o in paras], m=0.05, size=10)
# 형광펜: 강조 조각에 밑색(하이라이트) 입히기
for p in cb.text_frame.paragraphs:
    for r in p.runs:
        if r.font.bold and r.font.color.rgb == NAVY:
            rPr = r._r.get_or_add_rPr()
            hl = etree.Element(qn("a:highlight"))
            sc_ = etree.SubElement(hl, qn("a:srgbClr")); sc_.set("val", "FFE9A8")
            lat = rPr.find(qn("a:latin"))
            (lat.addprevious(hl) if lat is not None else rPr.append(hl))   # 스키마 순서: highlight는 latin 앞
box(s, 9.55, 4.3, 2.85, 0.2, [("* Claude Opus 5.5 기준, 공시 1건 판정 (2026.11 시범 운영)", {"s": 7.5, "c": GREY})], m=0.0, anchor="m")
person(s, 8.86, 4.6, 0.55)
box(s, 9.25, 4.57, 3.1, 0.34, [[("운용역  ", True, ORANGE), ("[수정] 또는 [승인] → 이때부터 가동", True, NAVY)]], m=0.02, size=9.5, anchor="m")
# 차별성 3개 — 아이콘 + 짧은 문장
dy = 5.2
cards = [("원문으로 확인되는 근거", "AI 답을 원문과 맞춰 보고, 원문에\n없으면 버림 → 할루시네이션 차단"),
         ("묻지 않아도 먼저 움직인다", "챗봇은 물어야 답한다. 에이전트는\n5분마다 스스로 확인, 07:30 정리"),
         ("답만 하면 되는 개인화", "설계는 AI Agent가 인터뷰로,\n결정은 운용역이"),
         ("RSI + 사람 최종 승인", [("놓친 사건 → AI 수정안 →\n🔒 ", False), ("사람이 승인해야만 반영", True, ORANGE)])]
CW4, CG4 = (11.7 - 3 * 0.12) / 4, 0.12
for k, (t_, d_) in enumerate(cards):
    x_ = 0.85 + k * (CW4 + CG4)
    rsi = k == 3
    shp(s, MSO_SHAPE.ROUNDED_RECTANGLE, x_, dy, CW4, 1.12, fill=RGBColor(0xFD, 0xF0, 0xE7) if rsi else TINT2,
        line=ORANGE_F if rsi else None, lw=1.25).adjustments[0] = 0.1
    if k == 0:      # 원문 대조: 문서 + 체크
        shp(s, MSO_SHAPE.FOLDED_CORNER, x_ + 0.14, dy + 0.3, 0.38, 0.48, fill=WHITE, line=GREEN, lw=1.25)
        box(s, x_ + 0.14, dy + 0.36, 0.38, 0.36, [("✓", {"s": 16, "b": True, "c": GREEN, "al": PP_ALIGN.CENTER})], m=0.0, anchor="m")
    elif k == 1:    # 스스로 움직임: 로봇
        robot(s, x_ + 0.08, dy + 0.3, 0.55)
    elif k == 2:
        person(s, x_ + 0.15, dy + 0.34, 0.6, BLUE)
    else:
        shp(s, MSO_SHAPE.CIRCULAR_ARROW, x_ + 0.1, dy + 0.3, 0.5, 0.5, fill=ORANGE_F)
        person(s, x_ + 0.27, dy + 0.45, 0.28, NAVY)
    box(s, x_ + 0.62, dy + 0.08, CW4 - 0.68, 0.96, [(t_, {"s": 10, "b": True, "c": ORANGE if rsi else NAVY, "sa": 3}), (d_, {"s": 8.6})], m=0.02, anchor="m")

# ================================================================ 5. ③ Agent 역할·Workflow — 역할 구간형(사람 / AI Agent / 코드 3줄)
s = S[4]; wipe(s)
head(s, "수집은 프로그램 코드가, 판단은 AI Agent가, 결정은 사람이",
     "프로그램 코드가 AI 토큰 없이 계속 지켜보고, 관련 소식이 있을 때만 AI Agent가 근거를 찾아 판정한다. 마지막 결정은 언제나 사람이 한다.")
ORANGE_T = RGBColor(0xFD, 0xF0, 0xE7)
lanes = [("사람", ORANGE_F, ORANGE_T), ("AI Agent", BLUE, TINT), ("프로그램\n코드", NAVY, PANEL)]
LY, LH = 2.70, 0.64
for k, (nm, c, t) in enumerate(lanes):
    y_ = LY + k * LH
    shp(s, MSO_SHAPE.RECTANGLE, 0.85, y_, 11.7, LH - 0.04, fill=t)
    if k == 0:
        person(s, 0.98, y_ + 0.08, 0.78, c)
    elif k == 1:
        robot(s, 0.93, y_ + 0.04, 0.64)
    else:
        box(s, 0.97, y_ + 0.13, 0.48, 0.34, [("</>", {"s": 10, "b": True, "c": WHITE, "al": PP_ALIGN.CENTER})],
            fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.0, anchor="m")
    box(s, 1.62, y_, 0.62, LH - 0.04, [(nm, {"s": 9.5, "b": True, "c": c})], m=0.0, anchor="m")
steps = [(0, "① 설정", "인터뷰로 근거·주기"),
         (2, "② 수집", "5분마다 새 소식"),
         (2, "③ 선별", "내 키워드 관련만"),
         (1, "④ 근거·판정", "부족하면 다시 검색"),
         (2, "⑤ 검증", "인용·금액 원문 대조"),
         (2, "⑥ 보고", "즉시 또는 07:30"),
         (0, "⑦ 확인", "동의 / 불필요 / 보류")]
PX0, PDX, PW, PH = 2.25, 1.47, 1.36, 0.52
cen = []
for i, (ln_, t_, d_) in enumerate(steps):
    c = lanes[ln_][1]
    x_, y_ = PX0 + i * PDX, LY + ln_ * LH + 0.05
    box(s, x_, y_, PW, PH, [(t_, {"s": 9.5, "b": True, "c": c, "al": PP_ALIGN.CENTER}), (d_, {"s": 8.3, "c": GREY, "al": PP_ALIGN.CENTER})],
        fill=WHITE, line=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.03, anchor="m", lw=1.25)
    cen.append((x_, y_))


def link(x1, y1, x2, y2, color=GREY_L, w=1.25, dash=False, head=True):
    cn = s.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    cn.line.color.rgb = color; cn.line.width = Pt(w)
    ln = cn.line._get_or_add_ln()
    if dash:
        d = etree.SubElement(ln, qn("a:prstDash")); d.set("val", "dash")
    if head:
        te = etree.SubElement(ln, qn("a:tailEnd")); te.set("type", "triangle"); te.set("w", "sm"); te.set("len", "sm")
    return cn


for i in range(6):
    (x1, y1), (x2, y2) = cen[i], cen[i + 1]
    link(x1 + PW, y1 + PH / 2, x2, y2 + PH / 2)
# RSI 띠 + 순환 점선(⑦ → 띠 → ①)
RY = LY + 3 * LH + 0.06
box(s, 0.85, RY, 11.7, 0.42, [], fill=ORANGE_T, line=ORANGE_F, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.25)
box(s, 0.97, RY, 1.25, 0.42, [("↺ RSI", {"s": 10.5, "b": True, "c": ORANGE})], m=0.0, anchor="m")
box(s, 2.25, RY, 10.2, 0.42,
    [[("재귀적 자기 개선 + 사람 최종 승인   ", True, ORANGE),
      ("⑧ AI Agent가 놓친 사건 원인 분석  ·  ⑨ 검색어·출처·주기 수정안  ·  ⑩ 🔒 ", False), ("운용역이 승인해야만 ①에 반영", True, ORANGE), (" (되돌리기 가능)", False, GREY)]],
    m=0.02, size=9, anchor="m")
x7 = cen[6][0] + PW / 2
link(x7, cen[6][1] + PH, x7, RY, ORANGE_F, 1.25, dash=True)
x1_ = cen[0][0] + PW / 2
link(x1_, RY, x1_, cen[0][1] + PH, ORANGE_F, 1.25, dash=True)
# 결과물: 07:30 판정 카드
CY = RY + 0.52
box(s, 0.85, CY, 11.7, 6.36 - CY, [], fill=WHITE, line=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.25)
box(s, 0.97, CY + 0.05, 2.0, 6.26 - CY, [("결과물", {"s": 9, "c": GREY}), ("07:30 판정 보고서", {"s": 10.5, "b": True, "c": NAVY}), ("(예시)", {"s": 8.5, "c": GREY})],
    m=0.02, anchor="m")
col1 = [[("[재검토 필요]  ", True, RGBColor(0xC6, 0x28, 0x28)), ("내 투자 근거 「수출 규제 영향은 제한적」이 ", True, NAVY), ("흔들릴 수 있음", True, RGBColor(0xC6, 0x28, 0x28))],
        [("사건  ", True, BLUE), ("NVIDIA, H20 칩 중국 수출에 허가 필요 (수시 공시 8-K, 04.16 06:22)", False)],
        [("근거  ", True, BLUE), ("\"…up to approximately $5.5 billion of charges…\"  ", False, GREY), ("✓ 원문 일치", True, GREEN)]]
col2 = [[("수치  ", True, BLUE), ("'최대' 55억 달러 예상 — 실제 비용은 아직 미확정", False)],
        [("다음  ", True, BLUE), ("분기 보고서(10-Q)에서 실제 비용 확인", False)],
        [("운용역  ", True, ORANGE), ("[동의]  [불필요]  [보류]", True, NAVY)]]
box(s, 2.95, CY + 0.05, 5.0, 6.26 - CY, [(c_, {"s": 9.5, "sa": 4}) for c_ in col1], m=0.03, anchor="m")
box(s, 8.05, CY + 0.05, 4.4, 6.26 - CY, [(c_, {"s": 9.5, "sa": 4}) for c_ in col2], m=0.03, anchor="m")

# ================================================================ 6. ④ AI 기술·Tool/API — RAG 패널형 + RSI 실제 백테스트(2026-11-09)
s = S[5]; wipe(s)
head(s, "Hybrid RAG로 찾고, RSI로 고치고, API로 넓힌다",
     "보안: MVP는 공개 예시만 외부 모델에 보낸다. 도입 시 사내 모델, 또는 종목·조건만 외부 전송(보유 비중·논지 문구 제외)하고 외부 전송은 모두 기록한다.")
# ① Agentic Hybrid RAG — 패널 + 얇은 연결선
label(s, 0.85, 2.64, 6.2, "① Agentic Hybrid RAG — 어디서, 무엇을 더 찾을지 AI Agent가 정한다")
kp = box(s, 0.85, 3.0, 2.05, 0.66, [("키워드 검색 (BM25)", {"s": 9.5, "b": True, "c": NAVY}), ("정확한 단어: 'H20' · 'Item 4.02'", {"s": 8.2, "c": GREY})],
         fill=WHITE, line=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.08, anchor="m", lw=1.25)
box(s, 0.85, 3.78, 2.05, 0.66, [("의미 검색 (벡터·임베딩)", {"s": 9.5, "b": True, "c": NAVY}), ("'수출 규제' ≈ 'export license'", {"s": 8.2, "c": GREY})],
    fill=WHITE, line=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.08, anchor="m", lw=1.25)
box(s, 3.2, 3.0, 1.85, 1.44, [], fill=PANEL, shape=MSO_SHAPE.ROUNDED_RECTANGLE)
box(s, 3.28, 3.04, 1.7, 0.3, [("순위 결합 (RRF)", {"s": 9.5, "b": True, "c": TEAL, "al": PP_ALIGN.CENTER})], m=0.0, anchor="m")
for k, (rk, tx) in enumerate([("1", "Note 7 · H20 비용"), ("2", "MD&A · 수출 허가"), ("3", "위험 요인")]):
    box(s, 3.32, 3.38 + k * 0.33, 1.62, 0.27, [[(rk + "  ", True, TEAL), (tx, False)]], fill=WHITE, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.06, size=8.2, anchor="m")
box(s, 5.35, 3.0, 1.7, 1.44, [], fill=TINT, line=BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.25)
robot(s, 5.5, 3.08, 0.5)
box(s, 5.95, 3.1, 1.08, 0.4, [("AI Agent\n판단", {"s": 9, "b": True, "c": BLUE})], m=0.0, anchor="m")
box(s, 5.45, 3.58, 1.55, 0.82, [[("충분 ", True, GREEN), ("→ 판정", False)], [("부족 ", True, ORANGE), ("→ 검색어·출처를 바꿔\n다시 검색 (최대 2회)", False)]],
    m=0.02, size=8.2)
link(2.9, 3.33, 3.2, 3.6)
link(2.9, 4.11, 3.2, 3.85)
link(5.05, 3.72, 5.35, 3.72)
# 재검색 순환(점선): AI Agent → 위로 → 검색 패널
link(6.2, 3.0, 6.2, 2.93, BLUE, 1.0, dash=True, head=False)
link(6.2, 2.93, 1.87, 2.93, BLUE, 1.0, dash=True, head=False)
link(1.87, 2.93, 1.87, 3.0, BLUE, 1.0, dash=True, head=True)
# ② RSI — 실제 백테스트
label(s, 7.3, 2.64, 5.25, "② RSI + 🔒 사람 최종 승인 — 실제로 해 본 결과 (2026.11.9)")
box(s, 7.3, 2.9, 5.25, 0.22, [("시험 문제: NVIDIA 분기 보고서(2025.5)에서 'H20 칩 실제 비용 45억 달러'를 찾아낼까?", {"s": 8.3, "c": NAVY})], m=0.02, anchor="m")
rsi = [("① 놓침", "비용 때문에 앞 4만 자만 읽어, 바로 뒤 '45억 달러'를 놓쳤다", NAVY),
       ("② AI Agent 분석", "판단 실수가 아니라, 읽는 범위를 앞에서 자른 게 문제", BLUE),
       ("③ AI Agent 수정안", "읽는 양은 그대로, 중요한 단어 주변만 골라 읽자", BLUE),
       ("④ 🔒 운용역 승인", "승인해야만 적용 + '전체 읽기와도 비교하라' 지시", ORANGE_F)]
for k, (t_, d_, c) in enumerate(rsi):
    y_ = 3.15 + k * 0.34
    box(s, 7.3, y_, 1.5, 0.29, [(t_, {"s": 8.6, "b": True, "c": WHITE, "al": PP_ALIGN.CENTER})], fill=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.02, anchor="m")
    box(s, 8.86, y_, 3.69, 0.29, [(d_, {"s": 8.5})], line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.06, anchor="m")
res = [("원래 방식", "✗ 못 찾음", "$0.10", RGBColor(0xC6, 0x28, 0x28), LINE),
       ("전체 다 읽기", "✓ 찾음", "$0.24", GREEN, LINE),
       ("골라 읽기(수정안)", "✓ 찾음", "$0.07", GREEN, GREEN)]
for k, (t_, r_, c_, rc, ln_) in enumerate(res):
    box(s, 7.3 + k * 1.77, 4.5, 1.69, 0.36, [(t_, {"s": 8.3, "b": True, "c": NAVY, "al": PP_ALIGN.CENTER, "sa": 0}),
                                             ([(r_ + " · ", True, rc), (c_, False, GREY)], {"s": 8.3, "al": PP_ALIGN.CENTER})],
        fill=WHITE, line=ln_, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.01, anchor="m", lw=1.25 if ln_ == GREEN else 0.75)
# ③ 도구·API
label(s, 0.85, 4.86, 6.0, "③ 도구·API")
box(s, 6.9, 4.88, 5.65, 0.24, [("* 위 백테스트 비용은 Claude Opus 5.5 기준 실측 (사례 1건)", {"s": 7.5, "c": GREY, "al": PP_ALIGN.RIGHT})], m=0.0, anchor="m")
rows = [["도구", "하는 일", "언제"],
        ["SEC EDGAR API", "새 공시 목록과 원문 가져오기 (초당 요청 한도 준수)", "5분마다 (장중 1분)"],
        ["하이브리드 검색 (SQLite·임베딩)", "질문에 맞는 원문 문단과 위치 반환", "근거가 부족할 때"],
        ["AI 판정 API (외부·사내 AI 교체형)", "투자 근거별 판정을 정해진 형식(JSON)으로 (외부 AI 또는 사내 AI)", "관련 사건이 있을 때"],
        ["검증기 (프로그램 코드)", "인용 원문 대조·금액 단위 확인·판정 기록 위변조 방지(해시)", "판정 직후"],
        ["외부 데이터 연결 (확장)", "SNS(X 등)·블룸버그·DART를 약관·API 계약 범위에서 연결", "기관 도입 후 필요할 때"]]
table(s, 0.85, 5.12, 11.7, rows, [3.0, 6.2, 2.5], size=8.6, row_h=0.205)

# ================================================================ 7. ⑤ 데이터 — 촘촘하게(사용자: "데이터 칸이니 빡빡하게, 비용 넣어")
s = S[6]; wipe(s)
head(s, "속보는 빠르게, 정확한 팩트는 공시 원문으로 확인",
     "출처마다 역할이 다르다. MVP는 누구나 쓸 수 있는 SEC 공개 데이터로 만들고, 기관이 계약한 피드(예: 블룸버그)는 외부 데이터 연결로 붙여 쓴다.")
MVP_T = RGBColor(0xEA, 0xF5, 0xEC)
rows = [["데이터", "무엇인가", "역할", "확인 주기 · 비용", "단계"],
        ["SEC 공시", "미국 상장사 의무 공시. 8-K = 수시(계약·사고·실적 자료), 10-Q·10-K = 분기·연간 보고서", "사실 확정 · 인용 근거", "5분마다 · 무료", [("MVP", True, GREEN)]],
        ["KIC 13F", "KIC가 분기마다 SEC에 내는 미국 주식 보유 목록", "대상 종목 제안", "분기 1회 · 무료", [("MVP", True, GREEN)]],
        ["투자 근거 목록", "인터뷰로 정한 내 투자 근거와 '무엇이 나오면 다시 볼지'", "판정 기준", "운용역이 바꿀 때", [("MVP", True, GREEN)]],
        ["사람 판정 기록", "사건마다 '이렇게 판정해야 맞다'를 운용역 2명이 따로 적고 맞춰 본 기준", "성능 측정", "실험 전 1회", [("MVP", True, GREEN)]],
        ["SNS 공개 게시물", "X·Truth Social 등 기업·정책 인사의 공개 게시물. 플랫폼 약관·공식 API 계약 범위에서만 수집", "먼저 알아채기 (사실 확정은 공시로)", "API 계약 (예: X 유료)", [("확장", True, GREY)]],
        ["DART · 뉴스(GDELT)", "DART = 한국 전자공시(금융감독원), GDELT = 전 세계 뉴스 목록", "국내·회사 밖 사건 감지", "주기 설정 · 무료", [("확장", True, GREY)]],
        ["블룸버그 등 기관 피드", "KIC가 이미 계약해 쓰는 정보 서비스", "외부 데이터 연결로 사용", "기관 계약", [("확장", True, GREY)]]]
gt7 = table(s, 0.85, 2.7, 11.7, rows, [2.0, 5.2, 2.2, 1.55, 0.75], size=8.5, row_h=0.29, zebra=False)
for i in range(1, len(rows)):
    for j in range(5):
        c_ = gt7.table.cell(i, j); c_.fill.solid(); c_.fill.fore_color.rgb = MVP_T if i <= 4 else PANEL
box(s, 0.85, 5.04, 11.7, 0.22, [[("AI 판정 비용 (실측, Claude Opus 5.5)  ", True, NAVY),
                                 ("수시 공시 1건 약 $0.04 · 분기 보고서 1건 약 $0.07(골라 읽기) ~ $0.24(전체 읽기) — 공시 확인 자체는 무료, AI는 관련 공시가 있을 때만 호출", False, GREY)]],
    m=0.02, size=8, anchor="m")
led = [("예시 ① 반도체 담당 운용역 — 투자 근거 목록",
        [["내 투자 근거", "다시 볼 조건 (예시)", "알림"],
         ["빅테크 4사 AI 투자 지속", "구글·MS·아마존·메타 설비투자 전망 하향", "07:30 정리"],
         ["메모리 업황 양호", "마이크론 매출 전망이 시장 예상 하회", "07:30 정리"],
         ["수출 규제 영향 제한적", "규제 비용 발생 (예상 최대치·실제 비용 구분)", "07:30 정리"]]),
       ("예시 ② 필수소비재 담당 운용역 — 투자 근거 목록",
        [["내 투자 근거", "다시 볼 조건 (예시)", "알림"],
         ["가격 결정력 유지", "P&G 판매량 2분기 연속 감소", "주 1회"],
         ["마진 방어", "월마트 매출총이익률 전망 하락", "주 1회"],
         ["배당 지속", "코카콜라 배당 동결·삭감", "즉시 경보"]])]
for k, (t_, tb) in enumerate(led):
    x_ = 0.85 + k * 5.95
    shp(s, MSO_SHAPE.ROUNDED_RECTANGLE, x_, 5.3, 5.75, 1.06, fill=PANEL).adjustments[0] = 0.08
    person(s, x_ + 0.1, 5.33, 0.36, ORANGE_F)
    box(s, x_ + 0.38, 5.32, 5.3, 0.22, [(t_, {"s": 8.8, "b": True, "c": NAVY})], m=0.0, anchor="m")
    table(s, x_ + 0.08, 5.56, 5.59, tb, [1.75, 2.95, 0.89], size=8, row_h=0.19, head_fill=TEAL, first_col_bold=False)

# ================================================================ 8. ⑥ MVP
s = S[7]; wipe(s)
head(s, "Agent는 이미 가동 중. 본선에서 완성하고 백테스트로 검증한다",
     "수집·AI 판정·인용 검증은 예선 기간 시범 운영으로 이미 돌아가고 있다(2026.11.9~13). 본선 3주는 기능을 통합하고 화면을 만든다. 날짜는 예선 결과 발표에 맞춰 조정한다.")
rows = [["구분", "MVP", "확장 (도입 시)"],
        ["설정", "AI 인터뷰로 개인 맞춤 에이전트 생성", "리서치·리스크관리 업무로 확대"],
        ["수집", "SEC 공시 (8-K·10-Q·10-K)", "SNS·DART·뉴스·블룸버그"],
        ["검색·판정", "하이브리드 검색 · 판정 보고서 · 인용 검증", "소문 판별 · 매체 신뢰도"],
        ["RSI", "놓친 사건 분석 → 수정안 → 🔒 사람 승인", "승인된 개선안을 다른 운용역과 공유"]]
_lt = table(s, 0.85, 2.72, 5.55, rows, [0.95, 2.45, 2.15], size=8.6, row_h=0.45)
_lt.table.rows[0].height = Inches(0.36)   # 머리줄은 오른쪽 표와 같은 높이
rows = [["기간", "만들 것", "완료 기준"],
        ["11/9~11/13 (예선 기간)", "시범 운영 (8개사, 5분마다 확인)\n새 공시가 있으면 07:00 AI 판정", "판정 기록·비용 측정"],
        ["1주 12/03~12/09", "AI 인터뷰 화면과 투자 근거 목록 만들기", "예시 2명 설정 완료\n(반도체·필수소비재)"],
        ["2주 12/10~12/16", "검색 → 판정 → 인용 확인 연결\n+ 급한 소식 즉시 알림", "그림 2 공시 3건\n바르게 판정"],
        ["3주 12/17~12/19", "RSI 루프 (분석 → 수정안 → 승인)", "놓친 사례 재발견\n(11/9 1건 성공)"],
        [[("마지막 3일 12/20~12/22", True, ORANGE)], [[("비교 실험(백테스트): 같은 사건 × 3개 방식", True)], [("키워드 알림 · 일반 AI 챗봇 · 우리 에이전트", False)]], "비교 결과표 · 데모 영상"]]
table(s, 6.6, 2.72, 5.95, rows, [1.75, 2.55, 1.65], size=8.6, row_h=0.36)
box(s, 0.85, 4.98, 11.7, 0.26, [("그림 2. 시연 사례: 2025년 실제 공시(한국 시간)와 에이전트가 내야 할 판정", {"s": 9, "b": True, "c": NAVY})], m=0.02)
tl = [("04.16 06:22", "NVIDIA 8-K (수시 공시)", "H20 관련 비용 '최대' 약 55억 달러 예상", "→ '수출 규제' 투자 근거 재검토 필요"),
      ("04.16 22:03", "AMD 8-K (수시 공시)", "MI308 관련 비용 '최대' 약 8억 달러 예상", "→ AMD 원문 확인 후 같은 투자 근거에 추가"),
      ("05.29 05:32", "NVIDIA 10-Q (분기 보고서)", "H20 실제 비용 45억 달러 확정", "→ 같은 보고서에 실제 금액 기록")]
ln = s.shapes.add_connector(1, Inches(1.0), Inches(5.31), Inches(12.4), Inches(5.31))
ln.line.color.rgb = GREY_L; ln.line.width = Pt(1.5)
for k, (t, f, d, j) in enumerate(tl):
    xx = 0.95 + k * 3.95
    dot = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(xx), Inches(5.24), Inches(0.14), Inches(0.14))
    dot.fill.solid(); dot.fill.fore_color.rgb = NAVY; dot.line.fill.background(); dot.shadow.inherit = False
    box(s, xx, 5.38, 3.8, 0.26, [[(t + "  ", True, BLUE), (f, True, NAVY)]], m=0.02, size=9.3)
    box(s, xx, 5.62, 3.8, 0.46, [(d, {"s": 8.6}), (j, {"s": 8.6, "b": True, "c": GREEN})], m=0.02)
box(s, 0.85, 6.08, 11.7, 0.3,
    [[("실제 작동 확인  ", True, ORANGE), ("시범 운영 중(11/9~13): 8개사 공시 5분마다 확인·매일 07:00 판정(새 공시가 있을 때만 AI 호출). RSI 백테스트(11/9): 놓쳤던 NVIDIA 'H20 비용 45억 달러'를 수정안 승인 후 다시 찾아냄 (6장, 1건).", False)]],
    m=0.02, size=8.5)

# ================================================================ 9. ⑦ 기대효과·확장성 — 고충 → 해결 수치(사용자 2026-11-10)
s = S[8]; wipe(s)
head(s, "출근 전에 정리는 끝. 운용역이 판단에만 집중할 수 있게",
     "출근하면 밤사이 소식이 내 투자 근거별로 정리돼 있고, 급한 일은 이미 알림으로 받았다. 이제 읽는 대신 판단한다.")


def sec(y, t, c):
    shp(s, MSO_SHAPE.RECTANGLE, 0.85, y + 0.04, 0.06, 0.2, fill=c)
    box(s, 0.97, y, 6.0, 0.28, [(t, {"s": 10.5, "b": True, "c": c})], m=0.0, anchor="m")


RED = RGBColor(0xC6, 0x28, 0x28)
RED_T = RGBColor(0xFC, 0xEC, 0xEC)
GRN_T = RGBColor(0xEA, 0xF5, 0xEC)
sec(2.6, "기대효과 — 운용역의 고충을 이렇게 줄인다", BLUE)
box(s, 3.75, 2.6, 3.9, 0.28, [("지금", {"s": 9, "b": True, "c": RED, "al": PP_ALIGN.CENTER})], m=0.0, anchor="m")
box(s, 7.95, 2.6, 4.6, 0.28, [("에이전트 도입 후", {"s": 9, "b": True, "c": GREEN, "al": PP_ALIGN.CENTER})], m=0.0, anchor="m")
pain = [("공시가 밤에 몰린다", "75%", "8종목 공시가 22~07시 접수, 연 102건 (실측)", "07:30 전 정리 완료", "출근하면 판단만 남는다 (목표)"),
        ("보고서가 너무 길다", "약 15만 자", "분기 보고서 1건 · 읽는 데 약 1.5시간 (추정)", "약 10초", "AI가 판정하고 핵심 문장만 인용 (실측, Claude Opus 5.5)"),
        ("중요한 숫자를 놓친다", "45억 달러 누락", "보고서 뒷부분의 실제 비용을 못 봄 (실측)", "같은 실수를 줄인다", "원인을 고쳐 승인 후 다시 찾음 (RSI 백테스트)"),
        ("급한 공시를 늦게 안다", "출근 후 확인", "회계 정정·대규모 손상도 아침에야 안다", "5분 이내 경보", "AI를 거치지 않고 규칙으로 바로 알림 (목표)"),
        ("예상과 실제를 헷갈린다", "예상 55억 · 실제 45억", "다른 공시에 나뉨 (실제 사례)", "따로 구분해 기록", "같은 보고서에 예상 → 실제를 이어서 (8장 그림 2)")]
for k, (t_, a_, ad, b_, bd) in enumerate(pain):
    y_ = 2.9 + k * 0.47
    box(s, 0.85, y_, 2.8, 0.42, [[(f"{k + 1}  ", True, BLUE), (t_, True, NAVY)]], fill=PANEL, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1, size=10.5, anchor="m")
    box(s, 3.75, y_, 3.9, 0.42, [[(a_ + "  ", True, RED), (ad, False, GREY)]], fill=RED_T, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1, size=8.6, anchor="m")
    for r in s.shapes[-1].text_frame.paragraphs[0].runs[:1]:
        r.font.size = Pt(13)
    link(7.65, y_ + 0.21, 7.95, y_ + 0.21, GREY_L, 1.5)
    box(s, 7.95, y_, 4.6, 0.42, [[(b_ + "  ", True, GREEN), (bd, False, GREY)]], fill=GRN_T, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1, size=8.6, anchor="m")
    for r in s.shapes[-1].text_frame.paragraphs[0].runs[:1]:
        r.font.size = Pt(13)
box(s, 0.85, 5.26, 11.7, 0.3,
    [[("조직 차원 효과   ", True, NAVY), ("감사 대응: 판정 기록 봉인(해시)   ·   안전: 사람 최종 승인으로 AI 오판 차단   ·   팀 학습: 한 명이 승인한 RSI 개선안을 팀 전체가 공유", False)]],
    fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1, size=8.6, anchor="m")
sec(5.6, "확장성 — 같은 구조로 더 넓게", TEAL)
stg = [("운용", "MVP → 확대", "담당 50종목이면 연 약 640건(추정) · 다른 운용역에 바로 적용", BLUE),
       ("리서치", "확장", "리포트 근거 숫자를 공시로 자동 갱신 · DART·블룸버그 연결", TEAL),
       ("매매", "확장", "급한 공시 경보를 매매 신호로 · 실행은 사람 승인", NAVY)]
SW, SG = 3.7, 0.3
for k, (t_, tag, d_, c) in enumerate(stg):
    x_ = 0.85 + k * (SW + SG)
    box(s, x_, 5.88, SW, 0.48, [], fill=WHITE, line=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.5)
    box(s, x_ + 0.1, 5.92, 1.55, 0.2, [[(f"{k + 1}  {t_}", True, WHITE), (f"  {tag}", False, WHITE)]],
        fill=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.03, size=8.6, anchor="m")
    box(s, x_ + 0.1, 6.12, SW - 0.2, 0.22, [(d_, {"s": 8.2})], m=0.02, anchor="m")
    if k < 2:
        link(x_ + SW, 6.12, x_ + SW + SG, 6.12, GREY_L, 1.5)

# ================================================================ 10. ⑧ 부록 — 출처 성격별·계산 근거·AI 활용(2026-11-10 재작성)
s = S[9]; wipe(s)
rows = [["구분", "출처", "쓰인 곳"],
        ["KIC 업무", "KIC 투자 프로세스·직무기술서 (kic.kr)", "운용역 업무 이해"],
        ["학술 논문", "Lesmy·Muchnik·Mugerman (2025) Lost in the fog · Dechow·Ge·Loh (2026) Beyond earnings quality, Review of Accounting Studies", "3장 배경"],
        ["검색 기법", "BM25 (Robertson·Zaragoza 2009) · RRF (Cormack 외 2009)", "6장 Hybrid RAG"],
        ["선행 연구·서비스", "AlphaSense 워크플로 에이전트 · AgenticThesis · Fin-RATE · FinFIRST · LiveNewsBench · BlindToChange", "비교·평가 설계"],
        ["공개 데이터", "SEC 13F: Korea Investment Corp (CIK 1441689, 2026-08-12 공시) · SEC EDGAR submissions (접수 시각, 2026-11-08 수집)", "3장 그림, 대상 종목"],
        ["시연 공시", "NVIDIA 8-K (0001045810-25-000082) · AMD 8-K (0000002488-25-000039) · NVIDIA 10-Q (0001045810-25-000116)", "5·6·8장"],
        ["그림", "Truth Social 원문 (Axios 캡처) · S&P 500 장중 흐름 (Google Finance, Finbold 인용)", "3장"],
        ["이용 약관", "SEC EDGAR 접근 정책 (초당 10회 이하 요청) · X 개발자 약관·API 계약", "2·6·7장 수집"]]
table(s, 0.85, 1.86, 11.7, rows, [1.6, 8.3, 1.8], size=8.2, row_h=0.22)
box(s, 0.85, 4.1, 11.7, 0.26, [("계산 근거 — 숫자는 실측·추정·목표를 구분해 표시했다", {"s": 9.5, "b": True, "c": NAVY})], m=0.02, anchor="m")
calc = [["숫자 (쓰인 곳)", "근거", "구분"],
        ["밤사이 공시 75%·연 102건 (2·3·9장)", "8개사 최근 1년 공시 136건 중 한국 시간 22:00~06:59 접수 102건 (팀 직접 집계)", "실측"],
        ["공시 1건 판정 약 10초 (2·9장)", "2026.11.9 시범 운영·백테스트 판정 8~12초, Claude Opus 5.5", "실측"],
        ["RSI 백테스트 (6·8·9장)", "NVIDIA 10-Q를 현재 규칙·전체 읽기·수정안으로 각각 판정, 판정 기록은 해시로 봉인 보관 (2026.11.9, 1건)", "실측"],
        ["읽는 데 약 1.5시간 (9장)", "분기 보고서 본문 146,294자 ≈ 약 2만 3천 단어 ÷ 분당 250단어 ≈ 90분", "추정"],
        ["담당 50종목이면 연 약 640건 (9장)", "8종목 102건 ÷ 8 × 50종목 ≈ 638건", "추정"]]
table(s, 0.85, 4.38, 11.7, calc, [2.7, 8.2, 0.8], size=8.2, row_h=0.22, head_fill=TEAL)
box(s, 0.85, 5.82, 11.7, 0.54,
    [[("AI 활용  ", True, NAVY), ("시스템 판정 모델: Claude Opus 5.5 (시범 운영·백테스트, 다른 모델로 교체 가능) / 기획서 작성 보조: OpenAI Codex(선행연구 정리·초안), Anthropic Claude(자료 조사·공시 시각 집계·원문 대조·초안 보완)", False)],
     [("데이터  ", True, NAVY), ("공개 자료와 자체 구성한 예시만 사용. 시연 투자 근거는 설명용.   ", False), ("✓ 민감정보·개인정보·API Key 미포함", True, TEAL)]],
    fill=TINT2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1, size=8.4, anchor="m")

# 3장(친구 수정본) — 용어 통일만: "투자 가정" → "투자 근거" (사용자 2026-11-10)
for _sh in S[2].shapes:
    if _sh.has_text_frame:
        for _pp in _sh.text_frame.paragraphs:
            for _r in _pp.runs:
                if "투자 가정" in _r.text:
                    _r.text = _r.text.replace("투자 가정", "투자 근거")
                if "·인플루언서가" in _r.text:                   # 사용자 2026-11-10: 인플루언서 문구 빼기(조사도 맞춤)
                    _r.text = _r.text.replace("·인플루언서가", "이")
                if "야간 접수" in _r.text:                       # 사용자 2026-11-10: '야간 접수' → '야간'
                    _r.text = _r.text.replace("야간 접수", "야간")

prs.save(OUT)
print("saved", OUT)
