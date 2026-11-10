# Thesis Fit — 공시로 내 투자 근거를 점검하는 개인 맞춤 에이전트

국부펀드 KIC, AI 에이전트 공모전 예선 출품작 (팀 Thesis Fit: 문성원 · 김건우)

> 출근 전에 정리는 끝. 운용역이 판단에만 집중할 수 있게.

밤사이 몰리는 미국 공시(SEC 8-K·10-Q·10-K)를 운용역 개인의 **투자 근거 목록** 기준으로 정리하는 AI Agent입니다.
수집은 프로그램 코드가, 판단은 AI Agent가, 결정은 사람이 합니다.

- 기획서: [`deck/KIC_최종기획서_ThesisFit.pdf`](deck/KIC_최종기획서_ThesisFit.pdf) (10쪽)
- 텍스트판: [`docs/최종기획서_ThesisFit.md`](docs/최종기획서_ThesisFit.md)

## 폴더 구성

| 폴더 | 내용 |
|---|---|
| `agent/` | 시범 운영 코드. `thesis_guard_pilot.py`(공시 수집 · 즉시 경보 · AI 판정 · 인용 원문 대조 · 판정 기록 해시 봉인 · 주간 요약), `llm.py`(Claude API 공용 창구: 사용 장부·월/누적 비용 상한·운영 시간 제한) |
| `backtest/` | RSI(재귀적 자기 개선) 백테스트. `rsi_bt.py`(현재 규칙 판정 → AI Agent 원인 분석·수정안), `rsi_after.py`(사람 승인 후 전체 읽기 vs 수정안 재판정) |
| `results/` | 실제 실행 기록. `rsi_bt.jsonl`(백테스트 판정·수정안·승인 기록, 각 줄 해시 봉인), `test.jsonl`(시험 판정 1건) |
| `deck/` | 기획서 PDF·PPTX와 생성 스크립트(`build_v3.py`, `build_kic.py` 공용 도우미) |
| `docs/` | 진행 기록(한계·기각 사항), 숫자 근거(재료집), 데이터 이용 조건 점검 |

## 시범 운영 (2026-11-09 ~ 11-13)

```
*/5 * * * *   python thesis_guard_pilot.py poll       # SEC 8개사 새 공시 확인, 8-K 4.02·2.06은 규칙으로 즉시 경보
0 22 * * 1-4  python thesis_guard_pilot.py judge      # 매일 07:00 KST AI 판정 (서버 시계 UTC)
10 22 * * 4   python thesis_guard_pilot.py report tg  # 금요일 주간 요약
python thesis_guard_pilot.py test NVDA                # 최근 8-K 1건으로 시험 판정
```

- 대상: KIC 13F 보유 상위 8개사(NVIDIA·Alphabet·Microsoft·Amazon·Broadcom·Micron·Meta·AMD)
- 판정 모델: Claude Opus 5.5 (`llm.py`에서 교체 가능)
- 시험 판정 1건: NVIDIA 8-K, 인용 원문 일치, 12초, 약 $0.04

## RSI 백테스트 결과 (2026-11-09, 사례 1건)

NVIDIA 10-Q(2025-05-29) 본문 146,294자 중 'H20 실제 비용 45억 달러'는 42,271번째 글자에 있어, 앞 40,000자만 읽는 원래 규칙은 놓칩니다.

| 방식 | 결과 | 비용 |
|---|---|---|
| 원래 규칙(앞 4만 자) | ✗ 못 찾음 | $0.098 |
| 전체 다 읽기 | ✓ 찾음 | $0.238 |
| 골라 읽기(AI Agent 수정안, 사람 승인 후 적용) | ✓ 찾음 | $0.072 |

사례가 1건뿐이라 일반화할 수 없습니다. 한계는 `docs/진행기록_한계와_기각사항.md` 8장에 정리했습니다.

## 실행 준비

```bash
pip install requests anthropic python-pptx
```

- `telegram_config.example.py`를 `telegram_config.py`로 복사해 키를 넣습니다(이 파일은 커밋하지 않습니다).
- SEC는 연락처가 든 User-Agent를 요구합니다: 환경 변수 `SEC_USER_AGENT="이름 이메일"`을 설정하세요.
- `llm.py`는 비용 사고를 막기 위해 특정 서버 이름(`ONLY_HOST`)과 운영 시간에서만 호출하도록 막혀 있습니다. 다른 환경에서는 이 값을 바꿔야 합니다.

## 데이터와 보안

- MVP는 누구나 쓸 수 있는 SEC 공개 데이터만 씁니다. SNS·블룸버그 등은 약관·API 계약 범위 안에서만 확장합니다.
- 키·토큰·개인정보는 저장소에 넣지 않습니다.
