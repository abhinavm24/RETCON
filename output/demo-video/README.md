# RETCON hackathon demo

**Final:** `RETCON-hackathon-demo.mp4` — 2:24, 1920×1080, 24 fps, H.264/AAC.

The film combines animated editorial graphics, full-resolution captures of the actual application, synthetic English narration, burned-in captions, and a quiet original synthesized soundtrack. The separate `.srt` file contains portable captions. `script.md` contains the timed narration.

## Evidence

This film uses the real Aster Protocol revision `70db4286e6ac46a0`, with OpenRouter model `google/gemma-4-31b-it:free`. The user initiated its repair run; the video task reviewed the actual replacements and approved publication through the writer UI. The final state was verified as `published`, manuscript version 2, with 3 chapters checked, 2 paragraphs repaired, and 3 chapters untouched. Chapter 5 was compared with the pre-recording manuscript and found identical.

The Airflow screenshot shows this actual asset-triggered cascade awaiting native HITL input. The approval sequence uses captured review and publication states; waits are condensed and labeled. No model response or application result was fabricated. `run-evidence.json` and the exported manuscript preserve the result.

## Reproduce

On macOS, use a Python environment with Pillow and imageio-ffmpeg. Full-resolution source captures are in `../playwright/`.

```sh
python produce.py prepare
python produce.py voices
python produce.py render
```

Narration uses the locally installed Samantha voice. The renderer uses local macOS fonts. Intermediate audio, previews, and source captures are included for editing. No credentials are included.

The live sample remains published. The recording used the project's existing OpenRouter connection, and the previously saved local sample and configuration were backed up under the ignored `.retcon/video-backup/` directory.
