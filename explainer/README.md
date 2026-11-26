# CE Targeting Process — animated explainer

`CE_Targeting_Explainer.mp4`: 1920×1080, 30 fps, H.264 + AAC, ~100 s.

## Rebuild
1. `pip install kokoro-onnx soundfile scipy` and download `kokoro-v1.0.onnx` + `voices-v1.0.bin`
   (github.com/thewh1teagle/kokoro-onnx releases) into `<models>`.
2. `python3 tts.py <models> <build>`: voiceover (voice `af_heart`, acronyms spelled out via phonemes).
3. `python3 timeline_audio.py <build>`: scene timing (`timeline.json`) plus the VO mixed with a ducked ambient pad (`mix.wav`).
4. `node render.js <build> preview 12.5 30`: stills; `node render.js <build> video <fromFrame> <toFrame> out.mp4` renders frames.
5. Mux the video with `mix.wav` in ffmpeg.

All visuals live in `scenes.html` (black background, orange accent, white/grey text and boxes; IBM Plex in `fonts/`). Elements are cued to narration words with `data-at="w:<sentence>:<word>"`.
