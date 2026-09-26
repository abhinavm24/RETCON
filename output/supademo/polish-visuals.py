"""Reduce UI glare and remove the on-screen narration credit.

The approved ElevenLabs audio and subtitle streams are copied without re-encoding.
Free-plan attribution is retained in the MP4 title and publishing instructions.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parent
BUILD=ROOT/'final-build'
OUT=ROOT/'contrast-build';OUT.mkdir(exist_ok=True)
FF=imageio_ffmpeg.get_ffmpeg_exe()
ORIGINAL=ROOT/'RETCON-final-elevenlabs.io.mp4'
TIMING=json.loads((BUILD/'timing.json').read_text())
CURVE='curves=master=0/0 0.25/0.17 0.5/0.40 0.75/0.65 1/0.92'
COLOR=['-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709']

def render(i):
    dst=OUT/f'scene-{i:02d}.mp4';duration=TIMING['scenes'][i]['duration']
    args=[FF,'-y','-loglevel','error']
    if i in (0,11):
        card=ROOT/'review-cut'/('opening.png' if i==0 else 'closing.png')
        args+=['-loop','1','-framerate','30','-i',str(card)]
        filt=f'setsar=1,fade=t=in:st=0:d=0.15,fade=t=out:st={duration-.15}:d=0.15,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'
    else:
        args+=['-i',str(BUILD/f'scene-{i:02d}.mp4')]
        filt=CURVE+',eq=saturation=1.08,unsharp=5:5:0.3:3:3:0,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'
    args+=['-vf',filt,'-t',str(duration),'-an','-r','30','-c:v','libx264','-preset','fast','-crf','18','-threads','2']+COLOR+[str(dst)]
    subprocess.run(args,check=True)
    print('Rendered',i+1,flush=True)
    return dst

with ThreadPoolExecutor(max_workers=3) as pool:parts=list(pool.map(render,range(12)))
concat=OUT/'segments.txt';concat.write_text(''.join(f"file '{p.name}'\n" for p in parts))
picture=OUT/'picture.mp4'
subprocess.run([FF,'-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy',str(picture)],check=True)
final=ROOT/'RETCON-final.mp4'
subprocess.run([FF,'-y','-loglevel','error','-i',str(picture),'-i',str(ORIGINAL),'-map','0:v','-map','1:a','-map','1:s','-c','copy','-bsf:v','h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0','-metadata','title=RETCON — Backfill for stories | elevenlabs.io','-movflags','+faststart',str(final)],check=True)
(ROOT/'final-delivery.md').write_text('''# RETCON final video

File: `RETCON-final.mp4` — 2:23, 1920×1080, 30 fps.

UI highlights are reduced, text/colour contrast strengthened, and BT.709 colour metadata is explicit. Opening and closing cards retain their original design. There is no on-screen ElevenLabs credit.

The approved Generation 2 audio and the subtitle track are copied directly from the prior final video: no additional pauses, speed changes, or audio re-encoding.

Suggested public upload title: **RETCON — Backfill for stories | elevenlabs.io**

ElevenLabs requires free-plan attribution in the published title; embedded MP4 metadata alone does not replace the platform's upload title. Source: https://help.elevenlabs.io/hc/en-us/articles/13313564601361-Can-I-publish-the-content-I-generate-on-the-platform
''')
print('FINAL:',final,flush=True)
