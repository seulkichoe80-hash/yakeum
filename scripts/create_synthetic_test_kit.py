"""Generate non-personal local test fixtures outside the source checkout."""
import argparse
from io import BytesIO
from pathlib import Path
import openpyxl
from PIL import Image, ImageDraw

HEADERS=['번호','조제일자','처방기관','조제기관','제품명','약효분류','성분명','약품코드','단위','1회 투약량','1일 투여횟수','총 투약일수']


def workbook(rows):
    book=openpyxl.Workbook();sheet=book.active;sheet.title='가상 자료'
    sheet.append(['약이음 가상 테스트 자료 — 실제 복용 기록 아님']);sheet.append(HEADERS)
    for row in rows:sheet.append(row)
    output=BytesIO();book.save(output);book.close();return output.getvalue()


def generate(output):
    output=Path(output)
    if not output.is_absolute() or output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError('저장소 밖의 절대 출력 경로를 지정하세요.')
    output.mkdir(parents=True,exist_ok=True)
    if any(output.iterdir()):raise ValueError('기존 파일을 보존하기 위해 빈 출력 폴더가 필요합니다.')
    previous=[1,'2026-09-01','가상의원','가상약국','가상제품','가상분류',None,'000123456','정','1','1','7']
    current=[*previous];current[1]='2026-10-01';current[9]='2'
    for name,rows in [('previous.xlsx',[previous]),('current.xlsx',[current]),('held.xlsx',[current,[9,'invalid',None,None,None,None,None,None,None,None,None,None]]),('empty.xlsx',[])]:
        with (output/name).open('xb') as target:target.write(workbook(rows))
    image=Image.new('RGB',(800,500),'white');draw=ImageDraw.Draw(image)
    draw.text((40,80),'YAKEUM - SYNTHETIC TEST ONLY',fill='black',font_size=32)
    draw.text((40,150),'Not a real prescription. Fake AI response.',fill='black',font_size=24)
    image.save(output/'synthetic-photo.png')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True)
    generate(parser.parse_args().output)
    print('가상 PNG와 XLSX 4종을 생성했습니다. 실제 건강정보가 아닙니다.')
