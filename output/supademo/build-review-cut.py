"""Edit the supplied Supademo MP4 into a silent 2:16 visual review cut.

Uses source video segments, not reconstructed application screenshots.
Only opening/closing cards and small editorial labels are generated.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json
from PIL import Image,ImageDraw,ImageFont
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'2026-09-24, 07_08_13 p.m.-RETCON___Backfill_for_stories.mp4'
OUT=ROOT/'review-cut';OUT.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe()
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
BOLD='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
BG='#14272d';WHITE='#f6f1e7';ACCENT='#f29165';GREEN='#a8c997'
def text(d,s,x,y,n=40,color=WHITE,bold=False):
    d.text((x,y),s,font=ImageFont.truetype(BOLD if bold else FONT,n),fill=color)
def card(name,opening):
    im=Image.new('RGB',(1920,1080),BG);d=ImageDraw.Draw(im)
    for r in range(160,1300,130):d.ellipse((1650-r,-220-r,1650+r,-220+r),outline='#243b41',width=2)
    text(d,'retcon.',90,65,50,bold=True)
    text(d,'BACKFILL FOR STORIES',90,155,26,ACCENT,True)
    if opening:
        text(d,'Mara dies in',90,310,108,bold=True)
        text(d,'chapter 2.',90,435,124,ACCENT,True)
        text(d,'Why is she still speaking',90,655,69)
        text(d,'in chapter 3?',90,745,69,bold=True)
        text(d,'ONE CHANGE. FOLLOW EVERY CONSEQUENCE.',90,960,26,'#afc1c1')
    else:
        for x,n,label in [(90,'3','CHAPTERS CHECKED'),(730,'2','PARAGRAPHS REPAIRED'),(1370,'3','CHAPTERS UNTOUCHED')]:
            text(d,n,x,295,220,ACCENT if n=='2' else GREEN,True)
            text(d,label,x,560,27,bold=True)
        text(d,'Change the past. Keep your story whole.',90,750,65,bold=True)
        text(d,'github.com/abhinavm24/RETCON',90,935,33,'#afc1c1')
    im.save(OUT/name)
card('opening.png',True);card('closing.png',False)

# Supademo export: each original chapter/step occupies approximately 4 seconds.
# Skip the tiny horizontal graph, grid detour, duplicate continuity and review views.
SCENES=[
 ('opening',None,10,'Mara dies in chapter 2. Why is she still speaking?'),
 ('workspace',4.05,8,'THE ASTER PROTOCOL'),
 ('change',12.05,12,'CHANGE ONE FACT: MARA DIES AFTER CHAPTER 2'),
 ('preview',16.05,16,'3 CHAPTERS AFFECTED. 2 DIALOGUE FAILURES.'),
 ('workflow',20.05,8,'REAL AIRFLOW RUN  |  MODEL WAIT CONDENSED'),
 ('graph',36.05,12,'ASSET-TRIGGERED WORKFLOW  |  REPAIRS VALIDATED'),
 ('approval-task',40.05,12,'NATIVE AIRFLOW HITL  |  AWAITING AUTHOR INPUT'),
 ('review',48.05,12,'REVIEW THE ORIGINAL AND PROPOSED PARAGRAPHS'),
 ('approve',52.05,12,'THE AUTHOR DECIDES WHAT BECOMES CANON'),
 ('published',56.05,12,'PUBLISHED: CANON AND APPROVED TEXT TOGETHER'),
 ('memory',60.05,12,'CHAPTER 5 REMEMBERS MARA. IT STAYS UNCHANGED.'),
 ('closing',None,10,'3 checked / 2 repaired / 3 untouched'),
]

def render(item):
    i,(name,start,duration,label)=item
    dst=OUT/f'{i:02d}-{name}.mp4'
    args=[FF,'-y','-hide_banner','-loglevel','error']
    if start is None:
        args+=['-loop','1','-framerate','30','-i',str(OUT/f'{name}.png')]
        filt=f'fade=t=in:st=0:d=0.25,fade=t=out:st={duration-.25}:d=0.25'
    else:
        args+=['-ss',str(start),'-t','3.8','-i',str(SOURCE)]
        labelpath=OUT/f'{i:02d}-label.txt';labelpath.write_text(label)
        filt=(f'scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2,'
              f'pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=0x14272d,setsar=1,'
              f'tpad=stop_mode=clone:stop_duration={duration-3.8},'
              f'drawtext=fontfile={FONT}:textfile={labelpath}:fontsize=25:fontcolor=white:'
              f'x=30:y=1027:box=1:boxcolor=0x14272d@0.93:boxborderw=13,'
              f'fade=t=in:st=0:d=0.15,fade=t=out:st={duration-.15}:d=0.15')
    args+=['-vf',filt,'-t',str(duration),'-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-threads','2',str(dst)]
    subprocess.run(args,check=True)
    print(f'Rendered {i+1}/12: {name}',flush=True)
    return dst

with ThreadPoolExecutor(max_workers=3) as pool:segments=list(pool.map(render,enumerate(SCENES)))
concat=OUT/'segments.txt';concat.write_text(''.join(f"file '{p.name}'\n" for p in segments))
final=ROOT/'RETCON-Supademo-visual-review-2m16s.mp4'
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(final)],check=True)
at=0;lines=['# RETCON — silent visual review cut','',f'Source: `{SOURCE.name}`','',
 'Duration: 2:16. Output: 1920×1080, 30 fps, no audio. Original export preserved.',
 'Application scenes use the supplied Supademo video, retaining its native framing and animations. Holds provide reading/narration time. Only title cards and editorial labels are added.',
 '', '| Time | Scene | Source start |','|---|---|---|']
for name,start,dur,label in SCENES:
    lines.append(f'| {at//60}:{at%60:02d}–{(at+dur)//60}:{(at+dur)%60:02d} | {label} | {start if start is not None else "Title card"} |');at+=dur
(ROOT/'visual-review-cut.md').write_text('\n'.join(lines)+'\n')
print('Finished:',final,flush=True)
