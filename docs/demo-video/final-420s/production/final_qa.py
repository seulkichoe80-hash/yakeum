from pathlib import Path
import json,subprocess,re,hashlib
from PIL import Image,ImageDraw,ImageFont,ImageStat
P=Path(__file__).parent;B=json.loads((P/'storyboard.json').read_text());(P/'frames').mkdir(exist_ok=True);(P/'montages').mkdir(exist_ok=True)
def ff(a):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',*a],check=True)
files=['YAKEUM_TTS_BGM_420s.mp4','YAKEUM_TTS_ONLY_420s.mp4','YAKEUM_SILENT_420s.mp4'];out={};hashes=[]
for name in files:
 f=P/name;meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries','format=duration,size:stream=codec_name,codec_type,width,height,r_frame_rate,nb_read_frames,sample_rate,channels,duration','-of','json',str(f)]))
 assert abs(float(meta['format']['duration'])-420)<.04
 v=[s for s in meta['streams'] if s['codec_type']=='video'][0];assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(1920,1080,'30/1',12600)
 aud=[s for s in meta['streams'] if s['codec_type']=='audio'];assert len(aud)==(0 if 'SILENT' in name else 1)
 ff(['-i',str(f),'-f','null','-'])
 h=subprocess.check_output(['ffmpeg','-v','error','-i',str(f),'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-']).decode().strip();hashes.append(h)
 meta['video_bitstream_hash']=h;meta['file_sha256']=hashlib.sha256(f.read_bytes()).hexdigest();meta['full_decode']='passed'
 if aud:
  log=subprocess.run(['ffmpeg','-hide_banner','-i',str(f),'-vn','-af','volumedetect','-f','null','-'],stderr=subprocess.PIPE,stdout=subprocess.DEVNULL,text=True).stderr
  meta['levels']={k:float(v) for k,v in re.findall(r'(mean_volume|max_volume): (-?[0-9.]+) dB',log)};assert meta['levels']['max_volume']<0
 out[name]=meta;print('file checked',name,flush=True)
assert len(set(hashes))==1
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',38)
assert len(B)==52 and sum(r['frames'] for r in B)==12600
for a,b in zip(B,B[1:]):assert abs(a['end']-b['start'])<.001
ocr_flags=[];flat_flags=[]
for r in B:
 assert len(r['caption'].splitlines())<=2 and max(font.getlength(x) for x in r['caption'].splitlines())<1800
 i=r['index'];strip=Image.new('RGB',(1440,300),'#102029');d=ImageDraw.Draw(strip)
 for j,t in enumerate([.5,r['duration']/2,max(.5,r['duration']-.5)]):
  fp=P/'frames'/f'{i:02}-{j}.jpg';ff(['-ss',str(t),'-i',str(P/'clips'/f'{i:02}.mp4'),'-vf','scale=480:270','-frames:v','1','-y',str(fp)]);im=Image.open(fp);strip.paste(im,(480*j,0));d.text((480*j+8,275),f'{i:02} {r["shot"]} +{t:.1f}s',fill='white')
  if ImageStat.Stat(im.convert('L').crop((20,25,460,230))).stddev[0]<5:flat_flags.append([i,j])
 strip.save(P/'montages'/f'shot-{i:02}.jpg')
 txt=subprocess.check_output(['tesseract',str(P/'frames'/f'{i:02}-1.jpg'),'stdout','-l','eng'],stderr=subprocess.DEVNULL).decode(errors='replace')
 if any(re.search(x,txt,re.I) for x in [r'AIza[0-9A-Za-z_-]{20,}',r'postgres(?:ql)?://',r'Bearer\s+[A-Za-z0-9._-]{12,}',r'eyJ[A-Za-z0-9_-]{15,}\.']):ocr_flags.append(i)
assert not ocr_flags and not flat_flags,(ocr_flags,flat_flags)
for st in range(1,10):
 rows=[r for r in B if r['stage']==st];im=Image.new('RGB',(1440,810),'#102029')
 for j in range(9):
  r=rows[min(len(rows)-1,round((len(rows)-1)*j/8))];im.paste(Image.open(P/'frames'/f'{r["index"]:02}-1.jpg'),((j%3)*480,(j//3)*270))
 im.save(P/'montages'/f'stage-{st}.jpg')
# Actual stage boundary frames, excluding no part of their visual transitions.
stamps=[10,53,120,200,240,310,345,399];im=Image.new('RGB',(1440,2400),'#102029');d=ImageDraw.Draw(im)
for row,t in enumerate(stamps):
 for j,dt in enumerate([-.22,0,.22]):
  fp=P/'frames'/f'boundary-{row}-{j}.jpg';ff(['-ss',str(t+dt),'-i',str(P/files[0]),'-vf','scale=480:270','-frames:v','1','-y',str(fp)]);im.paste(Image.open(fp),(j*480,row*300));d.text((j*480+8,row*300+275),f'{t}s {dt:+.2f}',fill='white')
im.save(P/'montages'/'stage-transitions.jpg')
for t,n in [(12,'family-title'),(76,'virtual-error'),(145,'changed'),(231,'saved'),(293,'existing-evidence'),(330,'held'),(388,'mobile'),(418,'last')]:ff(['-ss',str(t),'-i',str(P/files[0]),'-frames:v','1','-y',str(P/'frames'/(n+'.png'))])
report={'files':out,'identical_video_streams':True,'subtitle_cues':52,'shot_montages':52,'stage_montages':9,'inspected_transition_frames':24,'flat_content_flags':flat_flags,'ocr_secret_pattern_flags':ocr_flags,'app_sha':'ccb2602f86dd4e275c0a75ab77fb62484a8a8b02','actual_medical_api_calls':0,'physical_headphone_listening':'NOT_PERFORMED','physical_pc_speaker_listening':'NOT_PERFORMED','subjective_music_join_listening':'NOT_PERFORMED'}
(P/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))
