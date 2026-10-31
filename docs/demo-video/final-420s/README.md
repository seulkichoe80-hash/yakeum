# 약이음 7분 발표 삽입 영상

앱 촬영 기준: `ccb2602f86dd4e275c0a75ab77fb62484a8a8b02`.
15분 PPT 발표에 삽입하는 420초·1920×1080·30fps 영상의 최종 대본과 검증 기록입니다.

- `NARRATION_KO.md`: 사용자 제공 Typecast 음성의 배치 대본
- `captions-ko.srt`: 화면 자막 52개
- `SCREEN_ALIGNMENT.md`: 음성과 화면 배치 대조
- `VALIDATION.md`: 최종 수정·검증 범위와 미검증 사항
- `MUSIC_SOURCE.md`: 사용자 제공 음악의 출처·이용 조건 확인 상태
- `*-validation.json`, `ending-check.json`: 파일·음량·종료 수치 검사

## 구분과 제한

신규 촬영은 분리된 로컬 합성 자료와 Mock 응답입니다. 실제 Render 화면 캡처를 확보하지 못한 구간은 ‘사용자가 제공한 기존 실행 기록 요약’ 설명 카드로 표시했습니다. 사진의 실제 Gemini+가상 매칭 기록과 HIRA의 실제 식약처 매칭 기록을 구분합니다. 두 실제 서비스를 결합한 사진 전체 흐름을 검증했다고 주장하지 않습니다.

직접 청취한 음질·발음·싱크·PC 스피커 명료도는 미검증입니다. 음원과 TTS의 공개·제출 이용 조건은 확인이 필요합니다.

## 영상 파일 보관

후속 전체 작업 저장 요청에 따라 최종 MP4 3종, DOCX, 제작 코드·편집 설정·몽타주·주요 캡처를 이 폴더에 추가했습니다. 원본 음성·배경음·DB·중복 영상·중간 WAV·촬영 캐시는 제외했습니다. 제작 코드는 production/README.md의 원본 자료 의존성과 제한을 확인하세요. MP4는 GitHub 파일 페이지의 Download raw로 다운로드하세요.

- `YAKEUM_FINAL_TTS_BGM.mp4`
- `YAKEUM_FINAL_TTS_ONLY.mp4`
- `YAKEUM_FINAL_SILENT.mp4`

세 파일은 영상 스트림이 같고 오디오 구성만 다릅니다. 파일별 해시는 `video-validation.json`의 원래 파일명에 기록되어 있습니다.

이번 문서 저장에서 앱·API 계약·AGENTS.md 변경, 실제 API 호출, DB/슬롯 초기화, Render 설정 변경·배포는 수행하지 않았습니다.
