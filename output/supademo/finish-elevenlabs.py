"""Assemble the approved RETCON script with ElevenLabs Generation 2.

Keep the supplied audio's speaking speed and original pauses unchanged.
All app imagery comes from the supplied Supademo MP4.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,re,subprocess,wave,math,sys
from difflib import SequenceMatcher
import numpy as np
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'final-build';OUT.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe()
SOURCE=ROOT/'2026-09-24, 07_08_13 p.m.-RETCON___Backfill_for_stories.mp4'
VOICE=ROOT/'ElevenLabs_2026-09-24T19_44_10_Liam - Viral Short-Form Storyteller_pvc_sp93_s50_sb55_v3.mp3'
PARAS=(ROOT/'approved-narration.txt').read_text().strip().split('\n\n')
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'

def tokens(s):return re.findall(r"[a-z0-9]+(?:'[a-z0-9]+)?",s.lower().replace('’',"'"))
words=[]
for segment in json.loads((OUT/'transcript.json').read_text()):
    for w in segment['words']:
        ts=tokens(w['word'])
        for j,t in enumerate(ts):
            words.append({'token':t,'start':w['start']+(w['end']-w['start'])*j/len(ts),'end':w['start']+(w['end']-w['start'])*(j+1)/len(ts)})
ref=[];pstarts=[]
for p in PARAS:pstarts.append(len(ref));ref+=tokens(p)
matcher=SequenceMatcher(None,ref,[w['token'] for w in words],autojunk=False)
mapping={}
for block in matcher.get_matching_blocks():
    for k in range(block.size):mapping[block.a+k]=block.b+k
for i in range(len(ref)):
    if i not in mapping:
        prev=max((j for j in mapping if j<i),default=None);nxt=min((j for j in mapping if j>i),default=None)
        if prev is not None and nxt is not None:
            mapping[i]=round(mapping[prev]+(mapping[nxt]-mapping[prev])*(i-prev)/(nxt-prev))
        else:mapping[i]=mapping[prev] if prev is not None else mapping[nxt]
aligned=[words[mapping[i]] for i in range(len(ref))]
if matcher.ratio()<.94:raise RuntimeError(f'Alignment needs review: {matcher.ratio()}')

# The user prefers Generation 2 as downloaded: no extra pauses or tempo changes.
pause_lengths={}
pauses=[]
for p,d in pause_lengths.items():
    i=pstarts[p];left=aligned[i-1]['end'];right=aligned[i]['start']
    pauses.append({'paragraph':p+1,'source_time':(left+right)/2,'seconds':d})
pauses.sort(key=lambda x:x['source_time'])
def shift(t):return t+sum(p['seconds'] for p in pauses if t>=p['source_time'])
sr=48000
subprocess.run([FF,'-y','-loglevel','error','-i',str(VOICE),'-ar',str(sr),'-ac','1','-c:a','pcm_s16le',str(OUT/'generation-2-decoded.wav')],check=True)
with wave.open(str(OUT/'generation-2-decoded.wav'),'rb') as w:raw=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).copy()
parts=[];cursor=0
for p in pauses:
    n=round(p['source_time']*sr);parts.extend([raw[cursor:n],np.zeros(round(p['seconds']*sr),dtype=np.int16)]);cursor=n
parts.extend([raw[cursor:],np.zeros(sr,dtype=np.int16)])
audio=np.concatenate(parts)
with wave.open(str(OUT/'narration-original-pace.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(audio.tobytes())
total=math.ceil(len(audio)/sr*30)/30
if total>150:raise RuntimeError(f'Too long: {total}')
starts=[0]+[round(max(0,shift(aligned[i]['start'])-.2)*30)/30 for i in pstarts[1:]]
ends=starts[1:]+[total]
scenes=[{'paragraph':i+1,'start':a,'end':b,'duration':b-a,'text':p} for i,(a,b,p) in enumerate(zip(starts,ends,PARAS))]
export_index=ref.index('export',pstarts[10])
export_start=round((shift(aligned[export_index-3]['start'])-.15)*30)/30
manifest={'source_audio':VOICE.name,'voice':'Liam - Viral Short-Form Storyteller','take':'Generation 2','speech_speed_changed':False,'alignment_match':matcher.ratio(),'duration':total,'pauses':pauses,'scenes':scenes,'export_start':export_start}
(OUT/'timing.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2),flush=True)

def srt_time(t):
    ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
cues=[];idx=0
for p in PARAS:
    chunks=[];line=''
    for word in p.split():
        candidate=(line+' '+word).strip()
        if len(candidate)>73 and line:chunks.append(line);line=word
        else:line=candidate
        if line.endswith(('.', '?', '!')) and len(line)>35:chunks.append(line);line=''
    if line:chunks.append(line)
    for chunk in chunks:
        n=len(tokens(chunk));a=shift(aligned[idx]['start']);b=shift(aligned[idx+n-1]['end'])+.1
        cues.append(f'{len(cues)+1}\n{srt_time(a)} --> {srt_time(b)}\n{chunk}\n');idx+=n
(ROOT/'RETCON-final-elevenlabs.io.srt').write_text('\n'.join(cues))
if '--align-only' in sys.argv:raise SystemExit(0)

# Keep the established visual styling, adding the required ElevenLabs attribution.
im=Image.open(ROOT/'review-cut/closing.png').convert('RGB');d=ImageDraw.Draw(im)
d.text((90,1020),'Narration: elevenlabs.io',font=ImageFont.truetype(FONT,24),fill='#afc1c1')
im.save(OUT/'closing.png')
source_starts=[None,4.05,12.05,16.05,20.05,36.05,40.05,48.05,52.05,56.05,60.05,None]
labels=['','AIRFLOW PLUGIN  |  WRITER WORKSPACE','CHANGE MARA’S FATE AFTER CHAPTER 2','3 DEPENDENT CHAPTERS  |  2 DIALOGUE FAILURES','ASSET SCHEDULING  |  MODEL WAIT CONDENSED','DYNAMIC TASK MAPPING  |  COMMON AI @task.llm','NATIVE HITLOperator  |  AUTHOR APPROVAL','REVIEW THE ORIGINAL AND PROPOSED PARAGRAPHS','THE AUTHOR HAS THE FINAL SAY','NEW MANUSCRIPT VERSION  |  PUBLISHED ASSET EVENT','VALID MEMORY  |  CHAPTER 5 STAYS UNCHANGED','']

def render(i):
    duration=scenes[i]['duration'];start=source_starts[i];dst=OUT/f'scene-{i:02d}.mp4'
    args=[FF,'-y','-hide_banner','-loglevel','error']
    if start is None:
        card=ROOT/'review-cut/opening.png' if i==0 else OUT/'closing.png'
        args+=['-loop','1','-framerate','30','-i',str(card)]
        filt='setsar=1'
    else:
        args+=['-ss',str(start),'-t','3.8','-i',str(SOURCE)]
        label=OUT/f'label-{i:02d}.txt';label.write_text(labels[i])
        filt=f'scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14272d,setsar=1,tpad=stop_mode=clone:stop_duration={max(0,duration-3.8)},drawtext=fontfile={FONT}:textfile={label}:fontsize=25:fontcolor=white:x=30:y=1027:box=1:boxcolor=0x14272d@0.93:boxborderw=13'
    filt+=f',fade=t=in:st=0:d=0.15,fade=t=out:st={duration-.15}:d=0.15'
    args+=['-vf',filt,'-t',str(duration),'-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2',str(dst)]
    subprocess.run(args,check=True)
    if i==10:
        keep=export_start-scenes[i]['start'];expdur=scenes[i]['end']-export_start
        mem=OUT/'memory-trim.mp4';exp=OUT/'export-trim.mp4'
        subprocess.run([FF,'-y','-loglevel','error','-i',str(dst),'-t',str(keep),'-an','-c:v','libx264','-preset','fast','-crf','18','-threads','2',str(mem)],check=True)
        subprocess.run([FF,'-y','-loglevel','error','-i',str(OUT/'export-moment.mp4'),'-vf',f'tpad=stop_mode=clone:stop_duration={max(0,expdur-8)}','-t',str(expdur),'-an','-c:v','libx264','-preset','fast','-crf','18','-threads','2',str(exp)],check=True)
        cat=OUT/'memory-export.txt';cat.write_text("file 'memory-trim.mp4'\nfile 'export-trim.mp4'\n")
        subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(cat),'-c','copy',str(dst)],check=True)
    print(f'Rendered paragraph {i+1}: {duration:.2f}s',flush=True)
    return dst

with ThreadPoolExecutor(max_workers=3) as pool:segments=list(pool.map(render,range(12)))
cat=OUT/'final-segments.txt';cat.write_text(''.join(f"file '{p.name}'\n" for p in segments))
picture=OUT/'final-picture.mp4'
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(cat),'-c','copy',str(picture)],check=True)
final=ROOT/'RETCON-final-elevenlabs.io.mp4'
subprocess.run([FF,'-y','-loglevel','error','-i',str(picture),'-i',str(OUT/'narration-original-pace.wav'),'-i',str(ROOT/'RETCON-final-elevenlabs.io.srt'),'-map','0:v','-map','1:a','-map','2:s','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=9','-ar','48000','-c:a','aac','-b:a','192k','-c:s','mov_text','-metadata','title=RETCON — Backfill for stories | elevenlabs.io','-metadata:s:s:0','language=eng','-t',str(total),'-movflags','+faststart',str(final)],check=True)
print('FINAL:',final,flush=True)
