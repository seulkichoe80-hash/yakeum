# D팀 전달용 결함 재현 사례 (B 작성)

B의 공통 NormalizationResult를 D 통합 코드(`reconcile_normalization_results`)에 넣었을 때 팀 설계 의도와 어긋나 보이는 4가지 사례다.
D 코드·공통 계약은 수정하지 않았고, 아래 결과는 **임시 폴더에 D 브랜치를 풀어 읽기 전용으로 실행한 값**이다.

- 실행 대상 D 코드: `origin/codex/b-d-c-integration` (`4680470`) — `engine.py`는 `codex/b-to-d-integration`과 동일(해시 일치)
- 입력: `cases.json` (가상 Excel → B 파이프라인, 가상 ID·가상 약품만. 개인정보 없음)
- 재현 방법(D 브랜치 체크아웃 상태, 저장소 루트): `python backend/services/normalization/d_repro/run_on_d_branch.py`
- 입력 다시 만들기(B 브랜치): `python -m backend.services.normalization.d_repro.build_cases`
- "기대"는 **B가 이해한 설계 의도**이며 D의 공식 계약이 아니다. 아래 R3·R4는 결함이라기보다 의미 확인 요청이다.

## 관찰 결과
| 사례 | 입력 요약 | D 결과 (실행 확인) | 기대(설계 의도) |
| --- | --- | --- | --- |
| **R1** 한 시점에 같은 약 2줄 | 이전: 타이레놀 1줄(02-05) / 현재: 같은 약 2줄(05-05, 06-05) | `NEEDS_CONFIRMATION`(이전 1건) + `NEW` 2건 | 계속 복용 중인 약은 `MAINTAINED` 또는 대표 1건 비교 |
| **R2** 양쪽 모두 2줄 | 이전 2줄 / 현재 2줄 | `NEEDS_CONFIRMATION` 2건 + `NEW` 2건 | 같은 약 반복 조제는 같은 약으로 비교 |
| **R3** UNMATCHED + 성분 없음 | 약품코드만 동일, 성분·함량 모두 모름 | `MAINTAINED` / `SAME_INGREDIENT_SAME_STRENGTH` | 성분·함량을 확인할 수 없으므로 "동일 성분·동일 함량" 사유로 확정하지 않음 |
| **R4** 함량 null | 성분명은 있으나 `product_strength=null`, 투약량 동일 | `MAINTAINED` / `SAME_INGREDIENT_SAME_STRENGTH` | 함량을 모르면 "같은 함량" 사유를 붙이지 않음 |

## 원인 (D 코드 읽기 기준)
- R1·R2: `_find_unique_best_match`가 동률 후보(같은 `mfds_product_id` 2건)면 "모호하다"며 매칭하지 않는다. 추측하지 않는 설계는 안전하지만, 반복 조제는 B가 삭제하지 않으므로(팀장 결정) 한 시점에 같은 식별자가 여러 번 나온다.
- R3·R4: 값이 한쪽이라도 `null`이면 "비교 불가 = 변화 없음"으로 처리하고 `MAINTAINED`의 사유 코드가 고정이라, 성분·함량을 모르는 기록도 `SAME_INGREDIENT_SAME_STRENGTH`가 된다.

## 영향
- R1·R2: 이어서 복용 중인 약이 "최신 자료에서 확인되지 않음 + 신규"로 표시되어 사용자에게 혼란을 줄 수 있다(복용 중단을 뜻하지는 않음).
- R3·R4: 사유 코드가 실제 확인 수준보다 강해 보인다. 의료적 판단은 아니지만 "확인됨"으로 오해될 수 있다.

## D·팀장께 요청하는 결정
1. 한 시점 내 같은 약 반복 조제를 비교하는 규칙(대표 기록 선택, 그룹 비교) — B는 `repeat_report.find_repeat_groups`로 반복 그룹을 알려 줄 수 있음(기록은 변경하지 않음).
2. 성분 또는 함량이 `null`일 때 `MAINTAINED`에 붙일 `reason_code`/표시 방식(공통 계약 사항).
