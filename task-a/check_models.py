import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("--- 이미지 분석(generate_content)이 가능한 모델 목록 ---")
found = False
try:
    for m in client.models.list():
        # 'supported_methods' 대신 'supported_actions'를 사용합니다.
        # 'generate_content' 또는 'generateContent'가 포함되어 있는지 확인합니다.
        actions = m.supported_actions if m.supported_actions else []
        if 'generate_content' in actions or 'generateContent' in actions:
            print(f"✅ 사용 가능: {m.name}")
            found = True
except Exception as e:
    print(f"에러 발생: {e}")

if not found:
    print("\n❌ 현재 API 키로는 일반적인 이미지 분석 모델을 사용할 수 없는 것 같습니다.")
    print("💡 해결책: Google AI Studio에서 'Create API key in new project'로 새 키를 발급받으세요.")