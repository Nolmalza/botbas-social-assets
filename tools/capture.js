// usage: node capture.js <html> <out.mp4|--stills t1,t2,...> [duration=12]
const puppeteer = require('puppeteer-core');
const { spawn } = require('child_process');
const path = require('path');
(async () => {
  const [html, out, durArg] = process.argv.slice(2);
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME || '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-gpu', '--allow-file-access-from-files'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920 });
  await page.goto('file://' + path.resolve(html), { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  if (out === '--stills') {
    for (const t of durArg.split(',')) {
      await page.evaluate(x => window.render(x), +t);
      await page.screenshot({ path: `still_${t}.jpg`, type: 'jpeg', quality: 92 });
    }
  } else {
    const dur = +(durArg || 12), fps = 30;
    const tmp = out.replace(/\.mp4$/, '.part.mp4');
    const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp],
      { stdio: ['pipe', 'ignore', 'inherit'] });
    for (let i = 0; i < dur * fps; i++) {
      await page.evaluate(x => window.render(x), i / fps);
      const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
    ff.stdin.end();
    const code = await new Promise(r => ff.on('close', r));
    if (code !== 0) process.exit(code);
    require('fs').renameSync(tmp, out);
  }
  await browser.close();
})();
