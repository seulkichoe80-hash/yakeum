import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

print("--- 사용 가능한 모델 목록 ---")
try:
    # 현재 API 키로 접근 가능한 모든 모델 출력
    for m in client.models.list():
        print(f"모델명: {m.name}")
except Exception as e:
    print(f"에러 발생: {e}")