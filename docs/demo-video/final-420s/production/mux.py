from pathlib import Path
import subprocess,shutil,json
P=Path(__file__).parent;silent=P/'YAKEUM_TTS_EDIT_SILENT_420s.mp4';shutil.copyfile(silent,P/'YAKEUM_SILENT_420s.mp4')
for audio,name in [('narration-420.wav','YAKEUM_TTS_ONLY_420s.mp4'),('mix-420.wav','YAKEUM_TTS_BGM_420s.mp4')]:
 subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-i',str(silent),'-i',str(P/audio),'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-t','420','-movflags','+faststart','-y',str(P/name)],check=True);print(name,flush=True)
# Diagnostic mono clip is a listening aid, NOT a claim of physical speaker validation.
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-ss','120','-i',str(P/'YAKEUM_TTS_BGM_420s.mp4'),'-t','30','-vf','fps=30','-c:v','libx264','-preset','veryfast','-crf','18','-threads','2','-af','pan=mono|c0=0.5*c0+0.5*c1','-c:a','aac','-b:a','128k','-movflags','+faststart','-y',str(P/'PC_SPEAKER_CHECK_MONO_30s.mp4')],check=True)
print('mux complete',flush=True)
