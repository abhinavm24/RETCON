"""Generate user-approved narration through the public Kokoro UI."""
from pathlib import Path
import json,subprocess,re,urllib.request

HERE=Path(__file__).resolve().parent
CLI=['node','/private/var/folders/dm/16fx5vyj1231zs8s1kb8gkph0000gp/T/bunx-502-@playwright/cli@latest/node_modules/@playwright/cli/playwright-cli.js']
for i in range(1,12):
    dst=HERE/'kokoro'/f'voice-{i:02d}.wav'
    if dst.exists():continue
    narration=(HERE/f'voice-{i:02d}.txt').read_text()
    code='''async page => {
      const selector = 'a[href*="/gradio_api/file="]';
      const previous = await page.locator(selector).first().getAttribute('href');
      await page.getByRole('textbox', {name:'Input Text',exact:false}).fill(TEXT);
      await page.getByRole('button', {name:'Generate',exact:true}).click();
      await page.waitForFunction(previous => Array.from(document.querySelectorAll('a')).some(a => a.href.includes('/gradio_api/file=') && a.getAttribute('href') !== previous),previous,{timeout:60000});
      console.log('AUDIO_URL='+await page.locator(selector).first().getAttribute('href'));
    }'''.replace('TEXT',json.dumps(narration))
    p=subprocess.run(CLI+['-s=retcon-narration','run-code',code],capture_output=True,text=True)
    if p.returncode or '### Error' in p.stdout:
        print(p.stdout[-2000:],p.stderr[-1000:],flush=True)
        raise SystemExit(f'Generation stopped at scene {i}')
    p=subprocess.run(CLI+['-s=retcon-narration','eval','() => Array.from(document.querySelectorAll("a")).map(a => a.href).filter(h => h.includes("/gradio_api/file="))'],capture_output=True,text=True)
    urls=re.findall(r'https://hexgrad-kokoro-tts.hf.space/gradio_api/file=[^\s\"\x27]+',p.stdout)
    if p.returncode or not urls:
        print(p.stdout[-2000:],p.stderr[-1000:],flush=True)
        raise SystemExit(f'Generation stopped at scene {i}')
    urllib.request.urlretrieve(urls[0],dst)
    print(f'Scene {i+1}/12 saved: {dst.name} ({dst.stat().st_size} bytes)',flush=True)
