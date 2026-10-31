from pathlib import Path
import wave,json,subprocess,re
import numpy as np
P=Path(__file__).parent
# Decode stems to low-rate floating PCM for numerical analysis only (delivery stays 48kHz).
def pcm(name,rate=8000):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(P/name),'-ar',str(rate),'-ac','2','-f','f32le','-']),dtype=np.float32).reshape(-1,2)
v=pcm('narration-420.wav');b=pcm('music-base-420.wav');d=pcm('music-ducked-420.wav');mix=pcm('mix-420.wav');rate=8000
assert len(v)==len(b)==len(d)==len(mix)==420*rate
rms=lambda a:float(np.sqrt(np.mean(np.square(a,dtype=np.float64))))
db=lambda x:float(20*np.log10(max(x,1e-12)))
ratios=[];gain=[];active=[]
for i in range(420):
 x=v[i*rate:(i+1)*rate];y=d[i*rate:(i+1)*rate];base=b[i*rate:(i+1)*rate]
 if db(rms(x))>-32:
  ratios.append(db(rms(x))-db(rms(y)));active.append(i)
 if rms(base)>1e-6:gain.append(rms(y)/rms(base))
assert max(gain)<=1.001,max(gain)
assert np.max(np.abs(mix))<1
mono=(v[:,0]+v[:,1])*.5
mono_loss=db(rms(mono))-db(rms(v));assert abs(mono_loss)<.01
music_original='/workspace/attachments/3611da0a-e7ca-44b7-b2a0-2c08686e8d5f/leberch-soft-piano-soft-piano-music-603947.mp3'
length=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',music_original]))['format']['duration'];length=float(length)
joins=[{'overlap_start_approx':length-4,'overlap_end_approx':length},{'overlap_start_approx':2*(length-4),'overlap_end_approx':2*length-4}]
for j in joins:
 a=int(j['overlap_start_approx']*rate);z=int(j['overlap_end_approx']*rate);j['music_rms_dbfs']=db(rms(b[a:z]));j['music_peak_dbfs']=db(float(np.max(np.abs(b[a:z]))));j['direct_listening']='NOT_PERFORMED'
report={'stems_seconds':420,'voice_gain_db':-2,'music_base_gain_db':-14,'maximum_ducked_to_base_rms_ratio':max(gain),'active_voice_window_threshold_dbfs':-32,'active_voice_to_music_db':{'minimum':min(ratios),'median':float(np.median(ratios))},'voice_mono_downmix_rms_delta_db':mono_loss,'mix_sample_peak_dbfs':db(float(np.max(np.abs(mix)))),'repeat_boundaries':joins,'crossfade_gain_law':'linear; outgoing+incoming gains=1, no summing boost','earphone_hardware_listening':'NOT_PERFORMED','pc_speaker_hardware_listening':'NOT_PERFORMED','subjective_articulation_and_musical_phrase_review':'NOT_PERFORMED'}
(P/'audio-numerical-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
