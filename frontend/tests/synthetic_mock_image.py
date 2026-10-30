"""Deterministic synthetic test fixture matching the existing Mock's 1-tablet dose.
Not OCR evidence; not a real prescription. Writes PNG bytes only.
"""
from io import BytesIO
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont
font_path = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
font = ImageFont.truetype(str(font_path), 28) if font_path.exists() else ImageFont.load_default()
image=Image.new('RGB',(900,480),'white')
draw=ImageDraw.Draw(image)
draw.multiline_text((25,20),'약이음 합성 Mock 시연 · 실제 처방 아님\n제품: 가상알파정\n성분: 가상알파성분 / 함량: 100 mg\n1회 투약량: 1 정\n하루 횟수: 2 회\n투약일수: 7 일',font=font,fill='#183f38',spacing=12)
buffer=BytesIO();image.save(buffer,format='PNG');sys.stdout.buffer.write(buffer.getvalue())
