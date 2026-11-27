#!/usr/bin/env python3
"""تنزيل بوت: Telegram long-polling bot. Stdlib only. Token read from TOKEN_FILE, never printed."""
import uuid
import tempfile, json, os, re, subprocess, sys, threading, time, uuid, urllib.parse, urllib.request, urllib.error, mimetypes, shutil
from concurrent.futures import ThreadPoolExecutor

TOKEN = open(os.environ['TOKEN_FILE']).read().strip()
SB = 'https://dinlporwlqeoyvllhapo.supabase.co/rest/v1/rpc/'
SB_ANON = open('/home/sandbox/.sb_anon').read().strip()
SB_BOT = open('/home/sandbox/tnzl-bot/.bot_secret').read().strip()
LOCAL = os.path.exists('/home/sandbox/tnzl-bot/local_mode')   # self-hosted Bot API server: 2000 MB uploads
API = f'http://127.0.0.1:8081/bot{TOKEN}/' if LOCAL else f'https://api.telegram.org/bot{TOKEN}/'
LIMIT = (1990 if LOCAL else 49) * 1024 * 1024
LIMIT_M = '1990M' if LOCAL else '49M'
LIMIT_TXT = '2 جيجا' if LOCAL else '50 ميجا'
WORK = '/tmp/tnzlbot'
os.makedirs(WORK, exist_ok=True)
POOL = ThreadPoolExecutor(max_workers=4)
JOBS = {}          # job id -> dict(url, options, chat, title)
BUSY = set()
QUEUED = {}
CHAT_LOCKS = {}       # chats with an active download
URL_RE = re.compile(r'https?://[^\s<>"]+')
UA = 'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36'


def sb(fn, **a):
    """Call a mailbox function. Returns parsed JSON or raises RuntimeError with a short code (never the payload)."""
    r = urllib.request.Request(SB + fn, json.dumps(a).encode(), {'apikey': SB_ANON, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=20) as f:
            b = f.read().decode()
            return json.loads(b) if b else None
    except urllib.error.HTTPError as e:
        raise RuntimeError('rate' if 'rate_limited' in e.read().decode() else f'http{e.code}')
    except Exception:
        raise RuntimeError('net')


USERS = {}     # chat -> {'name':..., 'skipped':bool} cache; durable copy lives in Supabase tnzl_users
PENDING = set()  # chats we asked "اسمك إيه" and wait for a reply
YT_RE = re.compile(r'^https?://([\w-]+\.)*(youtube\.com|youtu\.be|youtube-nocookie\.com)(/|$)', re.I)


def get_user(chat):
    k = str(chat)
    if k in USERS:
        return USERS[k]
    try:
        r = sb('tnzl_user_get', p_bot=SB_BOT, p_chat=chat)
    except RuntimeError:
        return {'net': True}
    if r:
        USERS[k] = {'name': r.get('name'), 'skipped': bool(r.get('skipped'))}
        return USERS[k]
    return None


def set_user(chat, name, skipped=False):
    try:
        sb('tnzl_user_set', p_bot=SB_BOT, p_chat=chat, p_name=name, p_skipped=skipped)
    except RuntimeError:
        return False
    USERS[str(chat)] = {'name': name, 'skipped': skipped}
    return True


def uname(chat):
    u = get_user(chat) or {}
    return u.get('name') or ''


STATE = '/home/sandbox/tnzl-bot/state.json'
START = time.time()
HIST = {}   # chat -> [{'t': title, 'u': url}]
_lock = threading.Lock()


_PUSHED = {}


def push_state():
    """Mirror per-chat history/stats to Supabase (durable across sandbox resets). Only changed chats are sent."""
    for ch in set(list(HIST) + list(STATS)):
        snap = json.dumps([HIST.get(ch, []), STATS.get(ch, {})], sort_keys=True)
        if _PUSHED.get(ch) == snap:
            continue
        try:
            sb('tnzl_state_set', p_bot=SB_BOT, p_chat=int(ch), p_hist=HIST.get(ch, []), p_stats=STATS.get(ch, {}))
            _PUSHED[ch] = snap
        except Exception:
            pass


def pull_state():
    try:
        rows = sb('tnzl_state_all', p_bot=SB_BOT) or []
    except Exception:
        return
    for r in rows:
        ch = str(r['chat'])
        st = r.get('stats') or {}
        if ch not in STATS or (st.get('ok', 0) + st.get('fail', 0)) > (STATS[ch].get('ok', 0) + STATS[ch].get('fail', 0)):
            STATS[ch] = st
            HIST[ch] = r.get('hist') or []
        _PUSHED[ch] = json.dumps([HIST.get(ch, []), STATS.get(ch, {})], sort_keys=True)


def save_state():
    threading.Thread(target=push_state, daemon=True).start()
    with _lock:
        try:
            jobs = dict(list(JOBS.items())[-100:])
            tmp = STATE + '.tmp'
            with open(tmp, 'w') as f:
                json.dump({'jobs': jobs, 'hist': HIST, 'stats': STATS}, f)
            os.replace(tmp, STATE)
        except Exception:
            pass


def load_state():
    try:
        d = json.load(open(STATE))
        JOBS.update(d.get('jobs', {}))
        HIST.update(d.get('hist', {}))
        STATS.update(d.get('stats', {}))
    except Exception:
        pass


def safe_name(t):
    t = re.sub(r'[\\/:*?"<>|\n\r\t#]+', ' ', t or 'video').strip()
    t = re.sub(r'\s+', ' ', t)[:60].strip(' .')
    return t or 'video'


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def api(method, params=None, timeout=60):
    data = json.dumps(params or {}).encode()
    req = urllib.request.Request(API + method, data, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {'ok': False, 'description': str(e.code)}
    except Exception as e:
        return {'ok': False, 'description': type(e).__name__}


def send(chat, text, markup=None):
    p = {'chat_id': chat, 'text': text, 'disable_web_page_preview': True}
    if markup:
        p['reply_markup'] = markup
    r = api('sendMessage', p)
    if not r.get('ok'):
        log('sendMessage failed', r.get('description'))
    return r


def edit(chat, mid, text, markup=None):
    p = {'chat_id': chat, 'message_id': mid, 'text': text}
    if markup:
        p['reply_markup'] = markup
    r = api('editMessageText', p)
    if not r.get('ok') and 'no text' in str(r.get('description', '')):
        p2 = {'chat_id': chat, 'message_id': mid, 'caption': text[:1000]}
        if markup:
            p2['reply_markup'] = markup
        r = api('editMessageCaption', p2)
    return r


def upload(method, field, chat, path, extra=None):
    if LOCAL:
        p = {'chat_id': chat, field: 'file://' + os.path.abspath(path), **(extra or {})}
        return api(method, p, 3600)
    b = '----tnzl' + uuid.uuid4().hex
    parts = []
    for k, v in {'chat_id': str(chat), **(extra or {})}.items():
        parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    name = os.path.basename(path)
    mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="{field}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
    body_head = b''.join(parts)
    tail = f'\r\n--{b}--\r\n'.encode()
    size = os.path.getsize(path)

    class Body:
        def __init__(s):
            s.f = open(path, 'rb'); s.stage = 0; s.pos = 0
        def read(s, n=-1):
            if s.stage == 0:
                s.stage = 1; return body_head
            if s.stage == 1:
                d = s.f.read(1 << 16)
                if d: return d
                s.stage = 2; s.f.close(); return tail
            return b''
    req = urllib.request.Request(API + method, Body(), {'Content-Type': f'multipart/form-data; boundary={b}', 'Content-Length': str(len(body_head) + size + len(tail))})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except Exception:
            return {'ok': False, 'description': str(e.code)}
    except Exception as e:
        return {'ok': False, 'description': type(e).__name__}


def mb(n):
    if not n:
        return 'الحجم يظهر بعد البدء'
    if n < 1048576:
        return f'{max(1, round(n/1024))} كيلوبايت'
    return f'{n/1048576:.1f} ميجا'


def est(f, d):
    n = f.get('filesize') or f.get('filesize_approx') or 0
    if not n:
        br = f.get('tbr') or f.get('abr') or 0
        du = d.get('duration') or 0
        if br and du:
            n = int(br * 1000 / 8 * du)
    return n


def head_size(url):
    # actual size from the server (Content-Length), 0 if not available
    try:
        r = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
        with urllib.request.urlopen(r, timeout=8) as x:
            return int(x.headers.get('Content-Length') or 0)
    except Exception:
        try:
            r = urllib.request.Request(url, headers={'User-Agent': UA, 'Range': 'bytes=0-0'})
            with urllib.request.urlopen(r, timeout=8) as x:
                cr = x.headers.get('Content-Range') or ''
                return int(cr.split('/')[-1]) if '/' in cr and cr.split('/')[-1].isdigit() else 0
        except Exception:
            return 0


def http_json(url, data=None, timeout=25):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode() if data else None, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


# ---------- extractors ----------
def probe_tiktok(url):
    d = http_json('https://www.tikwm.com/api/', {'url': url, 'hd': 1})
    if d.get('code') != 0:
        raise RuntimeError('tiktok')
    x = d['data']
    META[url] = {'thumb': x.get('cover') or x.get('origin_cover'), 'dur': x.get('duration'), 'by': (x.get('author') or {}).get('nickname')}
    opts = []
    if x.get('hdplay'):
        opts.append({'key': 'hd', 'label': 'جودة عالية بدون علامة مائية', 'size': x.get('hd_size') or 0, 'kind': 'video', 'src': x['hdplay']})
    if x.get('play'):
        opts.append({'key': 'sd', 'label': 'جودة عادية بدون علامة مائية', 'size': x.get('size') or 0, 'kind': 'video', 'src': x['play']})
    if x.get('music'):
        opts.append({'key': 'au', 'label': 'الصوت فقط', 'size': 0, 'kind': 'audio', 'src': x['music']})
    for o in opts:
        real = head_size(o['src'])
        if real > 50000:
            o['size'] = real
        elif o['size'] and o['size'] < 50000:
            o['size'] = 0
    return (x.get('title') or 'TikTok')[:80], opts


def ytdlp(args, timeout=120):
    return subprocess.run(['yt-dlp', '--no-warnings', '--no-playlist', *args], capture_output=True, text=True, timeout=timeout)


def ytdlp_progress(args, timeout, cb):
    p = subprocess.Popen(['yt-dlp', '--no-warnings', '--no-playlist', '--newline', '--progress-template', 'PR %(progress.downloaded_bytes)s %(progress.total_bytes)s %(progress.total_bytes_estimate)s', *args],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = []
    t0 = time.time()
    try:
        for line in p.stdout:
            if line.startswith('PR '):
                try:
                    _, d, t1, t2 = line.split()
                    tot = int(t1) if t1.isdigit() else (int(float(t2)) if t2.replace('.', '').isdigit() else 0)
                    cb(int(float(d)), tot)
                except Exception:
                    pass
            else:
                out.append(line)
            if time.time() - t0 > timeout:
                p.kill()
                break
    finally:
        p.wait()
    return p.returncode, ''.join(out)


def probe_ytdlp(url):
    r = ytdlp(['-J', url], 90)
    if r.returncode != 0 and re.search(r'instagram\.com/(?:reels?|tv)/([\w-]+)', url):
        m = re.search(r'instagram\.com/(?:reels?|tv)/([\w-]+)', url)
        r = ytdlp(['-J', f'https://www.instagram.com/p/{m.group(1)}/'], 90)
    if r.returncode != 0:
        err = (r.stderr or '')
        if 'Sign in' in err or 'bot' in err:
            raise RuntimeError('yt-blocked')
        if 'login' in err.lower() or 'cookies' in err.lower():
            raise RuntimeError('login')
        raise RuntimeError('fail')
    d = json.loads(r.stdout)
    META[url] = {'thumb': d.get('thumbnail'), 'dur': d.get('duration'), 'by': d.get('uploader') or d.get('channel')}
    fm = d.get('formats') or []
    aud = max([est(f, d) for f in fm if f.get('vcodec') == 'none'] or [0])
    best = {}
    for f in fm:
        h = f.get('height')
        if not h or f.get('vcodec') in (None, 'none') or h > 1080:
            continue
        sz = est(f, d)
        has_a = f.get('acodec') not in (None, 'none')
        tot = sz + (0 if has_a else aud) if sz else 0
        if h not in best or (tot and tot < best[h]) or not best[h]:
            best[h] = tot
    opts = [{'key': f'h{h}', 'label': f'{h}p', 'size': s, 'kind': 'video', 'h': h} for h, s in sorted(best.items())][-4:]
    if not opts:
        seen = set()
        for f in fm:
            fid = str(f.get('format_id'))
            if f.get('vcodec') == 'none' or f.get('acodec') == 'none' and not f.get('vcodec') or f.get('ext') not in ('mp4', 'webm', 'mov') or fid in seen:
                continue
            if f.get('protocol') in ('mhtml',):
                continue
            seen.add(fid)
            lab = {'hd': 'جودة عالية', 'sd': 'جودة عادية'}.get(fid.lower(), fid)
            opts.append({'key': 'f' + fid[:20], 'label': lab, 'size': est(f, d), 'kind': 'video', 'fid': fid})
        opts = opts[-3:]
    if any(f.get('vcodec') == 'none' for f in fm):
        opts.append({'key': 'au', 'label': 'الصوت فقط (MP3)', 'size': aud, 'kind': 'audio'})
    return (d.get('title') or 'video')[:80], opts


META = {}        # url -> {'thumb','dur','by'}
PCACHE = {}      # url -> (time, title, opts)
STATS = {}       # chat -> {'ok': n, 'fail': n}


def human_err(e):
    e = str(e)
    return {
        'yt-blocked': 'يوتيوب غير متاح في البوت حاليًا (بيحجب الخوادم). جرّب تيك توك أو إنستجرام أو إكس.',
        'login': 'الرابط ده خاص أو محتاج تسجيل دخول، والبوت بيشتغل مع الروابط العامة بس.',
        'tiktok': 'مقدرتش أجيب فيديو تيك توك ده. تأكد إنه عام وما اتحذفش.',
        'net': 'في مشكلة اتصال مؤقتة. جرّب بعد دقيقة.',
    }.get(e, 'مقدرتش أقرأ الرابط ده. تأكد إنه فيديو عام وجرّب تاني.')


def probe(url):
    c = PCACHE.get(url)
    if c and time.time() - c[0] < 600:
        return c[1], c[2]
    t, o = _probe(url)
    PCACHE[url] = (time.time(), t, o)
    if len(PCACHE) > 100:
        for k in list(PCACHE)[:50]:
            PCACHE.pop(k, None)
    return t, o


def _probe(url):
    host = urllib.parse.urlparse(url).netloc.lower()
    if 'tiktok.com' in host:
        return probe_tiktok(url)
    return probe_ytdlp(url)


# ---------- download ----------
def fetch(src, path, cb=None):
    req = urllib.request.Request(src, headers={'User-Agent': UA})
    n = 0
    with urllib.request.urlopen(req, timeout=40) as r, open(path, 'wb') as f:
        total = int(r.headers.get('Content-Length') or 0)
        while True:
            c = r.read(1 << 16)
            if not c:
                break
            n += len(c)
            if cb:
                cb(n, total)
            if n > LIMIT:
                raise RuntimeError('toobig')
            f.write(c)
    return path


def do_download(url, o, d, cb=None, maxm=None):
    base = os.path.join(d, 'f')
    if o.get('src'):
        return fetch(o['src'], base + ('.mp3' if o['kind'] == 'audio' else '.mp4'), cb)
    if o['kind'] == 'audio':
        rc, so = ytdlp_progress(['-x', '--audio-format', 'mp3', '--audio-quality', '5', '--max-filesize', maxm or LIMIT_M, '-o', base + '.%(ext)s', url], 600, cb or (lambda a, b: None))
    else:
        if o.get('fid'):
            sel = f"{o['fid']}+ba/{o['fid']}/b"
        else:
            h = o['h']
            sel = f'bv*[height<={h}]+ba/b[height<={h}]/b'
        rc, so = ytdlp_progress(['-f', sel, '--merge-output-format', 'mp4', '--max-filesize', maxm or LIMIT_M, '-o', base + '.%(ext)s', url], 900, cb or (lambda a, b: None))
    fs = [x for x in os.listdir(d) if x.startswith('f.')]
    if rc != 0 or not fs:
        if 'larger than' in so or 'max-filesize' in so:
            raise RuntimeError('toobig')
        raise RuntimeError('fail')
    return os.path.join(d, fs[0])


def run_job(chat, mid, jid, key, as_doc=False):
    job = JOBS.get(jid)
    o = next((x for x in (job or {}).get('options', []) if x['key'] == key), None)
    if not job or not o:
        log('job', 'stale')
        send(chat, 'انتهت صلاحية الطلب، ابعت الرابط من جديد.')
        return
    if QUEUED.get(chat, 0) >= 3:
        send(chat, 'عندك 3 تنزيلات في الطابور، استنى لما يخلصوا.')
        return
    QUEUED[chat] = QUEUED.get(chat, 0) + 1
    if chat in BUSY:
        edit(chat, mid, 'في الطابور ⏳ هيبدأ أول ما التنزيل الحالي يخلص')
    lk = CHAT_LOCKS.setdefault(chat, threading.Lock())
    lk.acquire()
    BUSY.add(chat)
    d = os.path.join(WORK, uuid.uuid4().hex)
    os.makedirs(d)
    try:
        edit(chat, mid, f'جارٍ التنزيل: {o["label"]} ...')
        last = [0.0]

        def cb(done, total):
            if time.time() - last[0] < 4:
                return
            last[0] = time.time()
            pct = f' {done * 100 // total}%' if total else ''
            edit(chat, mid, f'جارٍ التنزيل: {o["label"]}{pct} ({mb(done)}' + (f' من {mb(total)})' if total else ')'))
        path = do_download(job['url'], o, d, cb)
        nm = os.path.join(d, safe_name(job['title']) + os.path.splitext(path)[1])
        if nm != path:
            os.replace(path, nm)
            path = nm
        size = os.path.getsize(path)
        if size > LIMIT:
            raise RuntimeError('toobig')
        edit(chat, mid, f'جارٍ الرفع ({mb(size)}) ...')
        if as_doc:
            r = upload('sendDocument', 'document', chat, path, {'caption': job['title']})
        elif o['kind'] == 'audio':
            r = upload('sendAudio', 'audio', chat, path, {'title': job['title']})
        else:
            r = upload('sendVideo', 'video', chat, path, {'caption': job['title'], 'supports_streaming': 'true'})
        if not r.get('ok'):
            r = upload('sendDocument', 'document', chat, path, {'caption': job['title']})
        if r.get('ok'):
            log('job ok', o['kind'], mb(size))
            STATS.setdefault(str(chat), {'ok': 0, 'fail': 0})['ok'] += 1
            edit(chat, mid, ('تم يا ' + uname(chat) + ' ✅ صلِّ على النبي') if uname(chat) else 'تم ✅ صلِّ على النبي')
            h = HIST.setdefault(str(chat), [])
            h.append({'t': job['title'][:60], 'u': job['url']})
            del h[:-10]
            save_state()
        else:
            edit(chat, mid, 'تعذر رفع الملف إلى تليجرام. جرّب جودة أقل.')
    except RuntimeError as e:
        log('job fail', str(e))
        STATS.setdefault(str(chat), {'ok': 0, 'fail': 0})['fail'] += 1
        m = {'toobig': f'الملف أكبر من حد تليجرام للبوتات ({LIMIT_TXT}). اختار جودة أقل، أو دوس زرار أرسل للتطبيق وانزّله من التطبيق مباشرة.', }.get(str(e), 'تعذر تنزيل الفيديو. جرّب جودة أخرى أو رابطًا آخر.')
        edit(chat, mid, m)
    except Exception as e:
        log('job error', type(e).__name__)
        edit(chat, mid, 'حصل خطأ أثناء التنزيل. جرّب مرة ثانية.')
    finally:
        BUSY.discard(chat)
        QUEUED[chat] = max(0, QUEUED.get(chat, 1) - 1)
        lk.release()
        shutil.rmtree(d, ignore_errors=True)
        JOBS.pop(jid, None) if False else None


def dur_txt(d):
    try:
        d = int(d)
        return f'{d // 60}:{d % 60:02d}'
    except Exception:
        return ''


PROBES = {}  # chat -> [timestamps]


# ---------- app distribution (always the latest release) ----------
GH_REPO = 'eslamahmedyosef12-cyber/Gooo'
APPC = {'t': 0, 'tag': None, 'n': 0, 'ver': '', 'url': '', 'size': 0, 'fid': {}}
APP_LOCK = threading.Lock()
APP_LAST = {}
APP_DIR = '/home/sandbox/tnzl-bot/appcache'


def latest_app(force=False):
    """Newest tnzl-wswr-vN release on GitHub (checked at most every 5 min), so a new ship is picked up automatically."""
    if not force and APPC['tag'] and time.time() - APPC['t'] < 300:
        return APPC
    try:
        rels = http_json(f'https://api.github.com/repos/{GH_REPO}/releases?per_page=100', timeout=20)
    except Exception:
        return APPC if APPC['tag'] else None
    best = None
    for r in rels:
        m = re.fullmatch(r'tnzl-wswr-v(\d+)', r.get('tag_name') or '')
        a = next((x for x in r.get('assets', []) if x['name'].endswith('.apk')), None)
        if m and a and (best is None or int(m.group(1)) > best[0]):
            best = (int(m.group(1)), r, a)
    if not best:
        return APPC if APPC['tag'] else None
    n, r, a = best
    APPC.update(t=time.time(), tag=r['tag_name'], n=n, ver=(r.get('name') or '').replace('تنزيل', '').strip(), url=a['browser_download_url'], size=a['size'])
    return APPC


def send_app(chat):
    now = time.time()
    if now - APP_LAST.get(chat, 0) < 30:
        send(chat, 'استنى شوية، التطبيق جاي.')
        return
    APP_LAST[chat] = now
    a = latest_app()
    if not a:
        send(chat, 'مقدرتش أجيب نسخة التطبيق دلوقتي، جرّب بعد شوية.')
        return
    cap = f'تطبيق تنزيل، آخر نسخة {a["ver"]} ({mb(a["size"])})\nلو عندك نسخة قديمة، ثبّت دي فوقها وبياناتك هتفضل زي ما هي. صلِّ على النبي 💚'
    with APP_LOCK:
        fid = a['fid'].get(a['tag'])
        if fid:
            r = api('sendDocument', {'chat_id': chat, 'document': fid, 'caption': cap})
            if r.get('ok'):
                log('app', 'sent-cached', a['tag'])
                return
        m = send(chat, f'جارٍ تجهيز التطبيق ({mb(a["size"])}) ...')
        os.makedirs(APP_DIR, exist_ok=True)
        path = f'{APP_DIR}/{a["tag"]}.apk'
        try:
            if not (os.path.exists(path) and os.path.getsize(path) == a['size']):
                req = urllib.request.Request(a['url'], headers={'User-Agent': UA})
                with urllib.request.urlopen(req, timeout=120) as f, open(path + '.part', 'wb') as o:
                    shutil.copyfileobj(f, o)
                if os.path.getsize(path + '.part') != a['size']:
                    raise RuntimeError('size')
                os.replace(path + '.part', path)
            for old in os.listdir(APP_DIR):
                if old != a['tag'] + '.apk':
                    try:
                        os.remove(f'{APP_DIR}/{old}')
                    except Exception:
                        pass
        except Exception as e:
            log('app', 'fetch fail', type(e).__name__)
            send(chat, 'مقدرتش أجهّز التطبيق دلوقتي، جرّب بعد شوية.')
            return
        r = upload('sendDocument', 'document', chat, path, {'caption': cap})
        if r.get('ok'):
            a['fid'][a['tag']] = (r['result'].get('document') or {}).get('file_id')
            log('app', 'sent', a['tag'])
        else:
            log('app', 'upload fail', str(r.get('description'))[:40])
            send(chat, 'مقدرتش أبعت الملف دلوقتي، جرّب بعد شوية.')


def handle_link(chat, url):
    now = time.time()
    ts = [x for x in PROBES.get(chat, []) if now - x < 60]
    if len(ts) >= 8:
        send(chat, 'بتبعت روابط كتير بسرعة، استنى دقيقة وكمّل.')
        return
    ts.append(now)
    PROBES[chat] = ts
    if YT_RE.match(url):
        jid = uuid.uuid4().hex[:8]
        JOBS[jid] = {'url': url, 'options': [{'label': 'YouTube', 'size': None, 'key': 'yt', 'kind': 'video'}], 'title': 'YouTube'}
        save_state()
        log('youtube', 'offer')
        deep = 'https://eslamahmedyosef12-cyber.github.io/Gooo/o.html#u=' + urllib.parse.quote(url, safe='')
        send(chat, '▶️ يوتيوب بيمنع السيرفرات، فالتنزيل بيتم من موبايلك أنت.\nاضغط "أرسل للتطبيق" وافتح تنزيل، هتلاقي الرابط في صندوق البوت 👇\n\nأو انسخ الرابط والصقه في التطبيق:\n' + url,
             {'inline_keyboard': [[{'text': '📲 أرسل للتطبيق', 'callback_data': f'a|{jid}'}],
                                  [{'text': '⚡ فتح مباشر (يحتاج نسخة 1.53 أو أحدث)', 'url': deep}]]})
        return
    r = send(chat, 'جارٍ فحص الرابط ...')
    mid = (r.get('result') or {}).get('message_id')
    try:
        title, opts = probe(url)
    except RuntimeError as e:
        log('probe fail', str(e))
        edit(chat, mid, human_err(e))
        return
    except subprocess.TimeoutExpired:
        log('probe fail', 'timeout')
        edit(chat, mid, 'الفحص أخد وقت طويل. جرّب تاني بعد شوية.')
        return
    except Exception as e:
        log('probe fail', type(e).__name__)
        edit(chat, mid, human_err('x'))
        return
    if not opts:
        edit(chat, mid, 'مفيش جودات متاحة للتنزيل في الرابط ده.')
        return
    jid = uuid.uuid4().hex[:8]
    JOBS[jid] = {'url': url, 'options': opts, 'title': title}
    save_state()
    meta = META.get(url) or {}
    info = [x for x in (meta.get('by'), dur_txt(meta.get('dur'))) if x]
    lines = [title] + ([' · '.join(info)] if info else []) + ['', f'اختار الجودة (حد تليجرام للبوتات {LIMIT_TXT}):']
    rows = []
    fit = [o for o in opts if o['kind'] == 'video' and (not o['size'] or o['size'] <= LIMIT)]
    if fit:
        best = fit[-1] if all(o['size'] for o in fit) else fit[len(fit) - 1]
        rows.append([{'text': f'⚡ أفضل جودة تناسب تليجرام ({best["label"]})', 'callback_data': f'd|{jid}|{best["key"]}'}])
    for o in opts:
        big = o['size'] and o['size'] > LIMIT
        lab = f'{o["label"]} · {mb(o["size"])}' + (' ⚠️ كبير' if big else '')
        rows.append([{'text': lab, 'callback_data': f'd|{jid}|{o["key"]}'}])
    if fit:
        rows.append([{'text': '📄 إرسال كملف أصلي (بدون ضغط)', 'callback_data': f'f|{jid}|{best["key"]}'}])
    rows.append([{'text': '📲 أرسل للتطبيق (للملفات الكبيرة)', 'callback_data': f'a|{jid}'}])
    kb = {'inline_keyboard': rows}
    thumb = meta.get('thumb')
    sent = False
    if thumb and thumb.startswith('http'):
        r2 = api('sendPhoto', {'chat_id': chat, 'photo': thumb, 'caption': '\n'.join(lines)[:1000], 'reply_markup': kb})
        if r2.get('ok'):
            sent = True
            api('deleteMessage', {'chat_id': chat, 'message_id': mid})
    if not sent:
        edit(chat, mid, '\n'.join(lines), kb)
    if len(JOBS) > 200:
        for k in list(JOBS)[:100]:
            JOBS.pop(k, None)


def safe_submit(fn, chat, *a):
    def run():
        try:
            fn(chat, *a)
        except Exception as e:
            log('task error', type(e).__name__)
            try:
                send(chat, 'حصل خطأ غير متوقع. جرّب تاني بعد شوية.')
            except Exception:
                pass
    POOL.submit(run)


WELCOME = ('صلِّ على النبي يا صاحبي 💚\n\nأهلًا بيك في تنزيل بوت 👋\n\nابعتلي رابط فيديو وأنا أنزّله وأبعتهولك هنا.\n'
           '• تيك توك: بدون علامة مائية\n• إنستجرام (منشورات وريلز عامة) وفيسبوك وإكس (تويتر)\n• يوتيوب: بيتحوّل للتطبيق بزرار واحد (السيرفر محظور منه) · ريديت غير متاح حاليًا\n• كل رابط: فيديو بجودات أو صوت MP3 فقط\n• المنشورات العامة فقط، وأي منصة ممكن تتغير وتتوقف مؤقتًا\n\n'
           f'حد تليجرام للبوتات {LIMIT_TXT}، فهوريك الأحجام قبل التنزيل.\n\n• روابط متعددة (حتى 3) في رسالة واحدة · ⚡ أفضل جودة تلقائيًا · شغال في المجموعات كمان\n\nلربط البوت بالتطبيق: /link الكود (من إعدادات التطبيق). لفك الربط: /unlink\nآخر تنزيلاتك: /history · حالة البوت: /status\nتحميل تطبيق تنزيل (آخر نسخة): /app')
APP_KB = {'inline_keyboard': [
    [{'text': '📥 حمّل تطبيق تنزيل', 'callback_data': 'g|app'}],
    [{'text': '🎧 احذف الموسيقى', 'callback_data': 'g|music'}],
    [{'text': '📜 تنزيلاتي', 'callback_data': 'g|hist'}, {'text': '📊 إحصائياتي', 'callback_data': 'g|stats'}],
    [{'text': '🔗 ربط التطبيق', 'callback_data': 'g|link'}, {'text': '❓ مساعدة', 'callback_data': 'g|help'}],
    [{'text': '🌐 الموقع', 'url': 'https://eslamahmedyosef12-cyber.github.io/Gooo/site/'}, {'text': '👤 المطوّر', 'callback_data': 'g|dev'}]]}
DEV_TXT = '👤 المطوّر\n\nالمصري Goo\nالمطوّر وصاحب المشروع\n\nمطوّر مصري بيحب التكنولوجيا والذكاء الاصطناعي، وصاحب مشروع «تنزيل». شغله كله على تطبيقات بسيطة وقوية تسهّل حياة الناس، وتجمع بين فكرة جديدة وسهولة في الاستخدام.\n\nصلِّ على النبي يا صاحبي 💚'
DEV_KB = {'inline_keyboard': [[{'text': '💬 واتساب', 'url': 'https://wa.me/201144864084'}, {'text': '✈️ تليجرام', 'url': 'https://t.me/Gx_o5'}]]}
START_TXT = ('ابعتلي أي رابط فيديو وأنا أجيبهولك 🎬\n\n🎵 تيك توك  ·  📸 إنستجرام  ·  📘 فيسبوك  ·  X إكس\n'
             '▶️ يوتيوب: بضغطة واحدة يفتح في التطبيق\n\nوالباقي من الأزرار اللي تحت 👇\n\n🌐 الموقع: eslamahmedyosef12-cyber.github.io/Gooo/site\nالمطوّر: المصري Goo · /dev')


def send_to_app(chat, jid):
    j = JOBS.get(jid)
    if not j:
        log('push', 'stale-job')
        send(chat, 'الرابط ده قديم، ابعته تاني.')
        return
    o = j['options'][0]
    try:
        ok = sb('tnzl_push', p_bot=SB_BOT, p_chat=chat, p_url=j['url'], p_title=(j['title'] or '')[:300], p_quality=str(o['label'])[:40], p_size=o['size'] or None)
    except RuntimeError as e:
        send(chat, 'بعتّ كتير، استنى دقيقة.' if str(e) == 'rate' else 'مقدرتش أبعت للتطبيق دلوقتي، جرّب بعد شوية.')
        return
    log('push', 'ok' if ok else 'not-linked')
    send(chat, 'اتبعت للتطبيق ✅ افتح تنزيل وهتلاقيه في صندوق البوت، وهيسألك قبل ما ينزّل.' if ok else 'التطبيق مش مربوط. افتح التطبيق، اضغط ربط البوت وابعتلي /link والكود.')


MEDIA = {}          # short id -> dict(chat, file_id, kind, name, size, dur)
MUSIC_LAST = {}     # chat -> last start time
MUSIC_INTRO = ('🎧 حذف الموسيقى\n\nابعتلي فيديو أو ملف صوتي، وهرجّعهولك من غير موسيقى مع إبقاء الصوت البشري (الكلام والغناء).\n\n'
               'للأمانة: بيشيل الموسيقى والآلات والمؤثرات الخلفية، والنتيجة بتتفاوت حسب الملف. المعالجة بتاخد من 2 لـ 25 دقيقة حسب الطول (حد أقصى 20 دقيقة للملف)، '
               'وهبعتلك الملف أول ما يخلص.')


def media_of(m):
    for key, kind in (('video', 'video'), ('audio', 'audio'), ('voice', 'audio'), ('video_note', 'video')):
        x = m.get(key)
        if x:
            return kind, x
    d = m.get('document')
    if d:
        mt = (d.get('mime_type') or '')
        if mt.startswith('video/'):
            return 'video', d
        if mt.startswith('audio/'):
            return 'audio', d
    return None, None


def handle_media(chat, m):
    kind, x = media_of(m)
    if not x:
        return
    size = x.get('file_size') or 0
    cap = 200 * 1048576 if LOCAL else 20 * 1048576
    if size > cap:
        send(chat, 'الملف كبير (%s). الحد الأقصى دلوقتي %s.' % (mb(size), 'نحو 200 ميجا' if LOCAL else '20 ميجا'))
        return
    if (x.get('duration') or 0) > 1200:
        send(chat, 'الملف أطول من 20 دقيقة. ابعت ملف أقصر.')
        return
    mid = uuid.uuid4().hex[:8]
    name = safe_name(x.get('file_name') or x.get('title') or ('video' if kind == 'video' else 'audio'))
    name = re.sub(r'\.[A-Za-z0-9]{2,4}$', '', name)[:40]
    MEDIA[mid] = {'chat': chat, 'file_id': x['file_id'], 'kind': kind, 'name': name, 'size': size, 'dur': x.get('duration') or 0}
    if len(MEDIA) > 200:
        for k in list(MEDIA)[:100]:
            MEDIA.pop(k, None)
    what = 'الفيديو' if kind == 'video' else 'الملف الصوتي'
    send(chat, f'وصلني {what} ({mb(size) if size else "الحجم غير معروف"}). أشيل الموسيقى وأسيب الصوت البشري؟',
         {'inline_keyboard': [[{'text': '🎧 ابدأ حذف الموسيقى', 'callback_data': 'm|' + mid}]]})


def music_run(chat, mid):
    j = MEDIA.get(mid)
    if not j or j['chat'] != chat:
        send(chat, 'الطلب ده قديم، ابعت الملف تاني.')
        return
    if time.time() - MUSIC_LAST.get(chat, 0) < 180:
        send(chat, 'استنى دقيقتين تلاتة لحد ما الطلب اللي قبله يخلص، وبعدين ابعت.')
        return
    gh = '/home/sandbox/.signing/github_token.txt'
    if STANDBY or not os.path.exists(gh) or not SB_SVC:
        send(chat, 'الخدمة دي شغالة من البوت الأساسي وهو بيرجع دلوقتي. ابعت الملف تاني بعد دقيقتين.')
        return
    MUSIC_LAST[chat] = time.time()
    send(chat, 'بجهّز الملف للمعالجة ... 🎧')
    try:
        fi = api('getFile', {'file_id': j['file_id']})
        if not fi.get('ok'):
            send(chat, 'تليجرام مش راضي يسلّمني الملف ده (غالبًا كبير). جرّب ملف أصغر.')
            MUSIC_LAST.pop(chat, None)
            return
        fp = fi['result']['file_path']
        if LOCAL and fp.startswith('/'):
            data = open(fp, 'rb').read()
        else:
            with urllib.request.urlopen(f'https://api.telegram.org/file/bot{TOKEN}/{fp}', timeout=180) as r:
                data = r.read()
        ext = os.path.splitext(fp)[1][:5] or ('.mp4' if j['kind'] == 'video' else '.mp3')
        obj = 'in-%s%s' % (uuid.uuid4().hex[:12], re.sub(r'[^A-Za-z0-9.]', '', ext))
        storage('POST', 'tnzl-tmp/' + obj, data, 'application/octet-stream')
        url = f'{SB_HOST}/storage/v1/object/public/tnzl-tmp/{obj}'
        del data
        body = json.dumps({'ref': 'main', 'inputs': {'url': url, 'chat': str(chat), 'kind': j['kind'], 'name': j['name']}}).encode()
        rq = urllib.request.Request('https://api.github.com/repos/eslamahmedyosef12-cyber/Gooo/actions/workflows/music.yml/dispatches', body,
                                    {'Authorization': 'token ' + open(gh).read().strip(), 'Accept': 'application/vnd.github+json'})
        urllib.request.urlopen(rq, timeout=30).read()
        log('music', 'dispatched', j['kind'], j['size'])
        send(chat, 'بدأت المعالجة ✅ هتوصلك النتيجة هنا لوحدها (من 2 لـ 25 دقيقة). تقدر تكمّل استخدام البوت عادي.')
    except Exception as e:
        log('music', 'fail', type(e).__name__)
        MUSIC_LAST.pop(chat, None)
        send(chat, 'حصلت مشكلة وأنا بجهّز الملف. جرّب تاني بعد شوية.')


def handle(u):
    k = 'cb' if 'callback_query' in u else 'msg'
    c = ((u.get('message') or {}).get('chat') or {}).get('id') or ((u.get('callback_query') or {}).get('message') or {}).get('chat', {}).get('id')
    t = re.sub(r'^(/\w+)@\w+', r'\1', (u.get('message') or {}).get('text') or '')
    log('update', k, 'chat', c, 'cmd', t.split()[0][:12] if t.startswith('/') else ('url' if URL_RE.search(t) else 'text'))
    if 'callback_query' in u:
        q = u['callback_query']
        api('answerCallbackQuery', {'callback_query_id': q['id']})
        parts = (q.get('data') or '').split('|')
        if len(parts) == 2 and parts[0] == 'n' and parts[1] == 'skip':
            cid = q['message']['chat']['id']
            PENDING.discard(cid)
            set_user(cid, '', True)
            send(cid, 'تمام 💚 ' + START_TXT + '\n\nولو حبيت تسجّل اسمك بعدين: /name اسمك', APP_KB)
            return
        if len(parts) == 2 and parts[0] == 'g' and parts[1] == 'music':
            send(q['message']['chat']['id'], MUSIC_INTRO)
            return
        if len(parts) == 2 and parts[0] == 'm':
            safe_submit(music_run, q['message']['chat']['id'], parts[1])
            return
        if len(parts) == 2 and parts[0] == 'g' and parts[1] in ('hist', 'stats', 'help', 'link', 'dev'):
            mm = q['message']
            cmd = {'hist': '/history', 'stats': '/stats', 'help': '/help', 'link': '/link', 'dev': '/dev'}[parts[1]]
            handle({'message': {'chat': mm['chat'], 'text': cmd}})
            return
        if len(parts) == 2 and parts[0] == 'g' and parts[1] == 'app':
            safe_submit(send_app, q['message']['chat']['id'])
            return
        if len(parts) == 2 and parts[0] == 'a':
            send_to_app(q['message']['chat']['id'], parts[1])
            return
        if len(parts) == 3 and parts[0] == 'f':
            m = q['message']
            safe_submit(run_job, m['chat']['id'], m['message_id'], parts[1], parts[2], True)
            return
        if len(parts) == 3 and parts[0] == 'd':
            m = q['message']
            safe_submit(run_job, m['chat']['id'], m['message_id'], parts[1], parts[2])
        return
    m = u.get('message') or {}
    chat = (m.get('chat') or {}).get('id')
    text = re.sub(r'^(/\w+)@\w+', r'\1', m.get('text') or '')
    if not chat:
        return
    group = (m.get('chat') or {}).get('type') in ('group', 'supergroup', 'channel')
    if media_of(m)[0] and not group:
        safe_submit(handle_media, chat, m)
        return
    if text.startswith('/music'):
        send(chat, MUSIC_INTRO)
        return
    if text.startswith('/start') and not group and len(text.split()) > 1 and re.fullmatch(r'j_[0-9a-f]{10}', text.split()[1]):
        try:
            wu = sb('tnzl_web_take', p_bot=SB_BOT, p_code=text.split()[1][2:])
        except RuntimeError:
            send(chat, 'مقدرتش أوصل للخدمة دلوقتي، جرّب من الموقع تاني بعد شوية.')
            return
        log('web', 'take', 'ok' if wu else 'expired')
        if not wu:
            send(chat, 'الرابط ده انتهت صلاحيته أو اتستخدم. ارجع للموقع والصق الرابط تاني.')
            return
        send(chat, 'وصلني الرابط من الموقع 🌐')
        safe_submit(handle_link, chat, wu)
        return
    if text.startswith('/start') or text.startswith('/help'):
        u = None if group else get_user(chat)
        if text.startswith('/help'):
            send(chat, WELCOME, APP_KB)
        elif group:
            send(chat, 'صلِّ على النبي 💚\n\n' + START_TXT, APP_KB)
        elif u and u.get('name'):
            send(chat, f'أهلًا بيك يا {u["name"]} 💚\n\n' + START_TXT, APP_KB)
        elif u is None:
            PENDING.add(chat)
            send(chat, 'صلِّ على النبي يا صاحبي 💚\nأهلًا بيك في تنزيل بوت 👋\n\nاسمك إيه؟ اكتبه وأنا هناديك بيه كل مرة.',
                 {'inline_keyboard': [[{'text': 'تخطّي', 'callback_data': 'n|skip'}]]})
        else:
            send(chat, 'صلِّ على النبي يا صاحبي 💚\n\n' + START_TXT, APP_KB)
        return
    if text.startswith('/name') and not group:
        nm = text.split(None, 1)[1].strip()[:30] if len(text.split(None, 1)) > 1 else ''
        if not nm or URL_RE.search(nm):
            send(chat, 'اكتب كده: /name اسمك')
            return
        PENDING.discard(chat)
        send(chat, f'تشرّفنا يا {nm} 💚' if set_user(chat, nm) else 'مقدرتش أحفظ الاسم دلوقتي، جرّب بعد شوية.')
        return
    if text.startswith('/dev'):
        send(chat, DEV_TXT, DEV_KB)
        return
    if text.startswith('/app'):
        safe_submit(send_app, chat)
        return
    if text.startswith('/history'):
        h = HIST.get(str(chat)) or []
        send(chat, ('آخر ما نزّلته:\n\n' + '\n\n'.join(f'{i + 1}. {x["t"]}\n{x["u"]}' for i, x in enumerate(reversed(h)))) if h else 'لسه ما نزّلتش حاجة. ابعتلي رابط.')
        return
    if text.startswith('/status'):
        up = int(time.time() - START)
        v = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True).stdout.strip()
        send(chat, f'البوت شغال ✅\nمنذ آخر إعادة تشغيل: {up // 3600} ساعة و{up % 3600 // 60} دقيقة\nنسخة المحرك: {v}\nالتنزيلات الجارية: {len(BUSY)}\nملحوظة: السيرفر المجاني بيعمل إعادة تشغيل أحيانًا، لو ماردش ابعت الرابط تاني بعد دقيقة.')
        return
    if text.startswith('/stats'):
        st = STATS.get(str(chat)) or {'ok': 0, 'fail': 0}
        send(chat, f'إحصائياتك في البوت:\nنجح: {st["ok"]}\nفشل: {st["fail"]}\nآخر تنزيلات: /history')
        return
    if text.startswith('/link') and group:
        send(chat, 'الربط بالتطبيق بيتم في المحادثة الخاصة مع البوت بس.')
        return
    if text.startswith('/link'):
        arg = text.split(None, 1)[1].strip() if len(text.split(None, 1)) > 1 else ''
        if not re.fullmatch(r'[A-Za-z0-9]{8}', arg):
            send(chat, 'افتح التطبيق: الإعدادات ثم ربط البوت، وهيظهرلك كود من 8 حروف. ابعتلي: /link الكود')
            return
        try:
            ok = sb('tnzl_link', p_bot=SB_BOT, p_code=arg.upper(), p_chat=chat)
        except RuntimeError as e:
            send(chat, 'حاولت كتير، استنى شوية وجرّب تاني.' if str(e) == 'rate' else 'مقدرتش أوصل للخدمة دلوقتي، جرّب بعد شوية.')
            return
        send(chat, 'تم الربط ✅ دلوقتي أي رابط تبعتهولي هتلاقي تحته زرار \"أرسل للتطبيق\". الكود اتلغى ومش هيشتغل تاني.' if ok else 'الكود غلط أو انتهت صلاحيته (10 دقايق) أو اتستخدم قبل كده. اطلب كود جديد من التطبيق.')
        return
    if text.startswith('/unlink'):
        try:
            n = sb('tnzl_unlink_bot', p_bot=SB_BOT, p_chat=chat)
            send(chat, 'تم فك الربط وحذف أي روابط معلّقة.' if n else 'مفيش ربط حالي.')
        except RuntimeError:
            send(chat, 'مقدرتش أوصل للخدمة دلوقتي، جرّب بعد شوية.')
        return
    if chat in PENDING and not group and text and not text.startswith('/') and not URL_RE.search(text):
        nm = ' '.join(text.split())[:30]
        if len(nm) >= 1:
            PENDING.discard(chat)
            send(chat, f'تشرّفنا يا {nm} 💚\n\n' + START_TXT if set_user(chat, nm) else 'مقدرتش أحفظ الاسم دلوقتي، ابعتلي رابط عادي وهنكمّل.')
            return
    urls = list(dict.fromkeys(URL_RE.findall(text)))[:3]
    if urls:
        if len(URL_RE.findall(text)) > 3:
            send(chat, 'هاخد أول 3 روابط بس في المرة الواحدة.')
        for x in urls:
            safe_submit(handle_link, chat, x)
    elif not group and not text.startswith('/'):
        send(chat, 'ابعتلي رابط فيديو (تيك توك أو إنستجرام أو إكس أو فيسبوك).')


# ---------- website direct-download relay (small files via Supabase Storage, auto-deleted) ----------
SB_HOST = 'https://dinlporwlqeoyvllhapo.supabase.co'
try:
    SB_SVC = open('/home/sandbox/tnzl-bot/.sb_service').read().strip()
except Exception:
    SB_SVC = ''
WEB_MAX = 44 * 1024 * 1024


def storage(method, path, data=None, ctype=None):
    h = {'apikey': SB_SVC, 'Authorization': 'Bearer ' + SB_SVC}
    if ctype:
        h['Content-Type'] = ctype
    r = urllib.request.Request(SB_HOST + '/storage/v1/object/' + path, data, h, method=method)
    with urllib.request.urlopen(r, timeout=180) as f:
        return f.read()


def web_job(j):
    code, url = j['code'], j['url']
    if YT_RE.match(url):
        sb('tnzl_web_fail', p_bot=SB_BOT, p_code=code, p_err='yt')
        return
    try:
        title, opts = probe(url)
        vids = [o for o in opts if o['kind'] == 'video']
        fit = [o for o in vids if o['size'] and o['size'] <= WEB_MAX]
        pick = fit[-1] if fit else next((o for o in vids if not o['size']), None)
        if not pick:
            sb('tnzl_web_fail', p_bot=SB_BOT, p_code=code, p_err='toobig')
            return
        d = tempfile.mkdtemp(prefix='web_')
        try:
            path = do_download(url, pick, d, None, '44M')
            size = os.path.getsize(path)
            if size > WEB_MAX:
                sb('tnzl_web_fail', p_bot=SB_BOT, p_code=code, p_err='toobig')
                return
            ext = os.path.splitext(path)[1] or '.mp4'
            name = code + ext
            storage('POST', 'tnzl-tmp/' + name, open(path, 'rb').read(), mimetypes.guess_type(path)[0] or 'video/mp4')
            sb('tnzl_web_done', p_bot=SB_BOT, p_code=code, p_file=f'{SB_HOST}/storage/v1/object/public/tnzl-tmp/{name}', p_title=title or 'video', p_size=size)
            log('web', 'job ok', mb(size))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    except RuntimeError as e:
        sb('tnzl_web_fail', p_bot=SB_BOT, p_code=code, p_err='toobig' if str(e) == 'toobig' else 'fail')
        log('web', 'job fail', str(e)[:20])
    except Exception as e:
        log('web', 'job fail', type(e).__name__)
        try:
            sb('tnzl_web_fail', p_bot=SB_BOT, p_code=code, p_err='fail')
        except Exception:
            pass


def web_sweep():
    for x in sb('tnzl_web_expired', p_bot=SB_BOT) or []:
        try:
            storage('DELETE', 'tnzl-tmp/' + x['file'].rsplit('/', 1)[-1])
        except urllib.error.HTTPError as e:
            if e.code not in (400, 404):
                continue
        except Exception:
            continue
        sb('tnzl_web_clear', p_bot=SB_BOT, p_code=x['code'])


def standby_web():
    while True:
        time.sleep(10)
        if WEB_ACTIVE():
            break
    web_worker()


def WEB_ACTIVE():
    return not primary_alive()[0]


def web_worker():
    if not SB_SVC:
        return
    last = 0
    while True:
        try:
            j = sb('tnzl_web_next', p_bot=SB_BOT)
            if j:
                web_job(j)
                continue
            if time.time() - last > 300:
                last = time.time()
                web_sweep()
        except Exception as e:
            log('web', 'worker', type(e).__name__)
            time.sleep(15)
        time.sleep(6)


STANDBY = os.environ.get('STANDBY') == '1'   # backup instance (GitHub Actions): polls only while the primary heartbeat is stale


def heartbeat():
    while True:
        try:
            sb('tnzl_hb_set', p_bot=SB_BOT)
        except Exception:
            pass
        time.sleep(20)


def primary_alive():
    try:
        r = sb('tnzl_hb_get')
        return float(r['age']) < 75, float(r['ts'])
    except Exception:
        return True, 0.0      # cannot tell: stay quiet rather than answer twice


def main():
    load_state()
    pull_state()
    if STANDBY:
        threading.Thread(target=standby_web, daemon=True).start()
    else:
        threading.Thread(target=heartbeat, daemon=True).start()
        threading.Thread(target=web_worker, daemon=True).start()
    api('setMyCommands', {'commands': [{'command': 'start', 'description': 'القائمة'}, {'command': 'app', 'description': 'حمّل تطبيق تنزيل'},
        {'command': 'history', 'description': 'تنزيلاتي'}, {'command': 'dev', 'description': 'المطوّر'}, {'command': 'link', 'description': 'ربط التطبيق'}, {'command': 'help', 'description': 'مساعدة'}]})
    me = api('getMe')
    log('bot', (me.get('result') or {}).get('username'))
    off = 0
    active, since, chk = not STANDBY, 0.0, 0.0
    while True:
        if STANDBY and time.time() - chk > 15:
            chk = time.time()
            alive, ts = primary_alive()
            if alive and active:
                active = False
                log('standby', 'primary back, idle')
            elif not alive and not active:
                active, since, off = True, ts, 0
                log('standby', 'primary down, taking over')
        if not active:
            time.sleep(5)
            continue
        r = api('getUpdates', {'offset': off, 'timeout': 30, 'allowed_updates': ['message', 'callback_query']}, 45)
        if not r.get('ok'):
            time.sleep(3)
            continue
        for u in r['result']:
            off = u['update_id'] + 1
            if STANDBY and (u.get('message') or {}).get('date', 1e12) < since:
                continue      # already answered by the primary before it went down
            try:
                handle(u)
            except Exception as e:
                log('handle error', type(e).__name__)


if __name__ == '__main__':
    main()
