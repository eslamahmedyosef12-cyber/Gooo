# -*- coding: utf-8 -*-
"""تنزيل PC: مدرب كتابة + تايمر مذاكرة. أوفلاين بالكامل. متوافق مع Python 3.7."""
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

AR_EASY = [
    'القراءة تفتح العقل.', 'من جد وجد.', 'العلم نور.', 'الوقت من ذهب.', 'اطلب العلم من المهد.',
    'الصبر مفتاح الفرج.', 'خير الكلام ما قل ودل.', 'النظام يصنع النجاح.', 'ابدأ الآن ولا تؤجل.',
    'التعب اليوم راحة الغد.', 'المذاكرة كل يوم تصنع الفرق.', 'اجتهد وتوكل على الله.',
]
EN_EASY = [
    'Study a little every day.', 'Small steps win the race.', 'Focus on one task at a time.',
    'Read, write and repeat.', 'Practice makes perfect.', 'Never give up on your goals.',
    'Start now, not tomorrow.', 'Good habits build a bright future.', 'Take a short break and return.',
    'Slow and steady wins.', 'Ask questions and keep learning.', 'Plan your day and follow it.',
]
AR_HARD = [
    'في عام 2024 قرأت 12 كتابًا، وحللت 150 مسألة، وراجعت 8 دروس كاملة؛ فهل ستفعل أكثر منها؟',
    'الجدول: السبت 9:30 رياضيات، الأحد 11:00 فيزياء، الاثنين 8:15 كيمياء، الثلاثاء 10:45 أحياء.',
    'قال المعلم: "راجع الدرس (3) والتمرين (7) قبل الحصة"، ثم أضاف: النجاح يحتاج إلى 100% من الجهد!',
    'اشتريت 3 كراسات بـ 45 جنيهًا، و5 أقلام بـ 20 جنيهًا؛ فكم دفعت في المجموع؟ الجواب: 65 جنيهًا.',
    'الامتحان يبدأ الساعة 9:00 صباحًا، ومدته ساعتان ونصف؛ احضر قبل الموعد بربع ساعة على الأقل.',
]
EN_HARD = [
    'In 2024, I read 12 books, solved 150 problems, and reviewed 8 full lessons; will you do more?',
    'Schedule: Sat 9:30 Math, Sun 11:00 Physics, Mon 8:15 Chemistry, Tue 10:45 Biology (Room 4B).',
    'The teacher said, "Review lesson (3) and exercise (7) before class," then added: success needs 100% effort!',
    'He bought 3 notebooks for $4.50 each and 5 pens for $2.00 each; the total was $23.50, right?',
    'The exam starts at 9:00 a.m. and lasts 2.5 hours; arrive at least 15 minutes early, please.',
]
AR = [re.sub('[\u064b-\u0652]', '', x) for x in AR]
AR_EASY = [re.sub('[\u064b-\u0652]', '', x) for x in AR_EASY]
AR_HARD = [re.sub('[\u064b-\u0652]', '', x) for x in AR_HARD]
POOLS = {
    ('ar', 'easy'): AR_EASY, ('en', 'easy'): EN_EASY,
    ('ar', 'mid'): AR, ('en', 'mid'): EN,
    ('ar', 'hard'): AR_HARD, ('en', 'hard'): EN_HARD,
}
CUSTOM_MAX = 250


def clean_custom(text):
    """normalise a user supplied passage: collapse whitespace, cap length. returns '' if too short."""
    t = re.sub(r'\s+', ' ', text or '').strip()
    t = re.sub('[\u064b-\u0652]', '', t)
    if len(t) > CUSTOM_MAX:
        t = t[:CUSTOM_MAX].rstrip()
    return t if len(t) >= 5 else ''


def has_arabic(t):
    return any('\u0600' <= c <= '\u06ff' for c in t)


def week_stats(history, today):
    """last-7-days average wpm per day (oldest first), plus overall avg/best/count."""
    days = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
    per = []
    for d in days:
        k = d.isoformat()
        ws = [h['w'] for h in history if isinstance(h, dict) and str(h.get('d', ''))[:10] == k and isinstance(h.get('w'), (int, float))]
        per.append((d, sum(ws) / len(ws) if ws else 0.0))
    allw = [h['w'] for h in history if isinstance(h, dict) and isinstance(h.get('w'), (int, float))]
    avg = sum(allw) / len(allw) if allw else 0.0
    return per, avg, (max(allw) if allw else 0.0), len(allw)


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


def main(tab=0, hook=None, theme=None, size=None):
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
    if size:
        root.geometry('%dx%d+0+0' % size)
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
    if not isinstance(store.get('tasks'), list):
        store['tasks'] = []
    if not isinstance(store.get('tasks'), list):
        store['tasks'] = []
    if not isinstance(store.get('lessons'), list):
        store['lessons'] = []
    if not isinstance(store.get('daily_goal'), int):
        store['daily_goal'] = 120

    def L(parent, text, size=11, color=TXT, bold=False, **kw):
        return tk.Label(parent, text=text, bg=kw.pop('bg', BG), fg=color, font=(FONT, size, 'bold' if bold else 'normal'), **kw)

    def B(parent, text, cmd, color=ACC, size=11, **kw):
        return tk.Button(parent, text=text, command=cmd, bg=color, fg='white', activebackground='#38b57c', activeforeground='white',
                         relief='flat', font=(FONT, size, 'bold'), padx=kw.pop('bpad', 14), pady=4, cursor='hand2', **kw)

    # background photo (pre-dimmed PNG so text stays readable); fails safe to a plain colour
    art = {'img': None}
    bg_lbl = tk.Label(root, bd=0, bg=BG)

    def set_art(name):
        try:
            base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            art['img'] = tk.PhotoImage(file=os.path.join(base, 'bg_%s.png' % name))
            bg_lbl.config(image=art['img'])
            bg_lbl.place(relx=0.5, rely=0.5, anchor='center')
        except Exception:
            try:
                bg_lbl.place_forget()
            except Exception:
                pass
    set_art('dark')

    # header
    head = tk.Frame(root, bg=BG)
    head.pack(pady=(8, 2))
    L(head, 'تنزيل', 22, GRN, True).pack()
    L(head, 'مدرب الكتابة  ·  تايمر المذاكرة  ·  بدون إنترنت', 9, SUB).pack()
    tk.Frame(head, bg=ACC, height=2, width=120).pack(pady=(6, 0))

    foot = L(root, 'تطوير: المصري Goo  ·  مجاني بدون إعلانات', 8, SUB)
    foot.pack(side='bottom', pady=4)

    tabs = tk.Frame(root, bg=BG)
    tabs.pack(fill='x', padx=30, pady=(6, 4))
    body = tk.Frame(root, bg=BG)
    body.pack(fill='both', expand=True, padx=30)
    f_type = tk.Frame(body, bg=BG)
    f_pomo = tk.Frame(body, bg=BG)
    f_stat = tk.Frame(body, bg=BG)
    f_tasks = tk.Frame(body, bg=BG)
    f_subjects = tk.Frame(body, bg=BG)
    tb = {}
    cur_tab = {'i': 0}
    cur_theme = {'n': 'dark'}

    def show(i):
        cur_tab['i'] = i
        f_type.pack_forget()
        f_pomo.pack_forget()
        f_stat.pack_forget()
        f_tasks.pack_forget()
        f_subjects.pack_forget()
        target = (f_type if i == 0 else f_pomo if i == 1 else
                  f_stat if i == 2 else f_tasks if i == 3 else f_subjects)
        target.pack(fill='both', expand=True)
        if i == 2:
            refresh_stats()
        if i == 3:
            refresh_tasks()
        if i == 4:
            refresh_subjects()
        for k, b in tb.items():
            b.config(bg=ACC if k == i else CARD, fg='white' if k == i else TXT)

    tb[4] = B(tabs, 'موادي', lambda: show(4), CARD, 10, bpad=4)
    tb[4].pack(side='right', expand=True, fill='x', padx=3)
    tb[3] = B(tabs, 'مهامي', lambda: show(3), CARD, 10, bpad=4)
    tb[3].pack(side='right', expand=True, fill='x', padx=3)
    tb[2] = B(tabs, 'إحصائياتي', lambda: show(2), CARD, 10, bpad=4)
    tb[2].pack(side='right', expand=True, fill='x', padx=3)
    tb[1] = B(tabs, 'تايمر المذاكرة', lambda: show(1), CARD, 10, bpad=4)
    tb[1].pack(side='right', expand=True, fill='x', padx=3)
    tb[0] = B(tabs, 'مدرب الكتابة', lambda: show(0), ACC, 10, bpad=4)
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

    row2 = tk.Frame(f_type, bg=BG)
    row2.pack(fill='x', pady=2)
    lvl_var = tk.StringVar(value='mid')
    for txt, v in (('صعب', 'hard'), ('متوسط', 'mid'), ('سهل', 'easy')):
        tk.Radiobutton(row2, text=txt, variable=lvl_var, value=v, bg=BG, fg=TXT, selectcolor=CARD, activebackground=BG,
                       activeforeground=TXT, font=(FONT, 10), command=lambda: new_text()).pack(side='right', padx=6)
    L(row2, ':المستوى', 10, SUB).pack(side='right', padx=4)

    def set_custom(text):
        t = clean_custom(text)
        if not t:
            return False
        ts['custom'] = t
        new_text(True)
        return True

    def custom_dialog():
        top = tk.Toplevel(root)
        top.title('اكتب نصك')
        top.configure(bg=BG)
        top.transient(root)
        L(top, 'الصق أو اكتب النص اللي عايز تتمرن عليه (حتى %d حرف)' % CUSTOM_MAX, 10, SUB).pack(padx=12, pady=(10, 4))
        box = tk.Text(top, width=48, height=6, font=(FONT, 12), wrap='word')
        box.pack(padx=12, pady=4)
        msg = L(top, '', 9, BAD)
        msg.pack()

        def ok():
            if set_custom(box.get('1.0', 'end')):
                top.destroy()
            else:
                msg.config(text='النص قصير جدًا (5 حروف على الأقل)')
        fr = tk.Frame(top, bg=BG)
        fr.pack(pady=8)
        B(fr, 'ابدأ التمرين', ok).pack(side='right', padx=6)
        B(fr, 'إلغاء', top.destroy, CARD, 10).pack(side='right', padx=6)
        box.focus_set()
        try:
            top.grab_set()
        except Exception:
            pass

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

    def new_text(keep_custom=False):
        if not keep_custom:
            ts['custom'] = None
        stop_typing(False)
        ts['lang'] = lang_var.get()
        if ts.get('custom'):
            ts['passage'] = ts['custom']
            ts['lang'] = 'ar' if has_arabic(ts['custom']) else 'en'
        else:
            pool = POOLS[(ts['lang'], lvl_var.get())]
            ts['passage'] = random.choice(pool)
            if lvl_var.get() == 'mid' and random.random() < 0.5:
                ts['passage'] += ' ' + random.choice(pool)
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
            refresh_stats()
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
    B(brow, 'اكتب نصك', custom_dialog, CARD, 10).pack(side='right', padx=6)
    B(brow, 'إنهاء الآن', lambda: stop_typing(True), '#7a2e2e', 10).pack(side='right', padx=6)

    # ---------- pomodoro ----------
    ps = {'phase': 'work', 'left': 25 * 60, 'running': False, 'end': 0, 'job': None}
    today = datetime.date.today().isoformat()
    sess = store['sessions']
    if not isinstance(store.get('mins'), dict):
        store['mins'] = {}
    mins = store['mins']
    ph_lbl = L(f_pomo, 'وقت المذاكرة', 16, GRN, True)
    ph_lbl.pack(pady=(14, 0))
    clock = tk.Label(f_pomo, text='25:00', bg=BG, fg=TXT, font=(FONT, 48, 'bold'))
    clock.pack(pady=4)
    cnt = L(f_pomo, '', 12, SUB)
    cnt.pack()
    set_row = tk.Frame(f_pomo, bg=BG)
    set_row.pack(pady=6)
    w_var = tk.IntVar(value=25)
    b_var = tk.IntVar(value=5)
    L(set_row, 'دقائق المذاكرة', 10, SUB).grid(row=0, column=3, padx=6)
    tk.Spinbox(set_row, from_=1, to=120, width=4, textvariable=w_var, font=(FONT, 12), justify='center').grid(row=0, column=2)
    L(set_row, 'دقائق الراحة', 10, SUB).grid(row=0, column=1, padx=6)
    tk.Spinbox(set_row, from_=1, to=60, width=4, textvariable=b_var, font=(FONT, 12), justify='center').grid(row=0, column=0)
    l_var = tk.IntVar(value=15)
    g_var = tk.IntVar(value=4)
    set_row2 = tk.Frame(f_pomo, bg=BG)
    set_row2.pack(pady=2)
    L(set_row2, 'راحة طويلة (كل 4 جلسات)', 10, SUB).grid(row=0, column=3, padx=6)
    tk.Spinbox(set_row2, from_=1, to=90, width=4, textvariable=l_var, font=(FONT, 12), justify='center').grid(row=0, column=2)
    L(set_row2, 'هدف اليوم (جلسات)', 10, SUB).grid(row=0, column=1, padx=6)
    tk.Spinbox(set_row2, from_=1, to=20, width=4, textvariable=g_var, font=(FONT, 12), justify='center').grid(row=0, column=0)
    top_var = tk.IntVar(value=0)

    def set_top():
        try:
            root.attributes('-topmost', bool(top_var.get()))
        except Exception:
            pass
    tk.Checkbutton(f_pomo, text='خلي النافذة فوق باقي البرامج', variable=top_var, command=set_top, bg=BG, fg=SUB,
                   selectcolor=CARD, activebackground=BG, activeforeground=TXT, font=(FONT, 9)).pack(pady=2)

    def upd_count():
        n = sess.get(today, 0)
        g = getm(g_var, 4)
        cnt.config(text='جلسات اليوم: %d من %d%s  ·  دقائق المذاكرة: %d' % (n, g, '  (تم الهدف)' if n >= g else '', mins.get(today, 0)))
        try:
            refresh_tasks()
        except Exception:
            pass

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
        ps['left'] = (getm(w_var, 25) if p == 'work' else getm(l_var, 15) if p == 'long' else getm(b_var, 5)) * 60
        ph_lbl.config(text={'work': 'وقت المذاكرة', 'break': 'وقت الراحة', 'long': 'راحة طويلة'}[p], fg=GRN if p == 'work' else YEL)
        clock.config(text=mmss(ps['left']))

    def ptick():
        if not ps['running']:
            return
        left = ps['end'] - time.monotonic()
        if left <= 0:
            if ps['phase'] == 'work':
                sess[today] = sess.get(today, 0) + 1
                mins[today] = mins.get(today, 0) + getm(w_var, 25)
                store['sessions'] = sess
                save(store)
                upd_count()
                beep_pattern('work_end')
                set_phase('long' if sess[today] % 4 == 0 else 'break')
            else:
                beep_pattern('break_end')
                set_phase('work')
            ps['end'] = time.monotonic() + ps['left']
            left = ps['left']
        clock.config(text=mmss(left))
        try:
            root.title('%s  %s' % (mmss(left), APP))
        except Exception:
            pass
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
        root.title(APP)
        pause_btn.config(state='disabled')

    def p_reset():
        ps['running'] = False
        if ps['job']:
            try:
                root.after_cancel(ps['job'])
            except Exception:
                pass
        set_phase('work')
        root.title(APP)
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
    L(f_pomo, 'التغيير في الدقائق يظهر بعد الضغط على إعادة', 9, SUB).pack(pady=2)

    st_sum = L(f_stat, '', 12, TXT, True)
    st_sum.pack(pady=(10, 2))
    st_sum2 = L(f_stat, '', 10, SUB)
    st_sum2.pack()
    L(f_stat, 'متوسط سرعتك في آخر 7 أيام (كلمة/دقيقة)', 10, SUB).pack(pady=(10, 2))
    chart = tk.Canvas(f_stat, width=520, height=170, bg=BG, highlightthickness=0)
    chart.pack(pady=4)

    def refresh_stats():
        per, avg, best, n = week_stats(store['history'], datetime.date.today())
        st_sum.config(text='المتوسط: %.0f   ·   أفضل نتيجة: %.0f   ·   عدد التمارين: %d' % (avg, best, n))
        wk = sum(v for k, v in mins.items() if k >= (datetime.date.today() - datetime.timedelta(days=6)).isoformat() if isinstance(v, int))
        ws = sum(v for k, v in sess.items() if k >= (datetime.date.today() - datetime.timedelta(days=6)).isoformat() if isinstance(v, int))
        st_sum2.config(text='جلسات مذاكرة آخر 7 أيام: %d   ·   دقائق المذاكرة: %d' % (ws, wk))
        chart.delete('all')
        mx = max([v for _, v in per] + [10.0])
        for i, (d, v) in enumerate(per):
            x = 20 + i * 72
            h = int(110 * v / mx)
            chart.create_rectangle(x, 130 - h, x + 44, 130, fill=ACC, outline='')
            if v:
                chart.create_text(x + 22, 122 - h, text='%.0f' % v, fill=TXT, font=(FONT, 9))
            chart.create_text(x + 22, 146, text=d.strftime('%d/%m'), fill=SUB, font=(FONT, 9))
        chart.create_line(10, 130, 510, 130, fill=SUB)

    def reset_stats():
        try:
            from tkinter import messagebox
            if not messagebox.askyesno(APP, 'تمسح كل النتائج والإحصائيات؟ الأمر ده مينفعش يتراجع عنه.'):
                return
        except Exception:
            return
        wipe_stats()

    def wipe_stats():
        store['history'] = []
        store['sessions'].clear()
        mins.clear()
        save(store)
        refresh_hist()
        refresh_stats()
        upd_count()
    B(f_stat, 'مسح الإحصائيات', reset_stats, '#7a2e2e', 10).pack(pady=8)


    # ---------- tasks and daily goal ----------
    L(f_tasks, 'مركز المهام والأهداف', 17, GRN, True).pack(pady=(10, 4))
    L(f_tasks, 'اكتب مهام مذاكرتك، وحدد ما أنجزته، وتابع هدفك اليومي.', 9, SUB).pack()

    goal_box = tk.Frame(f_tasks, bg=CARD, padx=10, pady=8)
    goal_box.pack(fill='x', pady=8)
    goal_var = tk.IntVar(value=store.get('daily_goal', 120))
    L(goal_box, 'هدف المذاكرة اليومي بالدقائق', 10, TXT, True, bg=CARD).pack(side='right', padx=6)
    goal_spin = tk.Spinbox(goal_box, from_=15, to=720, increment=15, width=5,
                           textvariable=goal_var, font=(FONT, 11), justify='center')
    goal_spin.pack(side='right', padx=5)
    goal_progress = L(goal_box, '', 10, GRN, True, bg=CARD)
    goal_progress.pack(side='left', padx=6)

    task_entry = tk.Entry(f_tasks, font=(FONT, 12), bg='#f4fbf6', fg='#102016',
                          relief='flat', justify='right')
    task_entry.pack(fill='x', pady=(4, 3), ipady=6)

    task_list = tk.Listbox(f_tasks, bg=CARD, fg=TXT, font=(FONT, 11),
                           relief='flat', height=9, highlightthickness=0,
                           selectbackground=ACC, activestyle='none', justify='right')
    task_list.pack(fill='both', expand=True, pady=4)

    task_hint = L(f_tasks, 'اختار مهمة واضغط إنجاز لتظهر عليها علامة x', 9, SUB)
    task_hint.pack()

    def refresh_tasks():
        task_list.delete(0, 'end')
        tasks = store.get('tasks', [])
        for task in tasks:
            if isinstance(task, dict):
                mark = '[x]' if task.get('done') else '[  ]'
                task_list.insert('end', '%s  %s' % (mark, task.get('title', 'مهمة بدون اسم')))
        try:
            goal = max(15, int(goal_var.get()))
        except Exception:
            goal = 120
        done_minutes = store.get('mins', {}).get(datetime.date.today().isoformat(), 0)
        pct = min(100, int(100.0 * done_minutes / max(goal, 1)))
        goal_progress.config(text='إنجاز الهدف: %d%%  (%d / %d دقيقة)' % (pct, done_minutes, goal))

    def add_task():
        title = task_entry.get().strip()
        if not title:
            task_hint.config(text='اكتب اسم المهمة أولًا', fg=BAD)
            return
        if len(title) > 100:
            title = title[:100]
        store.setdefault('tasks', []).append({'title': title, 'done': False,
                                               'created': datetime.date.today().isoformat()})
        save(store)
        task_entry.delete(0, 'end')
        task_hint.config(text='تمت إضافة المهمة', fg=GRN)
        refresh_tasks()

    def selected_task_index():
        selected = task_list.curselection()
        return selected[0] if selected else None

    def toggle_task():
        idx = selected_task_index()
        if idx is None or idx >= len(store.get('tasks', [])):
            task_hint.config(text='اختار مهمة من القائمة أولًا', fg=BAD)
            return
        task = store['tasks'][idx]
        if isinstance(task, dict):
            task['done'] = not bool(task.get('done'))
            save(store)
            refresh_tasks()
            task_list.selection_set(idx)

    def delete_task():
        idx = selected_task_index()
        if idx is None or idx >= len(store.get('tasks', [])):
            task_hint.config(text='اختار مهمة لحذفها أولًا', fg=BAD)
            return
        del store['tasks'][idx]
        save(store)
        refresh_tasks()
        task_hint.config(text='تم حذف المهمة', fg=SUB)

    def save_goal():
        try:
            value = max(15, min(720, int(goal_var.get())))
        except Exception:
            value = 120
        store['daily_goal'] = value
        goal_var.set(value)
        save(store)
        refresh_tasks()
        task_hint.config(text='تم حفظ هدفك اليومي', fg=GRN)

    task_buttons = tk.Frame(f_tasks, bg=BG)
    task_buttons.pack(fill='x', pady=5)
    B(task_buttons, 'إضافة مهمة', add_task, ACC, 10).pack(side='right', padx=3)
    B(task_buttons, 'إنجاز / تراجع', toggle_task, CARD, 10).pack(side='right', padx=3)
    B(task_buttons, 'حذف المهمة', delete_task, '#7a2e2e', 10).pack(side='right', padx=3)
    B(task_buttons, 'حفظ الهدف', save_goal, CARD, 10).pack(side='left', padx=3)
    task_entry.bind('<Return>', lambda e: add_task())

    # ---------- subject and lesson tracker ----------
    if not isinstance(store.get('lessons'), list):
        store['lessons'] = []

    L(f_subjects, 'خطة المواد والدروس', 17, GRN, True).pack(pady=(10, 3))
    L(f_subjects, 'سجّل كل درس، وحدد ما أنهيته، وتابع تقدمك في المنهج.', 9, SUB).pack()

    subject_entry = tk.Entry(f_subjects, font=(FONT, 11), bg='#f4fbf6',
                             fg='#102016', relief='flat', justify='right')
    subject_entry.pack(fill='x', pady=(8, 3), ipady=5)
    subject_entry.insert(0, 'اسم المادة')

    lesson_entry = tk.Entry(f_subjects, font=(FONT, 11), bg='#f4fbf6',
                            fg='#102016', relief='flat', justify='right')
    lesson_entry.pack(fill='x', pady=3, ipady=5)
    lesson_entry.insert(0, 'اسم الدرس')

    lesson_list = tk.Listbox(f_subjects, bg=CARD, fg=TXT, font=(FONT, 10),
                             relief='flat', height=8, highlightthickness=0,
                             selectbackground=ACC, activestyle='none', justify='right')
    lesson_list.pack(fill='both', expand=True, pady=4)

    lesson_summary = L(f_subjects, '', 9, SUB)
    lesson_summary.pack()

    def refresh_subjects():
        lesson_list.delete(0, 'end')
        lessons = store.get('lessons', [])
        total = 0
        completed = 0
        for item in lessons:
            if not isinstance(item, dict):
                continue
            total += 1
            done = bool(item.get('done'))
            if done:
                completed += 1
            mark = '[x]' if done else '[  ]'
            lesson_list.insert('end', '%s  %s  -  %s' % (
                mark, item.get('subject', 'مادة'), item.get('title', 'درس')))
        pct = int(100.0 * completed / total) if total else 0
        lesson_summary.config(text='إنجاز المنهج: %d%%  ·  %d من %d درس' %
                              (pct, completed, total))

    def add_lesson():
        subject = subject_entry.get().strip()
        title = lesson_entry.get().strip()
        if subject == 'اسم المادة':
            subject = ''
        if title == 'اسم الدرس':
            title = ''
        if not subject or not title:
            lesson_summary.config(text='اكتب اسم المادة واسم الدرس أولًا', fg=BAD)
            return
        if len(subject) > 50 or len(title) > 100:
            lesson_summary.config(text='اسم المادة 50 حرفًا والدرس 100 حرف كحد أقصى', fg=BAD)
            return
        store.setdefault('lessons', []).append({
            'subject': subject, 'title': title, 'done': False,
            'created': datetime.date.today().isoformat()
        })
        save(store)
        subject_entry.delete(0, 'end')
        lesson_entry.delete(0, 'end')
        refresh_subjects()
        lesson_summary.config(text='تمت إضافة الدرس وحفظه', fg=GRN)

    def selected_lesson_index():
        selected = lesson_list.curselection()
        return selected[0] if selected else None

    def toggle_lesson():
        idx = selected_lesson_index()
        lessons = store.get('lessons', [])
        if idx is None or idx >= len(lessons):
            lesson_summary.config(text='اختار درسًا من القائمة أولًا', fg=BAD)
            return
        item = lessons[idx]
        if isinstance(item, dict):
            item['done'] = not bool(item.get('done'))
            item['completed'] = (datetime.date.today().isoformat()
                                 if item['done'] else '')
            save(store)
            refresh_subjects()
            lesson_list.selection_set(idx)

    def delete_lesson():
        idx = selected_lesson_index()
        lessons = store.get('lessons', [])
        if idx is None or idx >= len(lessons):
            lesson_summary.config(text='اختار درسًا لحذفه أولًا', fg=BAD)
            return
        del lessons[idx]
        save(store)
        refresh_subjects()
        lesson_summary.config(text='تم حذف الدرس', fg=SUB)

    lesson_buttons = tk.Frame(f_subjects, bg=BG)
    lesson_buttons.pack(fill='x', pady=5)
    B(lesson_buttons, 'إضافة درس', add_lesson, ACC, 9).pack(side='right', padx=3)
    B(lesson_buttons, 'تم / لم يتم', toggle_lesson, CARD, 9).pack(side='right', padx=3)
    B(lesson_buttons, 'حذف', delete_lesson, '#7a2e2e', 9).pack(side='right', padx=3)
    lesson_entry.bind('<Return>', lambda e: add_lesson())

    def clear_ph(ent, ph):
        def f(e):
            if ent.get() == ph:
                ent.delete(0, 'end')
        ent.bind('<FocusIn>', f)
    clear_ph(subject_entry, 'اسم المادة')
    clear_ph(lesson_entry, 'اسم الدرس')
    refresh_subjects()

    def apply_restore(incoming):
        """replace data with a sanitised copy of `incoming`; keeps the live sess/mins dict objects."""
        if not isinstance(incoming, dict):
            raise ValueError('صيغة الملف غير صحيحة')

        def ints(d):
            out = {}
            if isinstance(d, dict):
                for k, v in d.items():
                    if isinstance(k, str) and isinstance(v, int) and not isinstance(v, bool) and v >= 0:
                        out[k] = v
            return out

        def good_hist(h):
            return (isinstance(h, dict) and isinstance(h.get('d'), str) and h.get('l') in ('ar', 'en')
                    and isinstance(h.get('w'), (int, float)) and isinstance(h.get('a'), (int, float)))
        new_hist = [h for h in incoming.get('history', []) if good_hist(h)][-200:] if isinstance(incoming.get('history'), list) else []
        new_tasks = [t for t in incoming.get('tasks', []) if isinstance(t, dict)] if isinstance(incoming.get('tasks'), list) else []
        new_less = [t for t in incoming.get('lessons', []) if isinstance(t, dict)] if isinstance(incoming.get('lessons'), list) else []
        new_s, new_m = ints(incoming.get('sessions')), ints(incoming.get('mins'))
        theme_v = incoming.get('theme') if incoming.get('theme') in ('dark', 'light') else None
        goal_v = incoming.get('daily_goal')
        store.clear()
        sess.clear()
        sess.update(new_s)
        mins.clear()
        mins.update(new_m)
        store['history'] = new_hist
        store['sessions'] = sess
        store['mins'] = mins
        store['tasks'] = new_tasks
        store['lessons'] = new_less
        if theme_v:
            store['theme'] = theme_v
        if isinstance(goal_v, int) and not isinstance(goal_v, bool):
            store['daily_goal'] = max(15, min(720, goal_v))
            goal_var.set(store['daily_goal'])
        save(store)

    # Backup and restore: user chooses the destination/source file.
    def backup_data():
        try:
            from tkinter import filedialog, messagebox
            name = filedialog.asksaveasfilename(
                parent=root, title='حفظ نسخة احتياطية',
                defaultextension='.json',
                filetypes=[('ملفات JSON', '*.json'), ('كل الملفات', '*.*')],
                initialfile='TanzilPC_backup.json')
            if not name:
                return
            with open(name, 'w', encoding='utf-8') as f:
                json.dump(store, f, ensure_ascii=False, indent=2)
            messagebox.showinfo(APP, 'تم حفظ النسخة الاحتياطية بنجاح.')
        except Exception as exc:
            try:
                from tkinter import messagebox
                messagebox.showerror(APP, 'تعذر حفظ النسخة: %s' % exc)
            except Exception:
                pass

    def restore_data():
        try:
            from tkinter import filedialog, messagebox
            name = filedialog.askopenfilename(
                parent=root, title='استعادة نسخة احتياطية',
                filetypes=[('ملفات JSON', '*.json'), ('كل الملفات', '*.*')])
            if not name:
                return
            if not messagebox.askyesno(APP, 'الاستعادة ستستبدل البيانات الحالية. هل تريد المتابعة؟'):
                return
            with open(name, 'r', encoding='utf-8') as f:
                incoming = json.load(f)
            if not isinstance(incoming, dict):
                raise ValueError('صيغة الملف غير صحيحة')
            apply_restore(incoming)
            refresh_hist()
            refresh_stats()
            upd_count()
            refresh_tasks()
            refresh_subjects()
            messagebox.showinfo(APP, 'تمت استعادة البيانات بنجاح.')
        except Exception as exc:
            try:
                from tkinter import messagebox
                messagebox.showerror(APP, 'تعذر استعادة النسخة: %s' % exc)
            except Exception:
                pass

    backup_row = tk.Frame(f_stat, bg=BG)
    backup_row.pack(pady=3)
    B(backup_row, 'نسخ احتياطي', backup_data, CARD, 9).pack(side='right', padx=4)
    B(backup_row, 'استعادة نسخة', restore_data, CARD, 9).pack(side='right', padx=4)

    upd_count()
    refresh_hist()
    refresh_stats()
    refresh_tasks()
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
        set_art(name)
        bg_lbl.lower()
        refresh_stats()
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
        try:
            store['daily_goal'] = max(15, min(720, int(goal_var.get())))
            save(store)
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
            elif a == '--size':
                size = tuple(int(v) for v in args[i + 1].split('x'))
        except Exception:
            pass
    try:
        main(t, None, th, size)
    except Exception:
        import traceback
        log_crash(traceback.format_exc())
        try:
            from tkinter import messagebox
            messagebox.showerror('تنزيل', 'حصل خطأ غير متوقع. اتسجل في ملف crash.log جوه مجلد TanzilPC.')
        except Exception:
            pass
        sys.exit(1)
