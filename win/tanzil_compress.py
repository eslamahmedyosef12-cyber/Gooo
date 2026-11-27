# -*- coding: utf-8 -*-
"""تنزيل ضاغط الفيديو: ضغط وتحويل الفيديو بدون إنترنت. بايثون 3.8، يعمل على ويندوز 7."""
import os
import re
import subprocess
import sys
import threading
import time

APP_NAME = 'تنزيل ضاغط الفيديو'
VERSION = '1.0.0'
CREATE_NO_WINDOW = 0x08000000


def base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def find_ffmpeg():
    env = os.environ.get('TANZIL_FFMPEG')
    if env and os.path.exists(env):
        return env
    for d in (base_dir(), getattr(sys, '_MEIPASS', base_dir())):
        p = os.path.join(d, 'ffmpeg.exe')
        if os.path.exists(p):
            return p
    return 'ffmpeg'


FFMPEG = find_ffmpeg()


def run_hidden(args, **kw):
    flags = CREATE_NO_WINDOW if os.name == 'nt' else 0
    return subprocess.Popen(args, creationflags=flags, **kw)


def probe(path):
    """Returns dict(duration seconds, width, height, has_audio, size bytes) using `ffmpeg -i`."""
    p = run_hidden([FFMPEG, '-hide_banner', '-i', path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = p.communicate()[0].decode('utf-8', 'replace')
    info = {'duration': 0.0, 'width': 0, 'height': 0, 'has_audio': 'Audio:' in out, 'has_video': 'Video:' in out,
            'size': os.path.getsize(path) if os.path.exists(path) else 0}
    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', out)
    if m:
        info['duration'] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    m = re.search(r'Video:.*?,\s*(\d{2,5})x(\d{2,5})', out)
    if m:
        info['width'], info['height'] = int(m.group(1)), int(m.group(2))
    return info


QUALITY = {
    'small': ('حجم صغير (مناسب للواتساب)', 30, 480),
    'medium': ('متوسط (جودة جيدة وحجم أقل)', 26, 720),
    'high': ('جودة عالية (قريب من الأصلي)', 23, 0),
}
FORMATS = {'mp4': 'MP4 (الأشهر)', 'mkv': 'MKV', 'avi': 'AVI (للأجهزة القديمة)', 'mp3': 'MP3 (صوت فقط)'}


def build_cmd(src, dst, info, fmt, mode, value):
    """mode: 'quality' (value = key of QUALITY) or 'size' (value = target MB). Returns ffmpeg argument list."""
    cmd = [FFMPEG, '-hide_banner', '-loglevel', 'error', '-y', '-i', src, '-progress', 'pipe:1', '-nostats']
    if fmt == 'mp3':
        kbps = 128
        if mode == 'size' and info['duration'] > 0:
            kbps = max(32, min(320, int(float(value) * 8192 / info['duration'])))
        return cmd + ['-vn', '-c:a', 'libmp3lame', '-b:a', '%dk' % kbps, dst]
    scale_h = 0
    crf = 26
    vbit = None
    if mode == 'size' and info['duration'] > 0:
        total = float(value) * 8192 / info['duration']          # kilobits per second for the whole file
        abit = 96 if total > 400 else 48
        vbit = max(60, int(total - abit))
        # lower resolution when the bitrate is small, so the picture stays clean
        h = info['height']
        if vbit < 350:
            scale_h = 360
        elif vbit < 800:
            scale_h = 480
        elif vbit < 1800:
            scale_h = 720
        if h and scale_h >= h:
            scale_h = 0
    else:
        _, crf, scale_h = QUALITY.get(value, QUALITY['medium'])
        if scale_h and info['height'] and info['height'] <= scale_h:
            scale_h = 0
    vf = []
    if scale_h:
        vf.append('scale=-2:%d' % scale_h)
    else:
        vf.append('scale=trunc(iw/2)*2:trunc(ih/2)*2')   # H.264 needs even sizes
    cmd += ['-vf', ','.join(vf), '-c:v', 'libx264', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', '-threads', '2']
    if vbit:
        cmd += ['-b:v', '%dk' % vbit, '-maxrate', '%dk' % int(vbit * 1.4), '-bufsize', '%dk' % int(vbit * 2)]
    else:
        cmd += ['-crf', str(crf)]
    if info['has_audio']:
        if fmt == 'avi':
            cmd += ['-c:a', 'libmp3lame', '-b:a', '128k']
        else:
            cmd += ['-c:a', 'aac', '-b:a', '96k' if mode != 'quality' or value != 'high' else '128k']
    else:
        cmd += ['-an']
    if fmt == 'mp4':
        cmd += ['-movflags', '+faststart']
    return cmd + [dst]


class Job:
    """One conversion run. progress callback gets (fraction, seconds_left or None)."""

    def __init__(self, cmd, duration, on_progress):
        self.cmd = cmd
        self.duration = duration
        self.on_progress = on_progress
        self.proc = None
        self.cancelled = False
        self.error = ''

    def run(self):
        self.proc = run_hidden(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        t0 = time.time()
        tail = []
        for raw in iter(self.proc.stdout.readline, b''):
            line = raw.decode('utf-8', 'replace').strip()
            m = re.match(r'out_time_(?:us|ms)=(\d+)', line)
            if m and self.duration > 0:
                done = int(m.group(1)) / 1000000.0
                frac = min(0.99, done / self.duration)
                el = time.time() - t0
                left = (el / frac - el) if frac > 0.02 else None
                self.on_progress(frac, left)
            elif line and '=' not in line.split(' ')[0]:
                tail.append(line)
                tail = tail[-6:]
        self.proc.wait()
        if self.cancelled:
            return False
        if self.proc.returncode != 0:
            self.error = ' | '.join(tail)[-300:]
            return False
        self.on_progress(1.0, 0)
        return True

    def cancel(self):
        self.cancelled = True
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.kill()
        except Exception:
            pass


def human_size(n):
    if n >= 1048576:
        return '%.1f ميجا' % (n / 1048576.0)
    return '%d كيلوبايت' % max(1, n // 1024)


def human_time(s):
    s = int(s)
    if s >= 3600:
        return '%d:%02d:%02d' % (s // 3600, (s % 3600) // 60, s % 60)
    return '%d:%02d' % (s // 60, s % 60)


def default_out(src, fmt):
    d, n = os.path.split(src)
    stem = os.path.splitext(n)[0]
    out = os.path.join(d, stem + '-tanzil.' + fmt)
    i = 2
    while os.path.exists(out):
        out = os.path.join(d, '%s-tanzil-%d.%s' % (stem, i, fmt))
        i += 1
    return out


def cli(argv):
    """tanzil.exe --cli INPUT OUTPUT FORMAT MODE VALUE   (used for self-test)"""
    src, dst, fmt, mode, value = argv[:5]
    info = probe(src)
    if mode == 'size':
        value = float(value)
    cmd = build_cmd(src, dst, info, fmt, mode, value)
    job = Job(cmd, info['duration'], lambda f, l: None)
    ok = job.run()
    print('ok' if ok else 'fail: ' + job.error)
    if ok:
        print('in=%d out=%d dur=%.1f' % (info['size'], os.path.getsize(dst), info['duration']))
    return 0 if ok else 1


def gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    BG, CARD, ACC, TXT, SUB = '#0b1f16', '#12301f', '#2e9e6b', '#e8fff3', '#9fc9b3'
    FONT = ('Tahoma', 10)
    root = tk.Tk()
    root.title(APP_NAME)
    root.configure(bg=BG)
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    ww, wh = 560, min(610, sh - 70)
    root.geometry('%dx%d+%d+%d' % (ww, wh, max(0, (sw - ww) // 2), 5))
    root.minsize(520, 480)
    try:
        ico = os.path.join(getattr(sys, '_MEIPASS', base_dir()), 'icon.ico')
        if os.path.exists(ico):
            root.iconbitmap(ico)
    except Exception:
        pass

    st = {'src': '', 'info': None, 'out': '', 'job': None, 'busy': False}
    v_fmt = tk.StringVar(value='mp4')
    v_mode = tk.StringVar(value='quality')
    v_q = tk.StringVar(value='medium')
    v_mb = tk.StringVar(value='16')

    def lbl(parent, text, size=10, color=TXT, bold=False, **kw):
        return tk.Label(parent, text=text, bg=parent['bg'], fg=color, font=('Tahoma', size, 'bold' if bold else 'normal'),
                        anchor='e', justify='right', **kw)

    head = tk.Frame(root, bg=BG)
    head.pack(fill='x', pady=(14, 4))
    lbl(head, 'تنزيل', 26, '#7fe0ae', True).pack()
    lbl(head, 'ضاغط ومحوّل الفيديو  ·  يعمل بدون إنترنت', 10, SUB).pack()
    lbl(head, 'صلِّ على النبي', 9, SUB).pack()

    def card(title):
        f = tk.Frame(root, bg=CARD, padx=14, pady=6)
        f.pack(fill='x', padx=16, pady=3)
        lbl(f, title, 11, '#7fe0ae', True).pack(fill='x')
        return f

    c1 = card('1) اختار الفيديو')
    file_lbl = lbl(c1, 'لسه ماختارتش ملف', 10, SUB, wraplength=480)
    file_lbl.pack(fill='x', pady=(4, 6))
    info_lbl = lbl(c1, '', 9, SUB)
    info_lbl.pack(fill='x')

    def pick():
        if st['busy']:
            return
        p = filedialog.askopenfilename(title='اختار فيديو أو صوت',
                                       filetypes=[('فيديو وصوت', '*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.webm *.3gp *.m4v *.mpg *.mpeg *.ts *.mp3 *.m4a *.wav *.aac *.ogg'), ('كل الملفات', '*.*')])
        if not p:
            return
        try:
            info = probe(p)
        except Exception:
            messagebox.showerror(APP_NAME, 'مقدرتش أشغّل ffmpeg. تأكد إن ffmpeg.exe جنب البرنامج.')
            return
        if not info['duration']:
            messagebox.showerror(APP_NAME, 'الملف ده مش فيديو أو صوت أقدر أقرأه.')
            return
        st['src'], st['info'] = p, info
        file_lbl.config(text=os.path.basename(p), fg=TXT)
        res = ('%dx%d  ·  ' % (info['width'], info['height'])) if info['width'] else ''
        info_lbl.config(text='%sالمدة %s  ·  الحجم %s' % (res, human_time(info['duration']), human_size(info['size'])))
        refresh_out()
        if not info['has_video']:
            v_fmt.set('mp3')
        refresh_est()

    tk.Button(c1, text='اختار ملف ...', command=pick, bg=ACC, fg='white', activebackground='#38b57c', relief='flat', font=('Tahoma', 11, 'bold'), padx=14, pady=4).pack(pady=(8, 0))

    c2 = card('2) النتيجة المطلوبة')
    for key, (name, crf, h) in QUALITY.items():
        tk.Radiobutton(c2, text=name, variable=v_q, value=key, command=lambda: (v_mode.set('quality'), refresh_est()), bg=CARD, fg=TXT, selectcolor=BG, activebackground=CARD, activeforeground=TXT, font=FONT, anchor='e').pack(fill='x')
    row = tk.Frame(c2, bg=CARD)
    row.pack(fill='x', pady=(4, 0))
    ent = tk.Entry(row, textvariable=v_mb, width=6, font=FONT, justify='center')
    ent.pack(side='right', padx=(6, 0))
    tk.Radiobutton(row, text='حجم محدد بالميجا:', variable=v_mode, value='size', command=lambda: refresh_est(), bg=CARD, fg=TXT, selectcolor=BG, activebackground=CARD, activeforeground=TXT, font=FONT).pack(side='right')
    est_lbl = lbl(c2, '', 9, SUB)
    est_lbl.pack(fill='x', pady=(4, 0))

    def refresh_est(*_):
        i = st['info']
        if not i:
            est_lbl.config(text='')
            return
        if v_fmt.get() == 'mp3':
            est_lbl.config(text='هيطلع ملف صوت MP3 فقط.')
        elif v_mode.get() == 'size':
            est_lbl.config(text='الحجم النهائي تقريبي (قريب من الرقم ده).')
        else:
            est_lbl.config(text='الحجم النهائي بيعتمد على الفيديو، هتشوفه بعد الانتهاء.')
    v_mb.trace('w', refresh_est)

    c3 = card('3) الصيغة ومكان الحفظ')
    fr = tk.Frame(c3, bg=CARD)
    fr.pack(fill='x')
    for k, n in FORMATS.items():
        tk.Radiobutton(fr, text=n, variable=v_fmt, value=k, command=lambda: (refresh_out(), refresh_est()), bg=CARD, fg=TXT, selectcolor=BG, activebackground=CARD, activeforeground=TXT, font=FONT).pack(side='right', padx=4)
    out_lbl = lbl(c3, '', 9, SUB, wraplength=480)
    out_lbl.pack(fill='x', pady=(6, 0))

    def refresh_out():
        if st['src']:
            st['out'] = default_out(st['src'], v_fmt.get())
            out_lbl.config(text='هيتحفظ في: ' + st['out'])

    def change_out():
        if not st['src']:
            return
        p = filedialog.asksaveasfilename(defaultextension='.' + v_fmt.get(), initialfile=os.path.basename(st['out']), initialdir=os.path.dirname(st['out']))
        if p:
            st['out'] = p
            out_lbl.config(text='هيتحفظ في: ' + p)
    tk.Button(c3, text='غيّر مكان الحفظ', command=change_out, bg=BG, fg=TXT, relief='flat', font=('Tahoma', 9)).pack(anchor='e', pady=(4, 0))

    c4 = tk.Frame(root, bg=BG)
    c4.pack(fill='x', padx=16, pady=3)
    style = ttk.Style()
    try:
        style.theme_use('clam')
    except Exception:
        pass
    style.configure('G.Horizontal.TProgressbar', troughcolor=CARD, background=ACC, bordercolor=BG, lightcolor=ACC, darkcolor=ACC)
    bar = ttk.Progressbar(c4, style='G.Horizontal.TProgressbar', maximum=100, length=520)
    bar.pack(fill='x')
    status = lbl(c4, 'جاهز', 10, SUB)
    status.pack(fill='x', pady=(4, 0))
    btn_row = tk.Frame(c4, bg=BG)
    btn_row.pack(pady=8)
    go = tk.Button(btn_row, text='ابدأ', bg=ACC, fg='white', activebackground='#38b57c', relief='flat', font=('Tahoma', 13, 'bold'), padx=30, pady=6)
    go.pack(side='right', padx=6)
    cancel = tk.Button(btn_row, text='إلغاء', bg='#7a2e2e', fg='white', relief='flat', font=('Tahoma', 11), padx=16, pady=6, state='disabled')
    cancel.pack(side='right', padx=6)
    open_btn = tk.Button(btn_row, text='افتح المجلد', bg=CARD, fg=TXT, relief='flat', font=('Tahoma', 11), padx=12, pady=6, state='disabled')
    open_btn.pack(side='right', padx=6)

    foot = tk.Label(root, text='تطوير: المصري Goo  ·  مجاني بدون إعلانات  ·  بيشتغل بدون نت', bg=BG, fg=SUB, font=('Tahoma', 8))
    foot.pack(side='bottom', pady=6)

    def set_busy(b):
        st['busy'] = b
        go.config(state='disabled' if b else 'normal')
        cancel.config(state='normal' if b else 'disabled')

    def on_progress(frac, left):
        def ui():
            bar['value'] = frac * 100
            t = '%d%%' % int(frac * 100)
            if left is not None and frac < 1:
                t += '  ·  باقي تقريبًا ' + human_time(left)
            status.config(text='جاري التحويل ...  ' + t, fg=TXT)
        root.after(0, ui)

    def finish(ok, job):
        set_busy(False)
        if ok:
            bar['value'] = 100
            try:
                sz = os.path.getsize(st['out'])
                status.config(text='خلص ✅  حجم الملف الجديد: %s  (الأصلي: %s)' % (human_size(sz), human_size(st['info']['size'])), fg='#7fe0ae')
            except Exception:
                status.config(text='خلص ✅', fg='#7fe0ae')
            open_btn.config(state='normal')
        elif job.cancelled:
            bar['value'] = 0
            status.config(text='اتلغى.', fg=SUB)
            try:
                if os.path.exists(st['out']):
                    os.remove(st['out'])
            except Exception:
                pass
        else:
            bar['value'] = 0
            status.config(text='فشل التحويل. جرّب صيغة تانية أو ملف تاني.', fg='#ff9c9c')
            messagebox.showerror(APP_NAME, 'فشل التحويل.\n\n' + (job.error or 'سبب غير معروف'))

    def start():
        if not st['src']:
            messagebox.showinfo(APP_NAME, 'اختار فيديو الأول.')
            return
        mode, value = v_mode.get(), v_q.get()
        if mode == 'size':
            try:
                value = float(v_mb.get().replace(',', '.'))
                if value <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showinfo(APP_NAME, 'اكتب رقم صحيح للحجم بالميجا.')
                return
            if v_fmt.get() != 'mp3' and st['info']['duration'] > 0 and value * 8192 / st['info']['duration'] < 70:
                messagebox.showinfo(APP_NAME, 'الحجم ده صغير جدًا بالنسبة لمدة الفيديو. اكتب رقم أكبر.')
                return
        if os.path.exists(st['out']):
            if not messagebox.askyesno(APP_NAME, 'الملف ده موجود. أستبدله؟'):
                return
        cmd = build_cmd(st['src'], st['out'], st['info'], v_fmt.get(), mode, value)
        job = Job(cmd, st['info']['duration'], on_progress)
        st['job'] = job
        set_busy(True)
        open_btn.config(state='disabled')
        bar['value'] = 0
        status.config(text='بدأنا ...', fg=TXT)

        def work():
            try:
                ok = job.run()
            except Exception as e:
                job.error = str(e)
                ok = False
            root.after(0, lambda: finish(ok, job))
        threading.Thread(target=work, daemon=True).start()

    def do_cancel():
        if st['job']:
            st['job'].cancel()

    def open_folder():
        p = st['out']
        try:
            if os.name == 'nt':
                subprocess.Popen(['explorer', '/select,', os.path.normpath(p)])
            else:
                subprocess.Popen(['xdg-open', os.path.dirname(p)])
        except Exception:
            pass

    def on_close():
        if st['busy']:
            if not messagebox.askyesno(APP_NAME, 'في تحويل شغال. تقفل وتلغيه؟'):
                return
            do_cancel()
        root.destroy()

    go.config(command=start)
    cancel.config(command=do_cancel)
    open_btn.config(command=open_folder)
    root.protocol('WM_DELETE_WINDOW', on_close)
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) >= 7 and sys.argv[1] == '--cli':
        sys.exit(cli(sys.argv[2:]))
    gui()
