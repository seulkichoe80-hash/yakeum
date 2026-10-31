from pathlib import Path
import json,subprocess,shutil
P=Path(__file__).parent;B=json.loads((P/'storyboard.json').read_text());F='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
def ff(a):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-filter_complex_threads','2','-threads','2',*a],check=True)
for i,r in [(43,(475,470,970,560))]:
 s=B[i];duration=s['duration'];first=P/'clips'/f'wide-{i:02}.mp4';second=P/'clips'/f'focus-{i:02}.mp4';target=P/'clips'/f'{i:02}.mp4';backup=P/'clips'/f'base-{i:02}.mp4';shutil.copyfile(target,backup)
 ff(['-i',str(backup),'-t','2','-vf','fade=t=out:st=1.88:d=0.12:color=0xeef3f2,fps=30','-an','-c:v','libx264','-preset','veryfast','-crf','18','-g','60','-threads','2','-pix_fmt','yuv420p','-y',str(first)])
 x,y,cw,ch=r;scale=min(1720/cw,840/ch);w=int(cw*scale)//2*2;h=int(ch*scale)//2*2;px=(1920-w)//2;py=70+(840-h)//2
 caption=P/'captions'/f'{i:02}.txt';caption.write_text(s['caption']);input_image=P/'stills'/(s['shot']+'.png')
 f=f'[0:v]crop={cw}:{ch}:{x}:{y},scale={w}:{h}:flags=lanczos[app];[1:v][app]overlay={px}:{py},drawbox=x=0:y=930:w=1920:h=150:color=0x111f29:t=fill,drawbox=x=1532:y=12:w=370:h=48:color=0x183f38:t=fill,drawtext=fontfile={F}:text=시연용 가상 응답:fontsize=29:fontcolor=white:x=1560:y=17,drawtext=fontfile={F}:textfile={caption}:fontsize=38:fontcolor=white:line_spacing=12:x=(w-text_w)/2:y=949,fps=30,format=yuv420p,fade=t=in:st=0:d=0.12:color=0xeef3f2,fade=t=out:st={duration-2-.12}:d=0.12:color=0xeef3f2[out]'
 ff(['-loop','1','-framerate','30','-i',str(input_image),'-f','lavfi','-i','color=c=0xeef3f2:s=1920x1080:r=30','-filter_complex',f,'-map','[out]','-t',str(duration-2),'-frames:v',str(s['frames']-60),'-an','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-g','60','-pix_fmt','yuv420p','-y',str(second)])
 lst=P/f'join-{i:02}.txt';lst.write_text(f"file '{first}'\nfile '{second}'\n");ff(['-f','concat','-safe','0','-i',str(lst),'-c','copy','-y',str(target)])
 print('polished',i,flush=True)
ff(['-f','concat','-safe','0','-i',str(P/'concat.txt'),'-c','copy','-movflags','+faststart','-y',str(P/'YAKEUM_TTS_EDIT_SILENT_420s.mp4')])
