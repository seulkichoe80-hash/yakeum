# 최종 영상 제작 코드 보관

실제 제작에 사용한 스크립트·장면표·음성 배치·촬영 메타데이터의 원본 보관본입니다. 앱 실행 코드는 변경하지 않습니다.

스크립트는 제작 당시의 `/workspace/outputs/`와 사용자 제공 첨부파일 경로를 참조합니다. 원본 MP3·녹화 WebM·중간 클립·stills는 포함하지 않아 이 폴더만으로 즉시 재생성할 수 없습니다. 해당 경로를 소유한 별도 원본 자료로 연결해야 합니다. 이 경로에는 키 값이 없습니다.

필요 도구: Python, FFmpeg/ffprobe, Pillow, NumPy, python-docx, 한글 Noto Sans CJK 폰트. final_qa.py의 OCR 점검에는 tesseract가 필요합니다.

제작 순서: render.py → finish_long_views.py → finish_saved_list.py → 클립 결합 → audio.py → mux.py → audio_qa.py / final_qa.py. 일부 클립은 이전 승인 버전에서 재사용했으므로 자동 재현 패키지로 간주하지 않습니다. 최종 MP4와 검사 JSON을 기준 산출물로 사용합니다.

새 실제 API 호출·실제 DB 연결은 이 편집 작업에 필요하지 않습니다. 기존 기록 요약 카드는 실제 실행 화면 캡처가 아닙니다.
