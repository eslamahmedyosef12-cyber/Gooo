# -*- coding: utf-8 -*-
"""تنزيل PC: مدرب كتابة + تايمر مذاكرة. أوفلاين بالكامل. Python 3.8."""
import json
import os
import random
import sys
import time
import threading
import datetime
import re
import tkinter as tk

try:
    import winsound
except Exception:
    winsound = None

APP = 'تنزيل - مدرب الكتابة والمذاكرة'
BG = '#0e1f17'
CARD = '#16301f'
ACC = '#2e9e6a'
TXT = '#e8f5ec'
SUB = '#9cc2aa'
BAD = '#c0504d'
FONT = 'Tahoma'
GRN = '#7fe0b0'
YEL = '#e0c97f'
THEMES = {
    'dark': dict(bg=BG, card=CARD, txt=TXT, sub=SUB, grn=GRN, yel=YEL),
    'light': dict(bg='#f2f8f4', card='#dcebe1', txt='#10261a', sub='#4a6957', grn='#1c7a4c', yel='#8a6a00'),
}

AR = [
    'العلم نور والجهل ظلام، ومن طلب العلم سهّل الله له طريقًا إلى الجنة.',
    'الوقت كالسيف إن لم تقطعه قطعك، فاغتنم كل دقيقة في المذاكرة.',
    'من جدّ وجد ومن زرع حصد، والنجاح يحتاج إلى صبر ومثابرة.',
    'القراءة غذاء العقل، وكل كتاب تقرؤه يفتح لك بابًا جديدًا من المعرفة.',
    'الصديق وقت الضيق، والعمل الصالح خير زاد ليوم الحساب.',
    'تعلّم من أخطائك ولا تيأس، فكل محاولة تقربك خطوة من هدفك.',
    'النظام في المذاكرة أهم من عدد الساعات، فراجع قليلًا كل يوم.',
    'الصبر مفتاح الفرج، ومن توكل على الله فهو حسبه.',
    'اجعل لكل مادة وقتًا محددًا، وخذ راحة قصيرة بين كل جلسة وأخرى.',
    'الأخلاق الحسنة تاج على رؤوس الأذكياء، فلا تفرّط فيها أبدًا.',
]
EN = [
    'The quick brown fox jumps over the lazy dog near the quiet river bank.',
    'Practice makes perfect, so type a little every day and watch your speed grow.',
    'Success is the sum of small efforts repeated day in and day out.',
    'A good student plans the week, studies in short sessions and takes breaks.',
    'Typing fast is useful, but typing correctly is what really saves your time.',
    'Reading every day builds a strong mind and gives you new ideas to share.',
    'Do not wait for the perfect moment, take the moment and make it perfect.',
    'Learning never exhausts the mind, it only makes it stronger and wiser.',
    'Keep your desk clean, your phone away and your goal clear in front of you.',
    'Small steps taken every day lead to big results in the long run.',
]

AR = [re.sub('[\u064b-\u0652]', '', x) for x in AR]


def _writable(d):
    try:
        os.makedirs(d, exist_ok=True)
        t = os.path.join(d, '.w')
        with open(t, 'w') as f:
            f.write('1')
        os.remove(t)
        return True
    except Exception:
        return False


def data_dir():
    exe = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    cands = []
    if os.environ.get('APPDATA'):
        cands.append(os.path.join(os.environ['APPDATA'], 'TanzilPC'))
    cands += [os.path.join(exe, 'TanzilData'), os.path.join(os.path.expanduser('~'), 'TanzilPC')]
    try:
        import tempfile
        cands.append(os.path.join(tempfile.gettempdir(), 'TanzilPC'))
    except Exception:
        pass
    for d in cands:
        if _writable(d):
            return d
    return None


DIR = data_dir()
DATA = os.path.join(DIR, 'data.json') if DIR else None


def log_crash(text):
    try:
        if DIR:
            with open(os.path.join(DIR, 'crash.log'), 'a', encoding='utf-8') as f:
                f.write('%s\n%s\n' % (datetime.datetime.now().isoformat(), text))
    except Exception:
        pass


def load():
    if not DATA:
        return {}
    try:
        with open(DATA, 'r', encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            return d
    except FileNotFoundError:
        return {}
    except Exception:
        try:
            os.replace(DATA, DATA + '.bad')
        except Exception:
            pass
    return {}


def save(d):
    if not DATA:
        return
    try:
        tmp = DATA + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        os.replace(tmp, DATA)
    except Exception:
        pass


def calc(passage, typed, seconds):
    """returns (wpm, accuracy%) using 5 chars = 1 word."""
    n = min(len(passage), len(typed))
    correct = sum(1 for i in range(n) if passage[i] == typed[i])
    minutes = max(seconds, 1.0) / 60.0
    wpm = (correct / 5.0) / minutes
    acc = 100.0 * correct / max(len(typed), 1)
    return wpm, acc


def beep_pattern(kind):
    def run():
        try:
            if winsound:
                seq = [(880, 250), (1175, 250), (1568, 400)] if kind == 'work_end' else [(1175, 250), (880, 400)]
                for f, d in seq:
                    winsound.Beep(f, d)
            else:
                print('\a', end='')
        except Exception:
            pass
    threading.Thread(target=run, daemon=True).start()


def main(tab=0, hook=None, theme=None):
    root = tk.Tk()
    global FONT
    try:
        import tkinter.font as tkfont
        fams = set(tkfont.families(root))
        for f in ('Tahoma', 'Segoe UI', 'Arial', 'Microsoft Sans Serif'):
            if f in fams:
                FONT = f
                break
        else:
            FONT = 'TkDefaultFont'
    except Exception:
        pass

    def on_err(exc, val, tb):
        import traceback
        log_crash(''.join(traceback.format_exception(exc, val, tb)))
    root.report_callback_exception = on_err
    root.title(APP)
    root.configure(bg=BG)
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    ww, wh = 640, min(560, sh - 70)
    root.geometry('%dx%d+%d+%d' % (ww, wh, max(0, (sw - ww) // 2), 5))
    root.minsize(600, 440)
    try:
        ico = os.path.join(getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__))), 'icon.ico')
        root.iconbitmap(ico)
    except Exception:
        pass
    store = load()
    if not isinstance(store.get('history'), list):
        store['history'] = []
    if not isinstance(store.get('sessions'), dict):
        store['sessions'] = {}

    def L(parent, text, size=11, color=TXT, bold=False, **kw):
        return tk.Label(parent, text=text, bg=kw.pop('bg', BG), fg=color, font=(FONT, size, 'bold' if bold else 'normal'), **kw)

    def B(parent, text, cmd, color=ACC, size=11, **kw):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg='white', activebackground='#38b57c', activeforeground='white',
                         relief='flat', font=(FONT, size, 'bold'), padx=14, pady=4, cursor='hand2', **kw)

    # header
    head = tk.Frame(root, bg=BG)
    head.pack(fill='x', pady=(8, 2))
    L(head, 'تنزيل', 22, GRN, True).pack()
    L(head, 'مدرب الكتابة  ·  تايمر المذاكرة  ·  بدون إنترنت', 9, SUB).pack()
    tk.Frame(head, bg=ACC, height=2, width=120).pack(pady=(6, 0))

    foot = L(root, 'تطوير: المصري Goo  ·  مجاني بدون إعلانات', 8, SUB)
    foot.pack(side='bottom', pady=4)

    tabs = tk.Frame(root, bg=BG)
    tabs.pack(fill='x', padx=16, pady=(6, 4))
    body = tk.Frame(root, bg=BG)
    body.pack(fill='both', expand=True, padx=16)
    f_type = tk.Frame(body, bg=BG)
    f_pomo = tk.Frame(body, bg=BG)
    tb = {}
    cur_tab = {'i': 0}
    cur_theme = {'n': 'dark'}

    def show(i):
        cur_tab['i'] = i
        f_type.pack_forget()
        f_pomo.pack_forget()
        (f_type if i == 0 else f_pomo).pack(fill='both', expand=True)
        for k, b in tb.items():
            b.config(bg=ACC if k == i else CARD, fg='white' if k == i else TXT)

    tb[1] = B(tabs, 'تايمر المذاكرة', lambda: show(1), CARD)
    tb[1].pack(side='right', expand=True, fill='x', padx=3)
    tb[0] = B(tabs, 'مدرب الكتابة', lambda: show(0), ACC)
    tb[0].pack(side='right', expand=True, fill='x', padx=3)

    # ---------- typing ----------
    ts = {'lang': 'ar', 'passage': '', 'start': None, 'limit': 60, 'running': False, 'job': None}
    row = tk.Frame(f_type, bg=BG)
    row.pack(fill='x', pady=2)
    lang_var = tk.StringVar(value='ar')
    lim_var = tk.IntVar(value=60)
    for txt, v in (('English', 'en'), ('عربي', 'ar')):
        tk.Radiobutton(row, text=txt, variable=lang_var, value=v, bg=BG, fg=TXT, selectcolor=CARD, activebackground=BG,
                       activeforeground=TXT, font=(FONT, 10), command=lambda: new_text()).pack(side='right', padx=6)
    L(row, ':اللغة', 10, SUB).pack(side='right', padx=4)
    for sec in (120, 60, 30):
        tk.Radiobutton(row, text='%d ث' % sec, variable=lim_var, value=sec, bg=BG, fg=TXT, selectcolor=CARD,
                       activebackground=BG, activeforeground=TXT, font=(FONT, 10)).pack(side='left', padx=4)
    L(row, ':المدة', 10, SUB).pack(side='left', padx=4)

    pass_card = tk.Frame(f_type, bg=CARD, padx=14, pady=12)
    pass_card.pack(fill='x', pady=4)
    pass_lbl = tk.Label(pass_card, text='', bg=CARD, fg=TXT, font=(FONT, 14), wraplength=560, justify='right')
    pass_lbl.pack(fill='x')
    pass_card.bind('<Configure>', lambda e: pass_lbl.config(wraplength=max(200, e.width - 30)))
    entry = tk.Entry(f_type, font=(FONT, 14), bg='#f4fbf6', fg='#102016', relief='flat', justify='right')
    entry.pack(fill='x', pady=4, ipady=6)
    stat = L(f_type, 'اضغط ابدأ ثم اكتب النص بالأعلى', 11, SUB)
    stat.pack(fill='x')
    brow = tk.Frame(f_type, bg=BG)
    brow.pack(pady=4)
    res = L(f_type, '', 12, GRN, True)
    res.pack()
    L(f_type, 'آخر النتائج', 10, SUB).pack(anchor='e')
    hist = tk.Listbox(f_type, bg=CARD, fg=TXT, font=(FONT, 10), relief='flat', height=4, highlightthickness=0, justify='right')
    hist.pack(fill='both', expand=True, pady=(2, 4))

    def refresh_hist():
        hist.delete(0, 'end')
        for h in reversed(store['history'][-30:]):
            hist.insert('end', '%s  |  %s  |  %.0f كلمة/د  |  دقة %.0f%%' % (h['d'], 'عربي' if h['l'] == 'ar' else 'EN', h['w'], h['a']))

    def new_text():
        stop_typing(False)
        ts['lang'] = lang_var.get()
        ts['passage'] = random.choice(AR if ts['lang'] == 'ar' else EN)
        if random.random() < 0.5:
            ts['passage'] += ' ' + random.choice(AR if ts['lang'] == 'ar' else EN)
        pass_lbl.config(text=ts['passage'])
        entry.config(state='normal', justify='right' if ts['lang'] == 'ar' else 'left', bg='#f4fbf6')
        entry.delete(0, 'end')
        res.config(text='')
        stat.config(text='اضغط على خانة الكتابة وابدأ، العدّاد بيشتغل مع أول حرف', fg=SUB)
        ts['start'] = None
        entry.focus_set()

    def stop_typing(finish=True):
        if ts['job']:
            try:
                root.after_cancel(ts['job'])
            except Exception:
                pass
            ts['job'] = None
        if finish and ts['start'] is not None:
            typed = entry.get()
            secs = time.monotonic() - ts['start']
            w, a = calc(ts['passage'], typed, secs)
            entry.config(state='disabled')
            res.config(text='السرعة: %.0f كلمة/دقيقة   ·   الدقة: %.0f%%' % (w, a))
            stat.config(text='خلصت! اضغط نص جديد للمحاولة تاني', fg=SUB)
            store['history'].append({'d': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'), 'l': ts['lang'], 'w': round(w, 1), 'a': round(a, 1)})
            store['history'] = store['history'][-200:]
            save(store)
            refresh_hist()
            ts['start'] = None

    def tick():
        if ts['start'] is None:
            return
        left = int(ts['limit'] - (time.monotonic() - ts['start']))
        typed = entry.get()
        n = min(len(typed), len(ts['passage']))
        bad = sum(1 for i in range(n) if ts['passage'][i] != typed[i])
        stat.config(text='الوقت المتبقي: %d ث   ·   أخطاء: %d' % (max(left, 0), bad), fg=SUB)
        if left <= 0 or len(typed) >= len(ts['passage']):
            stop_typing(True)
            return
        ts['job'] = root.after(250, tick)

    def on_key(ev):
        if ts['start'] is None and entry.cget('state') == 'normal' and ev.keysym not in ('Shift_L', 'Shift_R', 'Control_L', 'Control_R', 'Alt_L', 'Alt_R', 'Caps_Lock', 'Tab'):
            ts['start'] = time.monotonic()
            ts['limit'] = lim_var.get()
            tick()
        typed = entry.get()
        pref = ts['passage'][:len(typed)]
        entry.config(bg='#f4fbf6' if typed == pref else '#f7d6d4')

    entry.bind('<KeyRelease>', on_key)
    for seq in ('<<Paste>>', '<Control-v>', '<Control-V>', '<Shift-Insert>', '<Button-2>'):
        entry.bind(seq, lambda e: 'break')
    B(brow, 'نص جديد', new_text).pack(side='right', padx=6)
    B(brow, 'إنهاء الآن', lambda: stop_typing(True), '#7a2e2e', 10).pack(side='right', padx=6)

    # ---------- pomodoro ----------
    ps = {'phase': 'work', 'left': 25 * 60, 'running': False, 'end': 0, 'job': None}
    today = datetime.date.today().isoformat()
    sess = store['sessions']
    ph_lbl = L(f_pomo, 'وقت المذاكرة', 16, GRN, True)
    ph_lbl.pack(pady=(14, 0))
    clock = tk.Label(f_pomo, text='25:00', bg=BG, fg=TXT, font=(FONT, 60, 'bold'))
    clock.pack(pady=4)
    cnt = L(f_pomo, '', 12, SUB)
    cnt.pack()
    set_row = tk.Frame(f_pomo, bg=BG)
    set_row.pack(pady=10)
    w_var = tk.IntVar(value=25)
    b_var = tk.IntVar(value=5)
    L(set_row, 'دقائق المذاكرة', 10, SUB).grid(row=0, column=3, padx=6)
    tk.Spinbox(set_row, from_=1, to=120, width=4, textvariable=w_var, font=(FONT, 12), justify='center').grid(row=0, column=2)
    L(set_row, 'دقائق الراحة', 10, SUB).grid(row=0, column=1, padx=6)
    tk.Spinbox(set_row, from_=1, to=60, width=4, textvariable=b_var, font=(FONT, 12), justify='center').grid(row=0, column=0)

    def upd_count():
        cnt.config(text='جلسات اليوم: %d' % sess.get(today, 0))

    def mmss(s):
        s = max(int(s + 0.999), 0)
        return '%02d:%02d' % (s // 60, s % 60)

    def getm(var, default):
        try:
            return max(1, int(var.get()))
        except Exception:
            return default

    def set_phase(p):
        ps['phase'] = p
        ps['left'] = (getm(w_var, 25) if p == 'work' else getm(b_var, 5)) * 60
        ph_lbl.config(text='وقت المذاكرة' if p == 'work' else 'وقت الراحة', fg=GRN if p == 'work' else YEL)
        clock.config(text=mmss(ps['left']))

    def ptick():
        if not ps['running']:
            return
        left = ps['end'] - time.monotonic()
        if left <= 0:
            if ps['phase'] == 'work':
                sess[today] = sess.get(today, 0) + 1
                store['sessions'] = sess
                save(store)
                upd_count()
                beep_pattern('work_end')
                set_phase('break')
            else:
                beep_pattern('break_end')
                set_phase('work')
            ps['end'] = time.monotonic() + ps['left']
            left = ps['left']
        clock.config(text=mmss(left))
        ps['job'] = root.after(200, ptick)

    def p_start():
        if ps['running']:
            return
        ps['running'] = True
        ps['end'] = time.monotonic() + ps['left']
        start_btn.config(state='disabled')
        pause_btn.config(state='normal')
        ptick()

    def p_pause():
        if not ps['running']:
            return
        ps['left'] = max(ps['end'] - time.monotonic(), 0)
        ps['running'] = False
        start_btn.config(state='normal', text='كمّل')
        pause_btn.config(state='disabled')

    def p_reset():
        ps['running'] = False
        if ps['job']:
            try:
                root.after_cancel(ps['job'])
            except Exception:
                pass
        set_phase('work')
        start_btn.config(state='normal', text='ابدأ')
        pause_btn.config(state='disabled')

    pb = tk.Frame(f_pomo, bg=BG)
    pb.pack(pady=6)
    start_btn = B(pb, 'ابدأ', p_start, ACC, 13)
    start_btn.pack(side='right', padx=6)
    pause_btn = B(pb, 'إيقاف مؤقت', p_pause, CARD, 11, state='disabled')
    pause_btn.pack(side='right', padx=6)
    B(pb, 'إعادة', p_reset, '#7a2e2e', 11).pack(side='right', padx=6)
    B(pb, 'جرّب الصوت', lambda: beep_pattern('work_end'), CARD, 9).pack(side='left', padx=6)
    L(f_pomo, 'التغيير في الدقائق يظهر بعد الضغط على إعادة', 9, SUB).pack(pady=4)

    upd_count()
    refresh_hist()
    new_text()
    def apply_theme(name):
        global BG, CARD, TXT, SUB, GRN, YEL
        new = THEMES.get(name, THEMES['dark'])
        old = dict(bg=BG, card=CARD, txt=TXT, sub=SUB, grn=GRN, yel=YEL)
        mp = dict((old[k], new[k]) for k in old)
        BG, CARD, TXT, SUB, GRN, YEL = new['bg'], new['card'], new['txt'], new['sub'], new['grn'], new['yel']

        def walk(w):
            is_card_btn = False
            try:
                is_card_btn = isinstance(w, tk.Button) and str(w.cget('bg')) == old['card']
            except Exception:
                pass
            for opt in ('bg', 'fg', 'selectcolor', 'activebackground', 'activeforeground'):
                try:
                    v = str(w.cget(opt))
                except Exception:
                    continue
                if v in mp:
                    try:
                        w.configure(**{opt: mp[v]})
                    except Exception:
                        pass
            if is_card_btn:
                try:
                    w.configure(fg=TXT)
                except Exception:
                    pass
            for c in w.winfo_children():
                walk(c)
        walk(root)
        for k, b in tb.items():
            b.config(bg=ACC if k == cur_tab['i'] else CARD, fg='white' if k == cur_tab['i'] else TXT)
        theme_btn.config(text='وضع داكن' if name == 'light' else 'وضع فاتح')
        cur_theme['n'] = name

    def toggle_theme():
        n = 'light' if cur_theme['n'] == 'dark' else 'dark'
        apply_theme(n)
        store['theme'] = n
        save(store)

    theme_btn = tk.Button(head, text='وضع فاتح', command=toggle_theme, bg=CARD, fg=TXT, relief='flat', font=(FONT, 9), cursor='hand2')
    theme_btn.place(x=4, y=4)
    if (theme or store.get('theme')) == 'light':
        apply_theme('light')
    show(tab)

    def on_close():
        if ps['running']:
            try:
                from tkinter import messagebox
                if not messagebox.askyesno(APP, 'التايمر شغال. تقفل البرنامج؟'):
                    return
            except Exception:
                pass
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', on_close)
    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass
    if hook:
        ns = dict(locals())
        root.after(800, lambda: hook(ns))
    root.mainloop()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--selftest':
        p = 'a' * 50
        print('wpm_acc', calc(p, p, 60), calc(p, 'a' * 25 + 'b' * 25, 30))
        print('data', DATA)
        sys.exit(0)
    t = 0
    th = None
    size = None
    args = sys.argv[1:]
    for i, a in enumerate(args):
        try:
            if a == '--tab':
                t = int(args[i + 1])
            elif a == '--theme':
                th = args[i + 1]
        except Exception:
            pass
    try:
        main(t, None, th)
    except Exception:
        import traceback
        log_crash(traceback.format_exc())
        try:
            from tkinter import messagebox
            messagebox.showerror('تنزيل', 'حصل خطأ غير متوقع. اتسجل في ملف crash.log جوه مجلد TanzilPC.')
        except Exception:
            pass
        sys.exit(1)
