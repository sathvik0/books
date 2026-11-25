// Usage: node render.js <buildDir> <mode> [...]
//   preview t1 t2 ...    -> PNG stills
//   video <from> <to> <out.mp4>  -> frame range encoded to H.264
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const [B, mode, ...rest] = process.argv.slice(2);
const FPS = 30;
(async () => {
  const TL = JSON.parse(fs.readFileSync(path.join(B, 'timeline.json')));
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(__dirname, 'scenes.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(tl => window.init(tl), TL);
  if (mode === 'preview') {
    for (const t of rest) {
      await page.evaluate(t => window.render(t), parseFloat(t));
      await page.screenshot({ path: path.join(B, `prev_${t}.png`) });
    }
  } else {
    const [from, to, out] = [parseInt(rest[0]), parseInt(rest[1]), rest[2]];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-tune', 'animation', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let f = from; f < to; f++) {
      await page.evaluate(t => window.render(t), f / FPS);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();
