# Renders every reels/*.json into videos/<name>__<voice>.mp4 (skips ones that exist).
# json: {"html": "reels/x.html", "text": "Thai voice-over", "voices": ["th-TH-NiwatNeural"], "duration": 12, "seed": 7}
import glob, json, os, subprocess, sys

def run(*a):
    print('+', ' '.join(a)[:200], flush=True)
    subprocess.run(a, check=True)

def length(p):
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p],
                         capture_output=True, text=True).stdout.strip()
    return float(out or 0)

os.makedirs('videos', exist_ok=True)
failed = False
for cfg in sorted(glob.glob('reels/*.json')):
    name = os.path.basename(cfg)[:-5]
    c = json.load(open(cfg, encoding='utf-8'))
    for voice in c.get('voices') or ['th-TH-NiwatNeural']:
        short = voice.split('-')[-1].replace('Neural', '').lower()
        out = f'videos/{name}__{short}.mp4'
        if os.path.exists(out):
            continue
        try:
            v = '/tmp/voice.mp3'
            has_voice = True
            try:
                run('edge-tts', '--voice', voice, '--rate', c.get('rate', '+8%'), '--text', c['text'], '--write-media', v)
                has_voice = length(v) > 0.5
            except Exception as e:
                print('TTS failed, music only:', e); has_voice = False
            dur = max(float(c.get('duration', 12)), (length(v) + 2.0) if has_voice else 0)
            dur = round(dur, 2)
            run('node', 'tools/capture.js', c['html'], '/tmp/silent.mp4', str(dur))
            run('python3', 'tools/music.py', '/tmp/music.wav', str(dur), str(c.get('seed', 7)))
            tmp = out[:-4] + '.part.mp4'
            if has_voice:
                fc = ('[1:a]adelay=500|500,aresample=44100,aformat=channel_layouts=stereo,volume=1.6,apad,asplit=2[vo][sc];'
                      '[2:a]volume=0.32[mu];[mu][sc]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[duck];'
                      f'[duck][vo]amix=inputs=2:duration=first:normalize=0,afade=t=out:st={dur-1.2}:d=1.2[a]')
                run('ffmpeg', '-y', '-v', 'error', '-i', '/tmp/silent.mp4', '-i', v, '-i', '/tmp/music.wav',
                    '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                    '-t', str(dur), '-movflags', '+faststart', tmp)
            else:
                run('ffmpeg', '-y', '-v', 'error', '-i', '/tmp/silent.mp4', '-i', '/tmp/music.wav',
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k',
                    '-af', 'volume=0.6', '-t', str(dur), '-movflags', '+faststart', tmp)
            os.replace(tmp, out)
            print('done', out)
        except Exception as e:
            print('FAILED', out, e); failed = True
sys.exit(1 if failed else 0)
