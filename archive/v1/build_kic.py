# -*- coding: utf-8 -*-
"""KIC 공모전 예선 기획서 — 제공 양식(form.pptx)에 내용을 채운다."""
import sys
import copy
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree

SRC, OUT = sys.argv[1], sys.argv[2]
FONT = "Malgun Gothic"
NAVY = RGBColor(0x0E, 0x28, 0x41)
BLUE = RGBColor(0x2F, 0x73, 0xE8)
TEAL = RGBColor(0x15, 0x60, 0x82)
INK = RGBColor(0x22, 0x22, 0x22)
GREY = RGBColor(0x5A, 0x5A, 0x5A)
TINT = RGBColor(0xEE, 0xF4, 0xFD)
TINT2 = RGBColor(0xF4, 0xF6, 0xF8)
ORANGE = RGBColor(0xC8, 0x5A, 0x1E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xC9, 0xD3, 0xE0)

prs = Presentation(SRC)
S = list(prs.slides)


def _font(run, size, bold=False, color=INK, italic=False):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.italic = italic
    f.color.rgb = color
    f.name = FONT
    rPr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rPr.find(qn(tag))
        if el is None:
            el = etree.SubElement(rPr, qn(tag))
        el.set("typeface", FONT)


def _bullet(p, on, level=0):
    pPr = p._p.get_or_add_pPr()
    for t in ("a:buNone", "a:buChar", "a:buAutoNum"):
        for e in pPr.findall(qn(t)):
            pPr.remove(e)
    if on:
        ind = 140000 + level * 140000
        pPr.set("marL", str(ind))
        pPr.set("indent", str(-130000))
        bu = etree.SubElement(pPr, qn("a:buChar"))
        bu.set("char", "•" if level == 0 else "–")
    else:
        pPr.set("marL", "0")
        pPr.set("indent", "0")
        etree.SubElement(pPr, qn("a:buNone"))


def fill_tf(tf, paras, size=10.5, color=INK, align=None, space=2):
    """paras: list of str | (segments, opts). segments = str or [(text, bold, color?)]."""
    tf.word_wrap = True
    first = True
    for item in paras:
        if isinstance(item, tuple):
            segs, o = item
        else:
            segs, o = item, {}
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        if isinstance(segs, str):
            segs = [(segs, o.get("b", False))]
        for seg in segs:
            t, b = seg[0], seg[1]
            c = seg[2] if len(seg) > 2 else o.get("c", color)
            r = p.add_run()
            r.text = t
            _font(r, o.get("s", size), b, c, o.get("i", False))
        _bullet(p, o.get("bul", False), o.get("lv", 0))
        p.space_after = Pt(o.get("sa", space))
        p.alignment = o.get("al") or align or PP_ALIGN.LEFT


def box(sl, x, y, w, h, paras, fill=None, line=None, size=10.5, color=INK, anchor="t",
        shape=MSO_SHAPE.RECTANGLE, m=0.08, align=None, name=None, lw=0.75):
    sh = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        sh.name = name
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = 0.08
    if fill is None:
        sh.fill.background()
    else:
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
    if line is None:
        sh.line.fill.background()
    else:
        sh.line.color.rgb = line
        sh.line.width = Pt(lw)
    sh.shadow.inherit = False
    tf = sh.text_frame
    tf.margin_left = tf.margin_right = Inches(m)
    tf.margin_top = tf.margin_bottom = Inches(m * 0.7)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    fill_tf(tf, paras, size=size, color=color, align=align)
    return sh


def arrow(sl, x, y, w, h, color=BLUE):
    sh = sl.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def down(sl, x, y, w, h, color=BLUE):
    sh = sl.shapes.add_shape(MSO_SHAPE.DOWN_ARROW, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.fill.solid()
    sh.fill.fore_color.rgb = color
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def table(sl, x, y, w, rows, cols_w, size=9.5, head_fill=NAVY, row_h=0.3, first_col_bold=True, zebra=True):
    nr, nc = len(rows), len(rows[0])
    gf = sl.shapes.add_table(nr, nc, Inches(x), Inches(y), Inches(w), Inches(row_h * nr))
    tbl = gf.table
    tot = sum(cols_w)
    for j, cw in enumerate(cols_w):
        tbl.columns[j].width = Emu(int(Inches(w) * cw / tot))
    for i in range(nr):
        tbl.rows[i].height = Inches(row_h)
        for j in range(nc):
            c = tbl.cell(i, j)
            c.margin_left = c.margin_right = Inches(0.06)
            c.margin_top = c.margin_bottom = Inches(0.03)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            val = rows[i][j]
            tf = c.text_frame
            tf.paragraphs[0].text = ""
            if i == 0:
                c.fill.solid(); c.fill.fore_color.rgb = head_fill
                fill_tf(tf, [(val, {"b": True, "c": WHITE})], size=size)
            else:
                c.fill.solid()
                c.fill.fore_color.rgb = TINT2 if (zebra and i % 2 == 0) else WHITE
                if isinstance(val, list) and val and isinstance(val[0], tuple):
                    paras = [val]          # 한 문단 안의 여러 서식 조각
                else:
                    paras = val if isinstance(val, list) else [val]
                if j == 0 and first_col_bold:
                    paras = [(p, {"b": True, "c": NAVY}) if isinstance(p, str) else p for p in paras]
                fill_tf(tf, paras, size=size, space=0)
    # 표 스타일 무늬 끄기
    tblPr = tbl._tbl.tblPr
    tblPr.set("bandRow", "0")
    return gf


def drop(sh):
    sh._element.getparent().remove(sh._element)


def clear_guide(sl):
    for sh in list(sl.shapes):
        if sh.has_text_frame and sh.text_frame.text.startswith("[작성방법]"):
            drop(sh)


def src(sl, text, y=6.62):
    box(sl, 0.62, y, 12.18, 0.3, [(text, {"s": 7.5, "c": GREY})], m=0.02)


# ---------------------------------------------------------------- 2. Summary
s = S[1]
tbl = [sh for sh in s.shapes if sh.has_table][0].table
summary = [
    [("Thesis Sentinel (논지 파수꾼)", True, NAVY)],
    None, None, None, None,
]
cells = {
    0: [[("Thesis Sentinel (논지 파수꾼)", True, NAVY), (" — 운용역의 투자 논지를 밤새 감시하고, 급변 시 원인을 판독하며, 그 판단을 기록·채점하는 AI Agent", False)]],
    1: [[("KIC 운용역·투자위원회. ", True), ("투자부문 123명이 2,320억 달러(1인당 약 19억 달러)를 운용하고, 해외 시장은 서울의 밤에 움직인다. 인력 이탈로 ‘왜 샀고 무엇을 보면 파는가’라는 논지가 사람과 함께 사라지고, 공공기관으로서 판단 근거의 설명 책임이 크다.", False)]],
    2: [[("감시(밤) → 판독(아침) → 기억(D+10·D+20). ", True), ("논지에 걸리는 사건만 골라 원인을 4가지로 분류하고, 과거 유사 사건 통계를 직접 실행해 근거로 붙인다. 운용역 판단을 먼저 받고 에이전트 판정을 공개하며, 둘 다 사전 등록한 규칙으로 채점한다. ", False),
         ("차별점: ", True), ("① 판단을 결과 전에 봉인·채점 ② 숫자는 도구 실행값만 사용 ③ 사람 판단을 대체하지 않고 측정·강화", False)]],
    3: [[("KIC 공개 13F(SEC EDGAR)·시세·실적일·SEC 공시·FRED 거시·뉴스 메타데이터. ", False), ("교체형 LLM + 도구 호출 오케스트레이터, ", True),
         ("논지 장부(구조화 Memory) + 공시 문서 RAG, 이벤트 스터디 실행 도구, 인용·숫자 검증기", False)]],
    4: [[("아침 점검 수작업 약 2시간 → 15분 검토(목표치), 판단·근거의 감사 기록 자동화, 담당자가 바뀌어도 논지·판단 이력 인수인계. ", False),
         ("확장: ", True), ("위탁운용사 모니터링 · 총자산(TPA) 리스크 브리핑 · 타 기관(연기금·증권사 PB)", False)]],
}
for i in range(5):
    c = tbl.cell(i, 1)
    tf = c.text_frame
    p0 = tf.paragraphs[0]
    for r in list(p0.runs):
        p0._p.remove(r._r)
    for extra in tf.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)
    for seg in cells[i][0]:
        r = p0.add_run(); r.text = seg[0]
        _font(r, 11.5, seg[1], seg[2] if len(seg) > 2 else INK)
    end = p0._p.find(qn("a:endParaRPr"))
    if end is not None:
        p0._p.remove(end)

# ---------------------------------------------------------------- 3. 문제 정의
s = S[2]; clear_guide(s)
X, Y = 0.85, 1.88
# 왼쪽: 숫자
stats = [("123명", "KIC 투자부문 인력(2026.6)"), ("2,320억 달러", "총 운용자산(2025년 말)"), ("≈ 19억 달러", "투자인력 1인당 운용 규모(추정)")]
for k, (n, lab) in enumerate(stats):
    yy = Y + k * 1.0
    box(s, X, yy, 3.15, 0.9, [(n, {"s": 22, "b": True, "c": BLUE}), (lab, {"s": 9.5, "c": GREY})],
        fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.14, anchor="m", name=f"stat{k}")
box(s, X, Y + 3.0, 3.15, 0.86,
    [("해외 선례", {"s": 9.5, "b": True, "c": NAVY}),
     ("노르웨이 국부펀드(NBIM)는 AI로 신규 편입 기업의 위험을 24시간 안에 자동 표시한다(2026.2 보도). KIC는 1인당 규모가 더 크지만 이런 상시 감시 도구가 없다.", {"s": 8.5})],
    fill=TINT2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.12)
# 오른쪽: 문제 3개
probs = [
    ("P1  밤의 공백", "보유 자산 대부분이 해외 — 미국·유럽 장은 서울의 밤에 움직인다. 아침마다 운용역이 뉴스·리포트·시세를 수작업으로 모아 ‘무슨 일이 있었고 내 논지에 영향이 있나’를 정리한다. 커버할 시장은 넓고 인원은 적다."),
    ("P2  논지의 유실", "‘왜 샀고, 무엇을 보면 판다’는 투자 논지와 판단 근거가 메일·메모·사람의 머릿속에 흩어져 있다. 투자운용 인력 퇴직률 11.0%(2022), 기본급 정체·지방 이전 논란으로 이탈 압력이 커지며, 사람이 떠나면 논지도 함께 사라진다."),
    ("P3  검증되지 않는 판단", "급락 때의 판단(‘일시적이다/논지가 깨졌다’)이 결과와 대조되지 않는다. 무엇이 맞았는지 모르니 판단력이 쌓이지 않고, 국회·감사에 판단 근거를 설명할 기록도 부족하다."),
]
for k, (t, d) in enumerate(probs):
    yy = Y + k * 1.06
    box(s, 4.25, yy, 8.3, 0.96, [(t, {"s": 11.5, "b": True, "c": NAVY}), (d, {"s": 9.5})],
        line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.13, name=f"prob{k}")
box(s, 4.25, Y + 3.2, 8.3, 0.66,
    [[("주요 사용자 ", True, BLUE), ("1차 운용역(주식·대체 담당)  ·  2차 투자위원회·리스크관리  ·  3차 신규·인수 담당자(인수인계)", False)],
     [("활용 시나리오 ", True, BLUE), ("KIC 보유 종목이 미국장에서 −9% 급락한 다음 날 08:00 — 원인·논지 영향·대응안을 1시간 안에 보고해야 한다.", False)]],
    fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.13, size=9.5)
src(s, "출처: KIC 2025 연차보고서 · MTN(2026.10.12) 투자부문 인력·기본급 · 정일영 의원실 국감 자료(퇴직률) · CNBC(2026.2.26) NBIM — 1인당 규모는 총자산÷투자부문 인원으로 계산한 추정치")

# ---------------------------------------------------------------- 4. 서비스 제안·차별성
s = S[3]; clear_guide(s)
steps = [("① 논지 등록", "운용역: 종목·논지·\n감시 조건 입력"), ("② 밤사이 감시", "시세·공시·뉴스 중\n논지 관련 사건만 선별"),
         ("③ 판독 브리핑", "07:30 원인 분류·\n통계 근거·대응 선택지"), ("④ 운용역 판단", "10초 입력 후\n에이전트 판정 공개"),
         ("⑤ 자동 채점", "D+10·D+20 결과 대조\n→ 성적표·논지 갱신")]
bw, gap = 2.05, 0.36
for k, (t, d) in enumerate(steps):
    xx = 0.85 + k * (bw + gap)
    box(s, xx, 1.9, bw, 0.95, [(t, {"s": 11, "b": True, "c": WHITE, "al": PP_ALIGN.CENTER}),
                               (d, {"s": 8.5, "c": WHITE, "al": PP_ALIGN.CENTER})],
        fill=NAVY if k != 3 else BLUE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, anchor="m", m=0.06, name=f"step{k}")
    if k < 4:
        arrow(s, xx + bw + 0.06, 2.27, 0.24, 0.22)
# 핵심 기능 3
feats = [
    ("감시 — 논지에 걸리는 것만", "밤사이 수천 건의 사건 중 등록된 논지·감시 조건(예: ‘하이퍼스케일러 capex 하향’, ‘종가 −7%’)에 걸리는 것만 골라 확인한다. 걸리는 게 없으면 ‘이상 없음’ 한 줄로 끝난다."),
    ("판독 — 원인을 분류하고 숫자로", "급변의 원인을 A 논지 훼손 / B 공포 전염 / C 수급·기계적 / D 금리·매크로로 분류하고 5개 검증 질문에 근거를 붙인다. ‘과거 비슷한 급락 뒤 20일’ 통계는 코드를 직접 실행해 얻는다."),
    ("기억 — 판단을 봉인하고 채점", "판정과 운용역 판단을 결과가 나오기 전에 해시로 봉인해 논지 장부에 남기고, 사전 등록한 규칙으로 D+10·D+20에 채점한다. 담당자가 바뀌어도 논지와 판단 이력이 남는다."),
]
for k, (t, d) in enumerate(feats):
    xx = 0.85 + k * 3.95
    box(s, xx, 3.05, 3.75, 1.12, [(t, {"s": 10.5, "b": True, "c": NAVY}), (d, {"s": 8.8})],
        fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.13, name=f"feat{k}")
rows = [["", "일반 리서치 챗봇", "상용 리서치 도구", "Thesis Sentinel"],
        ["작동 방식", "질문하면 답한다(1회성)", "문서 검색·요약", [("매일 스스로 감시 → 판독 → 기록", True, TEAL)]],
        ["숫자의 근거", "모델이 생성(환각 위험)", "문서 인용", [("도구 실행값만 · 숫자마다 호출 번호 태그", True, TEAL)]],
        ["사람의 판단", "AI 답을 그대로 수용", "해당 없음", [("운용역이 먼저 판단 → 둘 다 채점(인지적 항복 방지)", True, TEAL)]],
        ["사후 검증", "없음", "없음", [("결과 전 봉인 → D+10·D+20 자동 채점·확신도 보정", True, TEAL)]]]
table(s, 0.85, 4.35, 11.7, rows, [1.3, 2.6, 2.4, 5.4], size=9.5, row_h=0.37)

# ---------------------------------------------------------------- 5. Agent 역할·Workflow
s = S[4]; clear_guide(s)
flow = [
    ("1 계획", "Orchestrator", "논지 장부에서 오늘의 감시 대상·조건을 읽고 작업 목록을 만든다"),
    ("2 탐색", "Watcher", "시세·공시·뉴스 도구 호출 → 사건별 논지 관련도 판정  ▶ 관련 없음이면 ‘이상 없음’으로 종료"),
    ("3 판독", "Analyst", "트리거 충족 사건의 원인을 A~D로 분류 · 5개 검증 질문(사실/추측, 이익 추정치, 가격 지표, 매도 주체, 과도성)"),
    ("4 통계", "Quant", "유사 사건 이벤트 스터디 실행(무작위 날짜 기준선 포함) → 수치 근거 생성"),
    ("5 검증", "Verifier", "숫자 태그·인용 원문 대조·반대 근거 탐색  ▶ 실패 시 재작성(최대 2회) → 그래도 실패면 ‘판정 보류’"),
    ("6 기록", "Scribe", "운용역 판단 입력 대기 → 판정 봉인(해시) → D+10·D+20 채점 일정 등록 → 성적표 갱신"),
]
for k, (n, who, d) in enumerate(flow):
    yy = 1.88 + k * 0.62
    box(s, 0.85, yy, 1.05, 0.52, [(n, {"s": 10.5, "b": True, "c": WHITE, "al": PP_ALIGN.CENTER})],
        fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, anchor="m", m=0.03)
    box(s, 1.98, yy, 1.32, 0.52, [(who, {"s": 9.5, "b": True, "c": BLUE, "al": PP_ALIGN.CENTER})],
        fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, anchor="m", m=0.03)
    box(s, 3.38, yy, 4.6, 0.52, [(d, {"s": 8.8})], line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, anchor="m", m=0.1)
# 오른쪽: 권한 표 + 종료 조건
rows = [["에이전트가 스스로", "코드가 막는 것", "사람이 하는 것"],
        [["감시 대상 선별", "도구 선택·호출 순서", "원인 분류·확신도", "통계 설계·실행", "브리핑 작성·재작성"],
         ["매매·주문 도구 없음", "미확인 속보 배제", "태그 없는 숫자 삭제", "기준 시각 이후 차단", "하루 비용·시간 상한"],
         ["논지 등록·수정", "판단 입력(선택)", "판정 보류 건 검토", "최종 의사결정", "채점 규칙 승인"]]]
gf = table(s, 8.2, 1.88, 4.35, rows, [1, 1, 1], size=8.5, row_h=0.32, first_col_bold=False, zebra=False)
gf.table.rows[1].height = Inches(1.3)
for j in range(3):
    tf = gf.table.cell(1, j).text_frame
    for p in tf.paragraphs:
        _bullet(p, True)
    gf.table.cell(1, j).vertical_anchor = MSO_ANCHOR.TOP
box(s, 8.2, 3.68, 4.35, 1.72,
    [("종료 조건", {"s": 10.5, "b": True, "c": NAVY}),
     ("감시 대상 사건 없음 → ‘이상 없음’ 보고", {"s": 9.2, "bul": True}),
     ("판정 + 검증 통과 + 봉인 완료 → 정상 종료", {"s": 9.2, "bul": True}),
     ("검증 2회 실패 → ‘판정 보류’로 사람에게 이관", {"s": 9.2, "bul": True}),
     ("비용·시간 상한 도달 → 수집분까지 보고 후 중단", {"s": 9.2, "bul": True}),
     ("같은 입력 3회 판정이 갈리면 확신도 하향·검토 요청", {"s": 9.2, "bul": True})],
    fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.13)
box(s, 8.2, 5.52, 4.35, 0.62,
    [[("우선순위 규칙 ", True, ORANGE), ("사전 등록한 ‘즉시 경보’ 조건(예: 지정학 봉쇄 확인)은 판독을 건너뛰고 바로 사람에게 알린다.", False)]],
    line=ORANGE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1, size=8.5)

# ---------------------------------------------------------------- 6. AI 기술·Tool/API
s = S[5]; clear_guide(s)
stack = [
    ("모델", "교체형 어댑터 — 선별은 경량 LLM, 판독·검증은 고성능 LLM. 설정 한 줄로 사내 모델로 교체"),
    ("Framework", "Python 자체 오케스트레이터(상태 머신 + 도구 호출). 단계·재시도·비용 상한을 코드로 강제"),
    ("Memory", "논지 장부(DB): 논지·감시 조건·판정·운용역 판단·채점 결과·해시. 전날 판단을 이어받는 근거"),
    ("RAG·검색", "SEC 공시·IR 문서를 단락 단위로 색인 → 검색 결과는 문서·위치와 함께 반환"),
]
for k, (t, d) in enumerate(stack):
    yy = 1.88 + k * 0.66
    box(s, 0.85, yy, 1.15, 0.57, [(t, {"s": 10, "b": True, "c": WHITE, "al": PP_ALIGN.CENTER})],
        fill=NAVY, shape=MSO_SHAPE.ROUNDED_RECTANGLE, anchor="m", m=0.03)
    box(s, 2.06, yy, 3.15, 0.57, [(d, {"s": 8.5})], fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, anchor="m", m=0.08)
rows = [["Tool", "역할", "입력 → 출력", "호출 조건"],
        ["get_prices", "시세·지수·환율", "티커·기간·as_of → 일봉", "감시 시작·판독·통계"],
        ["get_filings", "SEC 공시 원문", "기업·유형 → 단락+위치", "8-K 등 신규 공시 감지"],
        ["get_13f", "KIC 보유 내역", "분기 → 종목·수량", "분기 공시·논지 등록"],
        ["get_macro", "금리·VIX·달러", "지표·기간 → 시계열", "원인 D 후보일 때"],
        ["search_news", "뉴스 메타데이터", "키워드·시각 → 제목·링크", "밤사이 감시·속보 확인"],
        ["run_event_study", "유사 사건 통계", "조건·기간 → 분포·p값", "판독 시 항상"],
        ["ledger", "논지 장부 읽기·쓰기", "논지 ID → 이력 / 판정 봉인", "계획·기록 단계"],
        ["verify", "숫자·인용 검증", "브리핑 → 통과/삭제 목록", "출력 직전 항상"]]
table(s, 5.42, 1.88, 7.13, rows, [1.35, 1.35, 2.2, 1.9], size=8.3, row_h=0.285)
box(s, 0.85, 4.6, 11.7, 0.32, [("신뢰성 확보 — 환각·오류를 막는 6겹", {"s": 10.5, "b": True, "c": NAVY})], m=0.02)
layers = [("① 숫자 태그", "모든 숫자에 생성한 도구 호출 ID — 없으면 문장 삭제"),
          ("② 인용 대조", "인용문이 가져온 원문에 실제로 있는지 코드로 확인"),
          ("③ 주장-근거 표", "근거 칸이 빈 주장은 결론에 사용 금지"),
          ("④ 검증 에이전트", "다른 지시문으로 반대 근거를 찾고 결론 재검토"),
          ("⑤ 확인 대기", "1차 출처 2곳 미확인 속보는 판정 근거 제외"),
          ("⑥ 재시도·예외", "도구 실패 2회 재시도 → ‘데이터 없음’ 명시")]
for k, (t, d) in enumerate(layers):
    xx = 0.85 + k * 1.97
    box(s, xx, 4.95, 1.86, 0.98, [(t, {"s": 9.5, "b": True, "c": BLUE}), (d, {"s": 8.6})],
        line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.1)

# ---------------------------------------------------------------- 7. 데이터
s = S[6]; clear_guide(s)
rows = [["데이터", "출처", "수집·갱신", "전처리", "활용 목적", "이용 조건"],
        ["KIC 보유 내역(13F)", "SEC EDGAR (CIK 1441689)", "분기(최근 2026-08-12)", "CUSIP→티커 매핑, 비중 계산", "데모 포트폴리오·논지 대상", "공개 공시"],
        ["시세·지수·환율", "공개 시세 API", "일 1회 + 감시 시 수시", "수정주가, 거래일 정렬", "급변 감지·통계", "이용 조건 확인, 필요 시 대체 출처"],
        ["기업 공시(10-K·10-Q·8-K)", "SEC EDGAR API", "수시(신규 공시 감지)", "단락 분할·색인, 위치 보존", "원인 판독·인용 근거", "공개 공시"],
        ["실적 발표일·EPS", "기업 IR · SEC 공시", "분기", "발표 시각→반응일 계산", "실적 이벤트 통계", "공개 자료"],
        ["거시(금리·VIX·달러)", "FRED (미 세인트루이스 연준)", "일 1회", "결측 보정, 거래일 정렬", "원인 D(매크로) 판정", "공개, 출처 표기"],
        ["뉴스", "GDELT · 언론사 RSS", "15분", "제목·링크·시각만 저장(본문 미저장)", "밤사이 사건 선별", "메타데이터만 사용"],
        ["논지 장부·판단 기록", "운용역 입력(내부)", "수시", "구조화(논지·조건·판정·해시)", "기억·채점·인수인계", "내부 전용"]]
table(s, 0.85, 1.88, 11.7, rows, [1.75, 1.85, 1.6, 2.2, 1.9, 1.75], size=8.5, row_h=0.36)
gov = [("시점 고정(as_of)", "모든 조회에 기준 시각을 강제 — 과거 재현 때 그 시점 이후 데이터는 도구가 돌려주지 않는다(사후 지식 차단)."),
       ("데이터 3등급", "공개(외부 모델 전송 가능) · 내부(논지 장부, 요약만 전송) · 민감(비공개 포지션, 사내 모델만). 외부 전송은 전부 로그로 남긴다."),
       ("실제 도입 시", "13F 대신 KIC 내부 포트폴리오·리서치 문서로 교체. 13F는 미국 상장 주식만·분기 말 45일 지연이라는 한계를 데모에서 명시한다.")]
for k, (t, d) in enumerate(gov):
    xx = 0.85 + k * 3.95
    box(s, xx, 4.92, 3.75, 1.0, [(t, {"s": 10, "b": True, "c": NAVY}), (d, {"s": 8.8})],
        fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.13)

# ---------------------------------------------------------------- 8. MVP
s = S[7]; clear_guide(s)
scope = [("반드시(Must)", NAVY, "논지 장부 · 밤사이 감시 · 판독 브리핑 · 이벤트 스터디 도구 · 검증기 · 봉인·자동 채점 · 근거 추적 웹 화면"),
         ("되면(Should)", BLUE, "익명화한 과거 급변 재현 성적표 · 운용역 10초 입력 · 반대 논리 점검 · 주간 판단 성적표"),
         ("이번엔 안 함(Won't)", GREY, "위탁운용사 모니터링 · TPA 리스크 · 증권사 확장 · 매매 실행(설계상 제외)")]
for k, (t, c, d) in enumerate(scope):
    xx = 0.85 + k * 3.95
    box(s, xx, 1.88, 3.75, 0.82, [(t, {"s": 10, "b": True, "c": c}), (d, {"s": 8.5})],
        line=c, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.11, lw=1)
rows = [["기간", "구현", "완료 기준"],
        ["예선 기간 (11/12~12/2)", "봉인 기록 선행 시작(13F 상위 5종목)", "매일 판정·해시 커밋 — 본선 마감 시 약 30거래일 실전 기록"],
        ["1주차 (12/3~12/9)", "데이터 도구 · 논지 장부 · as_of 차단", "5종목 데이터 수집·조회 테스트 통과"],
        ["2주차 (12/10~12/16)", "감시·판독 흐름 · 검증기 · 채점 규칙", "샘플 급락 3건 브리핑 생성, 검증 통과율 측정"],
        ["3주차 (12/17~12/22)", "웹 화면 · 성적표 · 발표·시연 영상", "데모 URL 공개, GitHub 실행 가이드 완료"]]
table(s, 0.85, 2.85, 6.6, rows, [1.55, 2.6, 2.75], size=8.3, row_h=0.42)
box(s, 0.85, 5.05, 6.6, 1.17,
    [("기술 스택  ", {"s": 9.5, "b": True, "c": NAVY}),
     ("Python · FastAPI · SQLite/PostgreSQL · pandas/numpy · 교체형 LLM API · 웹 화면(React) · GitHub(봉인 기록)", {"s": 8.5}),
     ("데모 시나리오  ", {"s": 9.5, "b": True, "c": NAVY}),
     ("‘KIC 보유 종목이 밤사이 급락’ → 07:30 브리핑 → 운용역 판단 입력 → 문장 클릭 시 출처·원본 데이터 → 봉인 기록과 실전 성적표 공개", {"s": 8.5})],
    fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.12)
rows = [["주요 리스크", "대응"],
        ["사후 지식 오염(모델이 결말을 앎)", "실전 봉인 기록을 주 성적으로 · 재현은 익명화·as_of · 결말을 아는 사건 제외 · 원인 분류만 채점"],
        ["판독이 틀림", "정확도를 약속하지 않음 · 3자 비교(에이전트·운용역·단순 기준) · 확신도 보정 공개"],
        ["환각", "6겹 검증(④ 기술 참조) · 판정 보류 허용"],
        ["비용·지연", "경량/고성능 모델 분리 · 사건 걸린 날만 판독 · 하루 상한 코드 강제"],
        ["데이터 이용 조건", "공식·공개 출처 우선 · 뉴스 본문 미저장 · 출처 부록 기재"]]
table(s, 7.6, 2.85, 4.95, rows, [1.6, 3.35], size=8.2, row_h=0.56)

# ---------------------------------------------------------------- 9. 기대효과·확장성
s = S[8]; clear_guide(s)
rows = [["구분", "현재", "도입 후(목표)"],
        ["시간", "밤사이 사건 확인·아침 정리 수작업(약 2시간, 가정)", [("15분 검토 · 걸리는 사건 없으면 1줄 보고", True, TEAL)]],
        ["커버리지", "담당자가 직접 보는 범위로 제한", [("등록된 모든 논지를 매일 빠짐없이 감시", True, TEAL)]],
        ["품질", "근거가 메일·메모에 흩어짐", [("브리핑 모든 문장에 출처·원본 연결", True, TEAL)]],
        ["신뢰성", "판단과 결과를 대조하지 않음", [("모든 판단 사전 봉인 · D+10·D+20 자동 채점", True, TEAL)]],
        ["조직 기억", "담당자 이탈 시 논지 유실", [("논지·판단·적중률이 장부에 남아 인수인계", True, TEAL)]],
        ["설명 책임", "사후에 근거를 재구성", [("판단 시점의 근거·수정 이력이 감사 기록으로", True, TEAL)]]]
table(s, 0.85, 1.88, 6.85, rows, [1.1, 2.75, 3.0], size=8.8, row_h=0.47)
box(s, 0.85, 5.3, 6.85, 0.7,
    [[("측정 방법 ", True, BLUE), ("시간·커버리지는 본선 데모에서 실측해 보고하고, 신뢰성은 봉인 기록의 실전 성적(적중률·확신도 보정)으로 제시한다. 위 ‘현재’ 시간은 가정이며 KIC 실무 확인이 필요하다.", False)]],
    fill=TINT2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.12, size=8.5)
road = [("1단계 · MVP", "KIC 공개 13F 상위 5종목 · 미국 주식 · 공개 데이터 · 실전 봉인 기록"),
        ("2단계 · KIC 내부 적용", "전 자산군(채권·대체 포함) · 사내 모델 어댑터 · 투자위원회 문서 연동 · 운용역별 판단 성적표"),
        ("3단계 · 확장", "위탁운용사 모니터링(13F·핵심 인력·스타일 이탈) · 총자산(TPA) 리스크 브리핑 · 연기금·증권사 PB")]
for k, (t, d) in enumerate(road):
    yy = 1.88 + k * 1.0
    box(s, 7.95, yy, 4.6, 0.86, [(t, {"s": 10.5, "b": True, "c": WHITE}), (d, {"s": 8.6, "c": WHITE})],
        fill=[NAVY, TEAL, BLUE][k], shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.13)
    if k < 2:
        down(s, 10.1, yy + 0.87, 0.3, 0.12)
box(s, 7.95, 4.95, 4.6, 1.05,
    [("운영 적용 경로", {"s": 10, "b": True, "c": NAVY}),
     ("데이터 3등급 + 외부 전송 로그로 보안 심사 대응", {"s": 8.5, "bul": True}),
     ("모델 어댑터로 사내 모델(온프레미스) 전환", {"s": 8.5, "bul": True}),
     ("매매 권한 없는 ‘조언·기록’ 도구 — 도입 부담 최소", {"s": 8.5, "bul": True})],
    fill=TINT, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.12)

# ---------------------------------------------------------------- 10. 부록
s = S[9]; clear_guide(s)
rows = [["구분", "이름", "출처 / 링크", "이용 조건", "활용 범위"],
        ["데이터", "KIC 13F · 기업 공시", "SEC EDGAR (sec.gov)", "공개 공시", "보유 내역·공시 근거"],
        ["데이터", "거시 지표", "FRED (fred.stlouisfed.org)", "공개, 출처 표기", "금리·VIX·달러"],
        ["데이터", "시세", "공개 시세 API (본선 전 확정)", "이용 조건 확인 후 사용", "급변 감지·통계"],
        ["데이터", "뉴스 메타데이터", "GDELT · 언론사 RSS", "제목·링크만", "사건 선별"],
        ["모델/API", "LLM (본선 전 확정)", "상용 LLM API — 교체형", "각 사 약관 준수", "선별·판독·검증"],
        ["오픈소스", "pandas · numpy · FastAPI 등", "PyPI", "각 라이선스(BSD·MIT 등)", "데이터 처리·서버"],
        ["참고자료", "KIC 2025 연차보고서 · 언론 보도", "kic.kr · MTN · CNBC · 국회 국감 자료", "인용·출처 표기", "문제 정의 근거"],
        ["생성형 AI", "Claude (Anthropic)", "claude.ai", "약관 준수", "자료 조사·기획서 초안 작성 보조"],
        ["사전 검증", "팀 개인 프로토타입", "2026.8~11 개인 운영", "본선 코드는 신규 작성", "개념 검증(판독·채점 구조)"]]
table(s, 0.85, 1.88, 11.7, rows, [1.1, 2.3, 3.2, 2.3, 2.8], size=8.6, row_h=0.36)
box(s, 0.85, 5.6, 11.7, 0.6,
    [("주요 참고: KIC 2025 연차보고서(주요 투자성과) · MTN ‘운용역 2배 늘린 KIC…핵심인력 민간行’(2026.10.12) · CNBC ‘Norway’s sovereign wealth fund uses Claude to screen investments’(2026.2.26) · 2026 국정감사 재정경제기획위원회 보도", {"s": 8.3}),
     ("✓ 본 기획서에는 민감정보·개인정보·API Key가 포함되지 않았습니다.", {"s": 8.5, "b": True, "c": TEAL})],
    fill=TINT2, shape=MSO_SHAPE.ROUNDED_RECTANGLE, m=0.12)

prs.save(OUT)
print("saved", OUT)
