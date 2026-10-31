from pathlib import Path
import json,subprocess,re
import numpy as np
P=Path(__file__).parent;M=json.load(open('/workspace/outputs/yakeum-tts/audio_inventory.json'));A={r['number']:r['path'] for r in M}
def ff(a):subprocess.run(['ffmpeg','-hide_banner','-loglevel','error',*a],check=True)
# Original MP3s are never modified. File 4's tail duplicates file 3 (waveform r=.9554).
# Cuts are inside detected silence, never tempo/pitch transforms.
placements=[(1,0,None,.5),(2,0,None,10.3),(3,0,None,54),(4,0,27.2,122),(5,0,11.6314,158),(5,11.6314,20.5792,173.6314),(5,20.5792,None,185.5792),(6,0,None,201),(7,0,None,242),(8,0,None,282),(9,0,None,311),(10,0,17.348125,345.5),(10,17.348125,None,365.348125),(11,0,None,399.5)]
inputs=[]
for r in M:inputs+=['-i',r['path']]
filters=['[4:a]asplit=3[f5a][f5b][f5c]','[9:a]asplit=2[f10a][f10b]'];labels=[];p5=0;p10=0;used=[]
for i,(number,start,end,at) in enumerate(placements):
 if number==5:source=['f5a','f5b','f5c'][p5];p5+=1
 elif number==10:source=['f10a','f10b'][p10];p10+=1
 else:source=f'{number-1}:a'
 end_arg=f':end={end}' if end is not None else ''
 delay=round(at*48000)
 filters.append(f'[{source}]atrim=start={start}{end_arg},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume=-2dB,adelay={delay}S|{delay}S[v{i}]');labels.append(f'[v{i}]')
 duration=(end if end is not None else M[number-1]['duration'])-start
 used.append({'file':number,'source_start':start,'source_end':end,'timeline_start':at,'conservative_end':at+duration,'gain_db':-2})
filters.append(''.join(labels)+f'amix=inputs={len(labels)}:normalize=0,apad,atrim=duration=420[out]')
ff([*inputs,'-filter_complex',';'.join(filters),'-map','[out]','-c:a','pcm_s24le','-y',str(P/'narration-420.wav')])
music='/workspace/attachments/3611da0a-e7ca-44b7-b2a0-2c08686e8d5f/leberch-soft-piano-soft-piano-music-603947.mp3'
# Whole-track cadence/reverb tail, linear 4-second overlaps. No gain-summing boost.
ff(['-i',music,'-i',music,'-i',music,'-filter_complex','[0:a]aresample=48000,aformat=channel_layouts=stereo[a];[1:a]aresample=48000,aformat=channel_layouts=stereo[b];[2:a]aresample=48000,aformat=channel_layouts=stereo[c];[a][b]acrossfade=d=4:c1=tri:c2=tri[ab];[ab][c]acrossfade=d=4:c1=tri:c2=tri,atrim=duration=420,volume=-14dB,afade=t=in:st=0:d=3,afade=t=out:st=415:d=5[out]','-map','[out]','-c:a','pcm_s24le','-y',str(P/'music-base-420.wav')])
ff(['-i',str(P/'music-base-420.wav'),'-i',str(P/'narration-420.wav'),'-filter_complex','[0:a]apad=pad_dur=1[mb];[1:a]apad=pad_dur=1[vc];[mb][vc]sidechaincompress=threshold=0.05:ratio=6:attack=30:release=1000:knee=4:makeup=1,atrim=duration=420[ducked]','-map','[ducked]','-c:a','pcm_s24le','-y',str(P/'music-compressed-420.wav')])
# Scheduled -6dB floor covers quiet syllables and short pauses inside narration.
raw=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(P/'music-compressed-420.wav'),'-f','f32le','-ar','48000','-ac','2','-']),dtype=np.float32).reshape(-1,2)
envelope=np.ones(len(raw),dtype=np.float32);floor=10**(-6/20)
for segment in used:
 a=int(segment['timeline_start']*48000);z=min(len(raw),int(segment['conservative_end']*48000));pre=max(0,a-12000);post=min(len(raw),z+48000)
 envelope[pre:a]=np.minimum(envelope[pre:a],np.linspace(1,floor,a-pre,endpoint=False,dtype=np.float32))
 envelope[a:z]=np.minimum(envelope[a:z],floor)
 envelope[z:post]=np.minimum(envelope[z:post],np.linspace(floor,1,post-z,endpoint=False,dtype=np.float32))
subprocess.run(['ffmpeg','-v','error','-f','f32le','-ar','48000','-ac','2','-i','pipe:0','-c:a','pcm_s24le','-y',str(P/'music-ducked-420.wav')],input=(raw*envelope[:,None]).astype(np.float32).tobytes(),check=True)
ff(['-i',str(P/'narration-420.wav'),'-i',str(P/'music-ducked-420.wav'),'-filter_complex','[0:a][1:a]amix=inputs=2:normalize=0,alimiter=limit=0.95:level=false:latency=1,apad,atrim=duration=420[out]','-map','[out]','-c:a','pcm_s24le','-y',str(P/'mix-420.wav')])
levels=[]
for r in M:
 q=subprocess.run(['ffmpeg','-hide_banner','-i',r['path'],'-af','volumedetect','-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True).stderr
 levels.append({'file':r['number'],'input_duration':r['duration'],'applied_gain_db':-2,**{k:float(v) for k,v in re.findall(r'(mean_volume|max_volume): (-?[0-9.]+) dB',q)}})
(P/'audio-plan.json').write_text(json.dumps({'placements':used,'input_levels':levels,'original_total_seconds':sum(r['duration'] for r in M),'duplicate_trim':{'file':4,'start':27.2,'end':38.556,'seconds_removed':11.356,'duplicate_of':'3.mp3 tail 47.122s onwards','waveform_correlation':0.9554006962253585},'edited_narration_seconds':sum(r['duration'] for r in M)-11.356,'voice_gain_db':-2,'music_base_gain_db':-14,'scheduled_ducking':{'additional_gain_db':-6,'attack_ms':250,'release_ms':1000,'intervals':'all narration file/segment spans'},'ducking':{'threshold':0.05,'ratio':6,'attack_ms':30,'release_ms':1000,'knee':4,'makeup':1},'music_fade_in':3,'music_fade_out':5,'linear_crossfade_seconds':4,'master_limiter':{'limit':0.95,'automatic_gain':False},'playback_speed':1.0,'physical_headphone_listening':'NOT_PERFORMED','physical_pc_speaker_listening':'NOT_PERFORMED','musical_phrase_listening':'NOT_PERFORMED'},ensure_ascii=False,indent=2))
print('audio stems ready',flush=True)
