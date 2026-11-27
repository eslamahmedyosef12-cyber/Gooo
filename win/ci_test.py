import os, sys, time, json, tempfile
os.environ['APPDATA'] = tempfile.mkdtemp()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib
import tanzil_pc as T
fails = []
def check(name, cond):
    print(('PASS ' if cond else 'FAIL ') + name, flush=True)
    if not cond: fails.append(name)
def ev(root, keysym='a'):
    class E: pass
    e = E(); e.keysym = keysym; return e
def pump(root, secs):
    end = time.monotonic() + secs
    while time.monotonic() < end:
        root.update(); time.sleep(0.02)
def hook(ns):
    root = ns['root']; entry = ns['entry']; ts = ns['ts']; res = ns['res']
    try:
        # calc edge cases
        check('calc empty', T.calc('abc', '', 10) == (0.0, 0.0))
        check('calc perfect', abs(T.calc('a'*50, 'a'*50, 60)[0] - 10) < 1e-6)
        check('calc over-typed', T.calc('abc', 'abcdef', 30)[1] <= 100)
        # both languages produce text, no tashkeel
        for lang in ('ar', 'en'):
            ns['lang_var'].set(lang); ns['new_text']()
            check('passage ' + lang, len(ts['passage']) > 20)
        # full correct run in Arabic
        ns['lang_var'].set('ar'); ns['new_text']()
        ns['lim_var'].set(30)
        txt = ts['passage']
        entry.focus_force(); root.update()
        entry.insert(0, txt[:3]); ns['on_key'](ev(root)); pump(root, 0.5)
        check('timer started', ts['start'] is not None)
        entry.delete(0, 'end'); entry.insert(0, txt); ns['on_key'](ev(root)); pump(root, 0.6)
        check('finished on full text', ts['start'] is None and entry.cget('state') == 'disabled')
        check('result shown', 'كلمة' in res.cget('text') and '100%' in res.cget('text'))
        check('history saved', len(ns['store']['history']) == 1 and ns['hist'].size() == 1)
        # wrong text shows red
        ns['new_text']()
        entry.insert(0, 'zzz'); ns['on_key'](ev(root))
        check('error colour', entry.cget('bg') != '#f4fbf6')
        pump(root, 0.3)
        ns['stop_typing'](True)
        check('finish early works', entry.cget('state') == 'disabled')
        # finish with empty input, no crash
        ns['new_text'](); ns['stop_typing'](True)
        check('empty finish ok', True)
        # new text mid-run
        entry.insert(0, 'ab'); ns['on_key'](ev(root)); ns['new_text']()
        check('reset mid-run', ts['start'] is None and entry.get() == '')
        # time limit expiry
        ns['lim_var'].set(30); entry.insert(0, 'a'); ns['on_key'](ev(root)); ts['start'] -= 31; pump(root, 0.6)
        check('time limit ends', ts['start'] is None)
        # theme toggle
        ns['toggle_theme'](); root.update()
        check('light theme', ns['cur_theme']['n'] == 'light' and root.cget('bg') == T.THEMES['light']['bg'] and ns['store'].get('theme') == 'light')
        ns['show'](1); root.update(); ns['show'](0); root.update()
        check('tab colours light', ns['tb'][0].cget('bg') == T.ACC and ns['tb'][1].cget('bg') == T.THEMES['light']['card'])
        ns['toggle_theme'](); root.update()
        check('dark theme back', ns['cur_theme']['n'] == 'dark' and root.cget('bg') == T.THEMES['dark']['bg'])
        # tab switching + resize
        for i in (1, 0, 1, 0):
            ns['show'](i); root.update()
        root.geometry('800x700'); root.update(); root.geometry('600x440'); root.update()
        check('resize ok', True)
        # pomodoro
        ns['show'](1); root.update()
        ns['w_var'].set(1); ns['b_var'].set(1); ns['p_reset']()
        check('phase work 60s', ns['ps']['phase'] == 'work' and round(ns['ps']['left']) == 60)
        ns['p_start'](); pump(root, 0.5)
        check('running', ns['ps']['running'])
        ns['p_pause'](); l1 = ns['ps']['left']; pump(root, 0.5)
        check('paused holds', abs(ns['ps']['left'] - l1) < 0.01 and not ns['ps']['running'])
        ns['p_start'](); ns['ps']['end'] = time.monotonic() + 0.3; pump(root, 1.0)
        check('session counted + break', ns['ps']['phase'] == 'break' and ns['sess'].get(ns['today'], 0) == 1)
        ns['ps']['end'] = time.monotonic() + 0.3; pump(root, 1.0)
        check('back to work', ns['ps']['phase'] == 'work')
        ns['p_reset']()
        # garbage in spinbox
        ns['w_var'].set(1)
        try:
            ns['w_var'].set('x')
        except Exception:
            pass
        check('getm garbage', ns['getm'](ns['w_var'], 25) >= 1)
        # sound call does not crash
        T.beep_pattern('work_end'); T.beep_pattern('break_end'); pump(root, 1.5)
        check('beep ok', True)
        # persistence
        d = json.load(open(T.DATA, encoding='utf-8'))
        check('data persisted', len(d['history']) >= 1 and d['sessions'])
    except Exception as e:
        import traceback; traceback.print_exc(); fails.append('exception %r' % e)
    finally:
        root.destroy()
T.DATA = os.path.join(tempfile.mkdtemp(), 'data.json')
T.DIR = os.path.dirname(T.DATA)
T.main(0, hook)
# second launch: persisted data loads, corrupt file tolerated
check('data file exists', os.path.exists(T.DATA))
open(T.DATA, 'w').write('{{{bad')
def hook2(ns):
    check('corrupt data tolerated', ns['store']['history'] == [])
    ns['root'].destroy()
T.main(1, hook2)
print('FAILS', fails)
sys.exit(1 if fails else 0)
