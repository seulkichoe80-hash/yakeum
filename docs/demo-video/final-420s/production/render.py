from pathlib import Path
import json,subprocess,sys,math,os
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).parent;M=json.loads((P/'capture.json').read_text());B=json.loads((P/'storyboard.json').read_text());S={s['name']:s for s in M['shots']};RAW=M['webm'];F='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
(P/'clips').mkdir(exist_ok=True);(P/'captions').mkdir(exist_ok=True);(P/'montages').mkdir(exist_ok=True);(P/'frames').mkdir(exist_ok=True)
def run(a):subprocess.run(a,check=True)
def ff(a):run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','2','-threads','2',*a])
def rect(x,y,w,h):
 x=max(0,int(x)//2*2);y=max(0,int(y)//2*2);w=min(1920-x,max(2,int(w)//2*2));h=min(1440-y,max(2,int(h)//2*2));return x,y,w,h
def box(b,pad=18):return rect(b['x']-pad,b['y']-pad,b['width']+2*pad,b['height']+2*pad)
def crop(r):return f'crop={r[2]}:{r[3]}:{r[0]}:{r[1]}'
def layout(r,maxw=1720,maxh=840):
 scale=min(maxw/r[2],maxh/r[3]);w=int(r[2]*scale)//2*2;h=int(r[3]*scale)//2*2;return w,h,(1920-w)//2,70+(840-h)//2
# Evidence cards are clearly editorial records, never simulated application success screens.
def card(name,lines):
 im=Image.new('RGB',(1760,840),'#f8fbfa');d=ImageDraw.Draw(im)
 y=50
 for text,size,color,gap in lines:
  d.text((60,y),text,font=ImageFont.truetype(F,size),fill=color);y+=gap
 im.save(P/(name+'.png'))
card('existing-evidence',[
 ('사용자가 제공한 기존 실행 기록 요약',43,'#183f38',95),('실제 실행 화면 캡처가 아닌 설명 카드입니다.',32,'#445b65',110),
 ('건강보험심사평가원 자료 · 단일 합성 제품',40,'#183f38',70),('실제 식약처 매칭 → 비교 → 저장 → 재조회',39,'#243a43',110),
 ('사진 · 합성 PNG',40,'#183f38',70),('실제 Gemini 추출 + 가상 의약품 매칭·저장',39,'#243a43',85)])
card('closing-card',[
 ('약이음',86,'#183f38',160),('등록 → 내용 확인 → 비교 결과',52,'#183f38',135),('기록 비교와 실제 복용 확인을 구분합니다.',36,'#445b65',95),('이어서 PPT 발표로 돌아갑니다.',40,'#243a43',80)])
card('evidence-hira',[
 ('사용자가 제공한 기존 실행 기록 요약',43,'#183f38',95),('실제 실행 화면 캡처가 아닌 설명 카드입니다.',32,'#445b65',130),
 ('건강보험심사평가원 자료 경로',44,'#183f38',90),('단일 합성 제품의 실제 식약처 매칭',43,'#243a43',90),('비교 → 저장 → 재조회 사용자 확인 기록',40,'#243a43',90)])
card('evidence-photo',[
 ('사용자가 제공한 기존 실행 기록 요약',43,'#183f38',95),('실제 실행 화면 캡처가 아닌 설명 카드입니다.',32,'#445b65',130),
 ('사진 · 실제 Gemini 추출',46,'#183f38',95),('가상 의약품 매칭 → 비교 → 저장 → 재조회',39,'#243a43',100),('사용자가 확인한 기존 결과의 요약입니다.',32,'#445b65',80)])
card('evidence-limit',[
 ('사용자가 제공한 기존 실행 기록 요약',43,'#183f38',95),('실제 실행 화면 캡처가 아닌 설명 카드입니다.',32,'#445b65',130),
 ('사진에서 실제 Gemini와 실제 식약처를',43,'#6a4e23',90),('함께 사용한 전체 흐름은 미검증입니다.',43,'#6a4e23',100)])
for r in B:
 i=r['index'];name=r['shot'];mode=r['mode'];target=P/'clips'/f'{i:02}.mp4'
 if target.exists() and os.environ.get('YAKEUM_VIDEO_RESUME')=='1':continue
 s=S.get(name);d=r['duration'];filters=[];decor='';inputs=[];raw_start=0;source_length=1;image=False
 if (mode.startswith('card') or mode=='closing'):
  asset={'card':'existing-evidence.png','card-hira':'evidence-hira.png','card-photo':'evidence-photo.png','card-limit':'evidence-limit.png','closing':'closing-card.png'}[mode];inputs=['-loop','1','-framerate','30','-i',str(P/asset)];filters=['[0:v]scale=1760:840[app]','[1:v][app]overlay=80:70[body]'];image=True
 else:
  dynamic={'family','choose-previous','choose-current','read','edit','confirm','intake-select','save-click','hira-files','hira-compare','hira-save','hold-file'}
  if name=='compare-click':s=S['result-summary'];mode='box'
  raw_start=s['start'];source_length=min(d,s['end']-s['start'])
  if name not in dynamic:inputs=['-loop','1','-framerate','30','-i',str(P/'stills'/(s['name']+'.png'))]
  else:inputs=['-ss',str(raw_start),'-t',str(max(.5,source_length-.25)),'-i',RAW]
  b=s['box'];special=False
  if mode=='context':cr=rect(440,80,1040,1030)
  elif mode=='family':cr=rect(455,80,1030,250)
  elif mode in ('originals','contrast'):
   ims=s['images'];a=ims[0];left=rect(a['x'],a['y'],a['width'],a['height']*.73)
   if mode=='originals':z=ims[1];right=rect(z['x'],z['y'],z['width'],z['height']*.73);labels=['이전 원본 사진','현재 원본 사진']
   else:z=s['dose'];right=rect(z['x']-12,z['y']-38,z['width']+24,210);labels=['현재 원본 사진','가상 추출값']
   h1=int(820*left[3]/left[2])//2*2;h2=int(820*right[3]/right[2])//2*2
   filters=['[0:v]split=2[a][b]',f'[a]{crop(left)},scale=820:{h1}:flags=lanczos[one]',f'[b]{crop(right)},scale=820:{h2}:flags=lanczos[two]','[1:v][one]overlay=100:305[tmp]','[tmp][two]overlay=1000:305[body]'];special=True
   decor=f",drawtext=fontfile={F}:text='{labels[0]}':fontsize=42:fontcolor=0x183f38:x=100:y=210,drawtext=fontfile={F}:text='{labels[1]}':fontsize=42:fontcolor=0x183f38:x=1000:y=210"
  elif mode=='edit':b=s.get('dose',b);cr=rect(b['x']-18,b['y']-44,b['width']+36,230)
  elif mode=='confirm':a=s['ack'];z=s['compare'];cr=rect(a['x']-12,a['y']-20,970,z['y']+z['height']-a['y']+44)
  elif mode in ('changed','quick'):cr=rect(b['x']+5,b['y']+5,710,220)
  elif mode=='intake':cr=rect(b['x']-18,b['y']-20,750,b['height']+45)
  elif mode in ('save','saved'):
   a=s['intake'];z=s['save'] if mode=='save' else s['open'];cr=rect(min(a['x'],z['x'])-20,a['y']-20,780,z['y']+z['height']-a['y']+36)
  elif mode=='hira-result':cr=rect(b['x']-12,b['y']+355,800,460)
  elif mode=='hira-save':cr=rect(b['x']-12,b['y']+530,800,350)
  elif mode=='held':cr=rect(b['x']-12,b['y']+95,980,390)
  elif mode=='saved-detail':cr=rect(b['x']-12,b['y']+190,900,520)
  elif mode=='mobile-full':cr=rect(0,0,390,844)
  elif mode=='mobile-card':cr=rect(0,max(0,b['y']-20),390,min(520,844-max(0,b['y']-20)))
  elif mode=='mobile-intake':cr=rect(0,max(0,b['y']-45),390,min(370,844-max(0,b['y']-45)))
  else:cr=box(b)
  if not special:
   w,h,x,y=layout(cr,1720,840)
   filters=[f'[0:v]{crop(cr)},scale={w}:{h}:flags=lanczos[app]',f'[1:v][app]overlay={x}:{y}[body]']
   if mode=='changed':decor=f',drawbox=x={x+int(22*w/cr[2])}:y={y+int(112*h/cr[3])}:w={int(270*w/cr[2])}:h={int(42*h/cr[3])}:color=0xb64e14:t=3'
   if mode=='mobile-full':decor=f",drawtext=fontfile={F}:text='모바일 크기 화면':fontsize=38:fontcolor=0x183f38:x=1250:y=400,drawtext=fontfile={F}:text='390px 브라우저 확인':fontsize=28:fontcolor=0x445b65:x=1250:y=465"
 caption=P/'captions'/f'{i:02}.txt';caption.write_text(r['caption'])
 badge='기존 기록 요약' if mode.startswith('card') else '시연용 가상 응답'
 # Per-frame audit overlay; protected footer does not overlap the app viewport.
 finish=f"[body]drawbox=x=0:y=930:w=1920:h=150:color=0x111f29:t=fill,drawbox=x=1532:y=12:w=370:h=48:color=0x183f38:t=fill,drawtext=fontfile={F}:text='{badge}':fontsize=29:fontcolor=white:x=1560:y=17,drawtext=fontfile={F}:textfile={caption}:fontsize=38:fontcolor=white:line_spacing=12:x=(w-text_w)/2:y=949{decor},fps=30,format=yuv420p,fade=t=in:st=0:d=0.12:color=0xeef3f2,fade=t=out:st={d-.12}:d=0.12:color=0xeef3f2[out]"
 filters.append(finish)
 ff([*inputs,'-f','lavfi','-i','color=c=0xeef3f2:s=1920x1080:r=30','-filter_complex',';'.join(filters),'-map','[out]','-t',str(d),'-frames:v',str(r['frames']),'-an','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-g','60','-pix_fmt','yuv420p','-y',str(target)])
 print(f"rendered {i:02} {name} {d}s",flush=True)
# Lossless concatenation preserves all agreed stage timings.
(P/'concat.txt').write_text('\n'.join("file '"+str(P/'clips'/f'{r["index"]:02}.mp4')+"'" for r in B))
ff(['-f','concat','-safe','0','-i',str(P/'concat.txt'),'-c','copy','-movflags','+faststart','-y',str(P/'YAKEUM_TTS_EDIT_SILENT_420s.mp4')])
print('FINAL',flush=True)
