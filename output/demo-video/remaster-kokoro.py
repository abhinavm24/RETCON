"""Build the Kokoro edition while preserving the original Samantha video."""
from pathlib import Path
import shutil,subprocess,re,json
from functools import lru_cache
import produce as film

HERE=Path(__file__).resolve().parent
DEST=HERE/'kokoro-edition'
DEST.mkdir(exist_ok=True)
film.OUT=DEST
film.font=lru_cache(maxsize=128)(film.font)

def duration(p):
    r=subprocess.run([film.FF,'-hide_banner','-i',str(p)],capture_output=True,text=True)
    m=re.search(r'Duration: (\d+):(\d+):([\d.]+)',r.stderr)
    if not m:raise RuntimeError(f'Cannot read {p}')
    return int(m[1])*3600+int(m[2])*60+float(m[3])

manifest=[]
for i,scene in enumerate(film.SCENES):
    src=HERE/'kokoro'/f'voice-{i:02d}.wav'
    d=duration(src)
    pace=max(1,d/(scene[0]-.9))
    if pace>1.25:raise RuntimeError(f'Scene {i} needs new pacing: {pace}')
    subprocess.run([film.FF,'-y','-loglevel','error','-i',str(src),'-af',f'atempo={pace:.6f},loudnorm=I=-18:TP=-2:LRA=9','-ar','48000',str(DEST/f'voice-{i:02d}.aiff')],check=True)
    manifest.append({'scene':i+1,'source_seconds':d,'tempo_factor':pace,'final_seconds':duration(DEST/f'voice-{i:02d}.aiff')})
shutil.copy2(HERE/'run-evidence.json',DEST/'run-evidence.json')
film.VOICE_DUR=[film.getdur(i) for i in range(12)]
print(json.dumps(manifest,indent=2),flush=True)
(DEST/'narration-manifest.json').write_text(json.dumps({'engine':'Kokoro-82M','voice':'af_heart','service':'https://huggingface.co/spaces/hexgrad/Kokoro-TTS','clips':manifest},indent=2))
film.prepare()
film.render()
film.audio()
(DEST/'README.md').write_text('''# RETCON — Kokoro narration edition

2:24, 1920×1080, 24 fps. The visuals and verified application results are preserved, with newly generated Kokoro-82M Heart (af_heart) narration from the official free Hugging Face demo. Caption timings follow the new clips. Scene pacing is adjusted without changing pitch, and speech levels are normalized before mixing with the original music.

The prior Samantha version remains in the parent directory. Raw Kokoro audio is in ../kokoro/. See narration-manifest.json for per-scene timing and processing. Rebuild from the parent directory with `python remaster-kokoro.py`.
''')
