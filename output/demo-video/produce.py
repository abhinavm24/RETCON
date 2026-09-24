"""Reproducible 144-second film from genuine RETCON captures. No simulated UI."""
from pathlib import Path
import json, math, subprocess, sys, wave, array
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'output/demo-video'; CAP=ROOT/'output/playwright'
FF=imageio_ffmpeg.get_ffmpeg_exe()
W,H,FPS=1920,1080,24
BG='#14272d'; WHITE='#f6f1e7'; MUTED='#a4b7b6'; ORANGE='#f29165'; GREEN='#a8c997'; RED='#ed8f86'
FONT='/System/Library/Fonts/Supplemental/'
def font(n,bold=False,serif=False):return ImageFont.truetype(FONT+('Baskerville.ttc' if serif else 'Arial Bold.ttf' if bold else 'Arial.ttf'),n)
SCENES=[
 (10,'hook','ONE CHANGE. A BROKEN FUTURE.', 'Mara dies at the end of chapter two. So why is she still speaking in chapter three? One change can break everything that follows.'),
 (10,'brand','BACKFILL FOR STORIES.', 'Every data engineer knows backfill. Novelists call it retcon. Meet RETCON: an Apache Airflow plugin that helps writers follow the consequences of a change.'),
 (12,'workspace','THE WRITER MAKES THE BOLD CHOICE.', 'Here is The Aster Protocol, a five chapter mystery. The revision is simple: Mara dies at the end of chapter two. The writer sets the direction.'),
 (12,'ripple','FOLLOW THE RIPPLE.', 'Three later chapters depend on Mara. But dependency is not the same as contradiction. Chapters three and four contain broken dialogue. Chapter five only remembers her.'),
 (12,'violations','SHOW THE EXACT CONTRADICTION.', 'RETCON quotes the offending paragraphs. A dead character is still speaking. These are deterministic continuity failures, so we know exactly which paragraphs need attention.'),
 (14,'airflow','A REAL WORKFLOW. INSIDE AIRFLOW.', 'An asset event starts the cascade. Airflow checks dependent chapters, maps repairs across the failing paragraphs, and handles retries. This is the actual run, paused at its human approval task.'),
 (14,'diff','TWO PARAGRAPHS. PRECISE REPAIRS.', 'The model proposes focused repairs. In chapter four, Ivo takes over one line of dialogue. The rest of that paragraph stays intact. The writer can compare the original and the proposed text.'),
 (12,'validate','VALIDATE BEFORE THE AUTHOR REVIEWS.', 'The replacements pass the implemented continuity checks before review. Invalid or incomplete repairs cannot publish. Until the author approves, the published manuscript and its canon remain intact.'),
 (12,'approval','THE AUTHOR HAS THE FINAL SAY.', 'Now the writer approves the revision. That decision resumes the native Airflow human in the loop task. The reviewed paragraphs and the new canon are published together.'),
 (12,'memory','A MEMORY IS NOT A CONTRADICTION.', 'Chapter five still remembers Mara. That is valid after her death, so it stays exactly as written. A story can preserve someone without bringing them back to life.'),
 (12,'result','SMALL EDITS. A NEW REALITY.', 'The published result: three chapters checked, two paragraphs repaired, and three chapters untouched. The author can export the manuscript as Markdown, or keep writing the next chapter.'),
 (12,'close','MAKE THE BOLD CHOICE.', 'One plugin. A real Airflow workflow. AI for focused repairs, and a human for the final decision. RETCON. Change the past. Keep your story whole.'),
]

def run(args,**kw):return subprocess.run(args,check=True,**kw)
def wrap(draw,text,f,width):
 lines=[];line=''
 for word in text.split():
  q=(line+' '+word).strip()
  if draw.textlength(q,font=f)>width and line:lines.append(line);line=word
  else:line=q
 if line:lines.append(line)
 return lines
def txt(d,text,xy,size=36,color=WHITE,bold=False,width=None,serif=False,spacing=1.3):
 f=font(size,bold,serif);x,y=xy
 for line in wrap(d,text,f,width) if width else text.split('\n'):
  d.text((x,y),line,font=f,fill=color);y+=int(size*spacing)
 return y
def center(d,text,y,size,color=WHITE,bold=False):
 f=font(size,bold);d.text(((W-d.textlength(text,font=f))/2,y),text,font=f,fill=color)
def pill(d,text,x,y,color=ORANGE):
 f=font(21,True);w=d.textlength(text,font=f)+36
 d.rounded_rectangle((x,y,x+w,y+42),radius=21,outline=color,width=1);d.text((x+18,y+9),text,font=f,fill=color)
def base(i,t):
 im=Image.new('RGB',(W,H),BG);d=ImageDraw.Draw(im)
 for r in range(90,800,90):
  q=int(t*9)%90;d.ellipse((1580-r-q,-200-r-q,1580+r+q,-200+r+q),outline='#21383e',width=2)
 txt(d,'retcon.',(72,35),34,bold=True);txt(d,'APACHE AIRFLOW 3.3  /  HACKATHON DEMO',(1220,49),19,MUTED)
 d.line((72,102,1848,102),fill='#365057',width=1)
 d.rectangle((0,1073,int(W*(sum(s[0] for s in SCENES[:i])+t)/144),1079),fill=ORANGE)
 txt(d,f'{i+1:02d} / 12',(1760,1020),20,MUTED)
 return im,d

def prepare():
 for i,(dur,kind,title,narr) in enumerate(SCENES):
  (OUT/f'voice-{i:02d}.txt').write_text(narr)
 script=[];start=0
 for dur,kind,title,narr in SCENES:
  script.append(f'{start//60}:{start%60:02d}–{(start+dur)//60}:{(start+dur)%60:02d} | {title}\n{narr}\n');start+=dur
 (OUT/'script.md').write_text('# RETCON — 2:24 demo\n\nReal UI captures and completed run; model wait condensed.\n\n'+'\n'.join(script))
 print('Script and narration sources ready.',flush=True)

def voices():
 for i,s in enumerate(SCENES):
  run(['say','-v','Samantha','-r','172' if i in (1,7) else '164','-f',str(OUT/f'voice-{i:02d}.txt'),'-o',str(OUT/f'voice-{i:02d}.aiff')])
  if getdur(i)+.6>s[0]:
   dst=OUT/f'voice-{i:02d}.aiff';tmp=OUT/f'voice-{i:02d}.adjusted.aiff'
   run([FF,'-y','-loglevel','error','-i',str(dst),'-af',f'atempo={getdur(i)/(s[0]-.9):.4f}',str(tmp)])
   tmp.replace(dst)
  print('Voice',i,flush=True)

def render():
 imgs={p.stem:Image.open(p).convert('RGB') for p in CAP.glob('*.png')}
 # Extract only the recorded approval moment, with no changes to application state.
 vf=OUT/'approval-frames';vf.mkdir(exist_ok=True)
 run([FF,'-y','-loglevel','error','-ss','34','-i',str(CAP/'approval.webm'),'-t','12','-vf','fps=24',str(vf/'%04d.jpg')])
 clips=sorted(vf.glob('*.jpg'))
 evidence=json.loads((OUT/'run-evidence.json').read_text())
 para=evidence['run']['patches'][1]
 movie=OUT/'picture.mp4'
 enc=subprocess.Popen([FF,'-y','-loglevel','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(movie)],stdin=subprocess.PIPE)
 def screen(im,key,box,crop=None):
  src=imgs[key] if isinstance(key,str) else key
  if crop:src=src.crop(crop)
  x,y,w,h=box;ratio=min(w/src.width,h/src.height);sz=(int(src.width*ratio),int(src.height*ratio));pic=src.resize(sz,Image.Resampling.LANCZOS)
  im.paste(pic,(int(x+(w-sz[0])/2),int(y+(h-sz[1])/2)))
 def subtitle(d,narr,t,dur):
  words=narr.split();chunks=[' '.join(words[j:j+11]) for j in range(0,len(words),11)]
  # Sentence timing follows measured speech length; captions stay within each shot.
  speech=VOICE_DUR[len(done)] if len(done)<len(VOICE_DUR) else dur-1
  ix=min(len(chunks)-1,int(max(0,t-.5)/max(.01,speech)*len(chunks)))
  if t<.5 or t>speech+1:return
  text=chunks[ix];f=font(29);tw=d.textlength(text,font=f)
  d.rounded_rectangle(((W-tw)/2-24,967,(W+tw)/2+24,1024),radius=12,fill='#0b191e')
  d.text(((W-tw)/2,980),text,font=f,fill=WHITE)
 done=[]
 for i,(dur,kind,title,narr) in enumerate(SCENES):
  for frame in range(dur*FPS):
   t=frame/FPS;im,d=base(i,t);p=min(1,t/1.2);ease=1-(1-p)**3
   if kind=='hook':
    pill(d,'THE ASTER PROTOCOL',76,151)
    txt(d,'Mara dies in',(76,248),102,bold=True);txt(d,'chapter 2.',(76,365),122,ORANGE,bold=True)
    if t>2:
     txt(d,'So why is she still',(80,570),64);txt(d,'speaking in chapter 3?',(80,658),64,bold=True)
    d.rounded_rectangle((1270,280,1780,780),radius=24,fill='#21383e',outline='#466069',width=2)
    txt(d,'CHAPTER 03',(1310,325),24,ORANGE,bold=True)
    txt(d,'“The key opens the lower archive,” Mara said.',(1310,410),48,width=410,serif=True)
    d.line((1310,685,1740,685),fill=RED,width=3);txt(d,'CONTINUITY BROKEN',(1310,717),23,RED,bold=True)
   elif kind=='brand':
    center(d,'retcon.',230,220,bold=True);center(d,'Backfill for stories.',515,73,ORANGE)
    center(d,'Change one fact. Follow every consequence.',659,39)
    pill(d,'AN APACHE AIRFLOW PLUGIN',730,797)
   elif kind=='workspace':
    txt(d,title,(74,145),46,bold=True)
    screen(im,'01-live',(70,240,1250,665))
    txt(d,'THE REVISION',(1360,292),23,ORANGE,bold=True)
    txt(d,'Mara',(1360,356),84,bold=True);txt(d,'dies at the end\nof chapter 2.',(1360,465),44)
    pill(d,'REAL APPLICATION',1360,698)
   elif kind=='ripple':
    txt(d,title,(74,150),62,bold=True);txt(d,'Dependency does not always mean damage.',(78,240),37,MUTED)
    xs=[230,595,960,1325,1690]
    d.line((xs[0],494,xs[-1],494),fill='#4a6267',width=5)
    travel=595+1095*min(1,max(0,t-1)/4)
    if t>1:d.line((595,494,travel,494),fill=ORANGE,width=7)
    for j,x in enumerate(xs):
     color=ORANGE if j==1 else RED if j in (2,3) else GREEN
     lit=t>j*.55
     d.rounded_rectangle((x-125,384,x+125,609),radius=22,fill='#243b40',outline=color if lit else '#4a6267',width=3)
     txt(d,f'CHAPTER {j+1:02d}',(x-89,413),22,MUTED,bold=True)
     txt(d,['Intact','Change','Repair','Repair','Memory'][j],(x-91,472),42,color,bold=True)
     txt(d,['Untouched','Mara dies','Dialogue','Dialogue','Still valid'][j],(x-90,548),24)
    txt(d,'3 chapters checked',(74,740),52,bold=True);txt(d,'Only 2 paragraphs need repair.',(74,814),42,ORANGE)
   elif kind=='violations':
    txt(d,title,(74,145),48,bold=True)
    screen(im,'02-continuity',(65,245,1230,670),crop=(295,285,1030,675))
    txt(d,'DETERMINISTIC\nCHECK',(1350,330),34,ORANGE,bold=True)
    txt(d,'A dead character\ncannot speak.',(1350,465),43)
    txt(d,'Quoted evidence.\nPrecise location.',(1350,647),30,MUTED)
   elif kind=='airflow':
    txt(d,title,(74,145),48,bold=True)
    screen(im,'04-airflow',(75,238,1130,670))
    for j,(a,b) in enumerate([('01','Asset-triggered cascade'),('02','Mapped AI repairs'),('03','Validate replacements'),('04','Native HITL approval')]):
     y=280+j*145;c=ORANGE if j==min(3,int(t/3)) else MUTED
     txt(d,a,(1260,y),29,c,bold=True);txt(d,b,(1320,y),34,width=510)
    txt(d,'Actual run • model wait condensed',(78,921),23,MUTED)
   elif kind=='diff':
    txt(d,title,(74,145),54,bold=True)
    txt(d,'CHAPTER 04  /  PARAGRAPH 4–2',(78,242),25,MUTED,bold=True)
    for x,label,text,col in [(75,'ORIGINAL',para['before'],RED),(990,'PROPOSED',para['after'],GREEN)]:
     d.rounded_rectangle((x,325,x+855,809),radius=22,fill='#21383e',outline='#466069',width=2)
     txt(d,label,(x+35,356),24,col,bold=True)
     txt(d,text,(x+35,439),44,width=778,serif=True,spacing=1.42)
    pill(d,'MARA → IVO',800,844)
   elif kind=='validate':
    txt(d,title,(74,145),48,bold=True)
    screen(im,'03-changes',(65,235,1240,678),crop=(278,70,1390,840))
    for j,s in enumerate(['Focused AI repairs','Rule checks passed','Original draft preserved']):
     y=340+j*150;d.ellipse((1330,y,1363,y+33),fill=GREEN)
     txt(d,s,(1390,y-5),35,width=430)
    txt(d,'Next: the writer decides.',(1328,828),29,ORANGE)
   elif kind=='approval':
    txt(d,title,(74,145),52,bold=True)
    screen(im,'03-changes' if t<5 else '06-published',(65,230,1340,690),crop=(278,50,1395,920))
    txt(d,'REVIEW',(1460,350),28,MUTED,bold=True);txt(d,'Approve.',(1460,412),57,ORANGE,bold=True)
    txt(d,'Resume Airflow.\nPublish together.',(1460,535),33)
    pill(d,'ACTUAL RUN',1460,770)
    txt(d,'Review → publication • elapsed time condensed',(78,925),23,MUTED)
   elif kind=='memory':
    txt(d,title,(74,145),51,bold=True)
    screen(im,'07-memory',(60,245,1270,660),crop=(280,130,1048,685))
    txt(d,'CHAPTER 05',(1370,330),27,GREEN,bold=True)
    txt(d,'She is gone.\nHer memory\nremains.',(1370,430),49)
    pill(d,'UNCHANGED',1370,720,GREEN)
   elif kind=='result':
    txt(d,title,(74,145),62,bold=True);pill(d,'PUBLICATION VERIFIED',76,246,GREEN)
    for x,num,label in [(100,'3','CHAPTERS CHECKED'),(735,'2','PARAGRAPHS REPAIRED'),(1370,'3','CHAPTERS UNTOUCHED')]:
     txt(d,num,(x,346-int(18*(1-ease))),235,ORANGE if num=='2' else GREEN,bold=True)
     txt(d,label,(x+3,627),26,bold=True)
    d.line((78,739,1840,739),fill='#4a6267',width=2)
    txt(d,'Manuscript v2  •  Approved by the author  •  Export as Markdown',(78,804),38)
   elif kind=='close':
    center(d,'retcon.',188,190,bold=True)
    center(d,'Change the past.',447,80,ORANGE)
    center(d,'Keep your story whole.',551,80)
    center(d,'Asset scheduling   /   Mapped AI   /   Human approval',743,34,MUTED)
    center(d,'github.com/abhinavm24/RETCON',846,34)
   subtitle(d,narr,t,dur)
   # Short dip transitions give each chapter a deliberate editorial beat.
   fade=min(1,t/.3,(dur-t)/.3)
   if fade<1:im=Image.blend(Image.new('RGB',(W,H),BG),im,max(0,fade))
   if frame==dur*FPS//2:im.save(OUT/f'preview-{i:02d}.jpg',quality=88)
   enc.stdin.write(im.tobytes())
  done.append(i);print('Rendered',i+1,kind,flush=True)
 enc.stdin.close()
 if enc.wait():raise RuntimeError('Video encoder failed')

def audio():
 # Original quiet ambient score: sine harmonics, a pulse, and soft chapter accents.
 sr=24000;length=144;buf=array.array('h')
 chords=[(110,164.81,220),(98,146.83,196),(130.81,196,261.63),(87.31,130.81,174.61)]
 for n in range(sr*length):
  t=n/sr;ch=chords[int(t//12)%4];env=min(1,t/3,(length-t)/4)
  v=sum(math.sin(2*math.pi*f*t)+.22*math.sin(2*math.pi*f*2*t) for f in ch)/4
  beat=math.exp(-7*(t%1.5))*math.sin(2*math.pi*55*t)
  buf.append(int(32767*env*(.027*v+.009*beat)))
 with wave.open(str(OUT/'score.wav'),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(buf.tobytes())
 args=[FF,'-y','-loglevel','error','-i',str(OUT/'picture.mp4'),'-i',str(OUT/'score.wav')]
 for i in range(12):args+=['-i',str(OUT/f'voice-{i:02d}.aiff')]
 filters=[];at=0
 for i,s in enumerate(SCENES):
  filters.append(f'[{i+2}:a]aresample=48000,volume=1.1,adelay={int((at+.5)*1000)}:all=1[v{i}]');at+=s[0]
 filters.append('[1:a]aresample=48000[bed]')
 filters.append('[bed]'+''.join(f'[v{i}]' for i in range(12))+'amix=inputs=13:duration=longest:normalize=0,alimiter=limit=0.85:level=false[a]')
 args+=['-filter_complex',';'.join(filters),'-map','0:v','-map','[a]','-c:v','copy','-c:a','aac','-b:a','192k','-t','144','-movflags','+faststart',str(OUT/'RETCON-hackathon-demo.mp4')]
 run(args)
 # Portable captions, using speech duration to keep each cue inside its shot.
 lines=[];cue=1;start=0
 def ts(t):
  ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
 for i,(dur,kind,title,narr) in enumerate(SCENES):
  words=narr.split();chunks=[' '.join(words[j:j+11]) for j in range(0,len(words),11)]
  for k,c in enumerate(chunks):
   a=start+.5+VOICE_DUR[i]*k/len(chunks);b=start+.5+VOICE_DUR[i]*(k+1)/len(chunks)
   lines.append(f'{cue}\n{ts(a)} --> {ts(b)}\n{c}\n');cue+=1
  start+=dur
 (OUT/'RETCON-hackathon-demo.srt').write_text('\n'.join(lines))

def getdur(i):
 import re
 p=subprocess.run([FF,'-hide_banner','-i',str(OUT/f'voice-{i:02d}.aiff')],capture_output=True,text=True)
 m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',p.stderr)
 if not m:raise RuntimeError('Voice missing')
 return int(m[1])*3600+int(m[2])*60+float(m[3])

if __name__=='__main__':
 mode=sys.argv[1] if len(sys.argv)>1 else 'prepare'
 if mode=='prepare':prepare()
 elif mode=='voices':voices()
 else:
  VOICE_DUR=[getdur(i) for i in range(12)]
  print('Narration durations:',VOICE_DUR,flush=True)
  for i,d in enumerate(VOICE_DUR):
   if d+.6>SCENES[i][0]:raise RuntimeError(f'Voice {i} exceeds shot: {d}')
  if mode=='render':render();audio()
  elif mode=='audio':audio()
