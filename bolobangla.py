"""
BoloBangla AI - বলো বাংলা এআই
🤖◀)) BoloBangla AI
Version 1.2.0
"""

import os
import json,sys,time,wave,threading,tempfile,json,uuid,datetime,shutil,socket
import tkinter as tk
from tkinter import font as tkfont
import sounddevice as sd
import numpy as np
import requests,pyperclip,keyboard
from PIL import Image,ImageDraw
import pystray

def _load_api_key():
    """Load Groq API key: config file first, then environment variable"""
    try:
        cfg_path = os.path.join(os.path.expanduser("~"), ".bolobangla_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                k = cfg.get("groq_api_key", "").strip()
                if k:
                    return k
    except:
        pass
    return os.environ.get("GROQ_API_KEY", "")

GROQ_API_KEY = _load_api_key()
HOTKEY_BN = "ctrl+shift+b"
HOTKEY_EN = "ctrl+shift+e"
# বিকল্প hotkey — যদি মূলটা অন্য software (Avro) দখল করে রাখে
HOTKEY_BN_ALT = "alt+z"
HOTKEY_EN_ALT = "alt+x"
APP_NAME  = "বলো বাংলা এআই"
APP_EN    = "BoloBangla AI"
LOGO      = "🤖◀))"
VERSION   = "1.2.0"
SAMPLE_RATE = 16000
CHANNELS    = 1
DATA_DIR    = os.path.join(os.path.expanduser("~"),"BoloBanglaAI_Data")
CONFIG_FILE = os.path.join(os.path.expanduser("~"),".bolobangla_config.json")

PUNCT_BN = {
    "কমা":",","দাড়ি":"।","দাঁড়ি":"।","পূর্ণ বিরতি":"।","পূর্ণছেদ":"।",
    "সেমিকোলন":";","সেমি কোলন":";","সেমি:":";","সেমি: ":";","সেমি":";","অর্ধ বিরতি":";",
    "কোলন":":","বিন্দু":":",
    "প্রশ্নবোধক":"?","প্রশ্নবোধক চিহ্ন":"?","জিজ্ঞাসা চিহ্ন":"?","জিজ্ঞাসা":"?","প্রশ্ন চিহ্ন":"?",
    "বিস্ময়বোধক":"!","বিস্ময়বোধক চিহ্ন":"!","বিস্ময়সূচক চিহ্ন":"!",
    "বিস্ময় সূচক চিহ্ন":"!","বিস্ময় চিহ্ন":"!","বিস্ময়":"!","আশ্চর্য":"!","আশ্চর্যবোধক":"!",
    "নতুন লাইন":"\n","পরের লাইন":"\n","এন্টার":"\n",
    "নতুন প্যারা":"\n\n","নতুন অনুচ্ছেদ":"\n\n",
    "ড্যাশ":"—","হাইফেন":"-",
    "ব্র্যাকেট খোলো":"(","বন্ধনী খোলো":"(",
    "ব্র্যাকেট বন্ধ":")","বন্ধনী বন্ধ":")",
}
PUNCT_EN = {
    "comma":",","period":".","full stop":".","dot":".",
    "semicolon":";","semi colon":";","semi":";","semi:":";",
    "colon":":","clone":":",
    "question mark":"?","question":"?",
    "exclamation mark":"!","exclamation":"!","exclamation point":"!","explanation":"!",
    "Line ↵":"\n","next line":"\n","enter":"\n","new paragraph":"\n\n",
    "dash":"—","hyphen":"-",
    "open bracket":"(","close bracket":")",
    "open quote":'"',"close quote":'"',
}

is_recording  = False
_last_toggle_time = 0
_prev_hwnd = None
ai_polish_mode = False
_saved_clipboard = ""
raw_mode      = False
import threading as _threading
_record_lock  = _threading.Lock()
audio_frames  = []
mic_stream    = None
current_lang  = "bn"
indicator_win = None
toolbar_win   = None
app_running   = True


def _kill_stale_instances():
    """Kill any leftover BoloBangla python/pythonw processes (except self).
    এতে পুরনো আটকে থাকা instance বন্ধ হয়, hotkey সবসময় কাজ করে।"""
    try:
        import ctypes, subprocess
        my_pid = os.getpid()
        script_name = os.path.basename(os.path.abspath(__file__)).lower()
        # Find python/pythonw processes running bolobangla
        try:
            out = subprocess.check_output(
                ['wmic', 'process', 'where',
                 "name='python.exe' or name='pythonw.exe'",
                 'get', 'ProcessId,CommandLine', '/format:csv'],
                stderr=subprocess.DEVNULL, timeout=8
            ).decode('utf-8', 'ignore')
            for line in out.splitlines():
                if script_name in line.lower():
                    parts = line.strip().split(',')
                    pid = parts[-1].strip()
                    if pid.isdigit() and int(pid) != my_pid:
                        try:
                            subprocess.run(['taskkill', '/f', '/pid', pid],
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL, timeout=5)
                            print(f"[\u2713] পুরনো instance বন্ধ করা হলো (PID {pid})")
                        except:
                            pass
        except Exception:
            pass
        time.sleep(0.5)
    except Exception as e:
        print(f"[!] Stale cleanup: {e}")

def check_single_instance(_retry=True):
    try:
        s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1",47291))
        s.listen(1)
        return s
    except OSError:
        # পুরনো instance আটকে আছে — সেটা বন্ধ করে আবার চেষ্টা করি
        if _retry:
            print("[!] পুরনো BoloBangla AI পরিষ্কার করা হচ্ছে...")
            _kill_stale_instances()
            time.sleep(1.0)
            return check_single_instance(_retry=False)
        print("[!] BoloBangla AI আগে থেকেই চলছে!")
        sys.exit(0)

def load_config():
    try:
        with open(CONFIG_FILE,"r",encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    try:
        with open(CONFIG_FILE,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False)
    except:
        pass

def is_first_run():
    return not load_config().get("welcomed",False)

def mark_welcomed(contribute=False):
    config=load_config()
    config["welcomed"]=True
    config["contribute"]=contribute
    config["user_id"]=config.get("user_id",str(uuid.uuid4())[:8])
    save_config(config)

def should_contribute():
    return load_config().get("contribute",False)

def get_user_id():
    return load_config().get("user_id","anonymous")

def log_voice_data(audio_path,transcription):
    if not should_contribute():
        return
    try:
        os.makedirs(DATA_DIR,exist_ok=True)
        entry={"timestamp":datetime.datetime.now().isoformat(),"user_id":get_user_id(),"text":transcription}
        with open(os.path.join(DATA_DIR,"voice_log.jsonl"),"a",encoding="utf-8") as f:
            f.write(json.dumps(entry,ensure_ascii=False)+"\n")
        dest=os.path.join(DATA_DIR,f"{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        shutil.copy2(audio_path,dest)
    except:
        pass


# ─── WELCOME SCREEN ───────────────────────────
class WelcomeScreen:
    def __init__(self,on_done):
        self.on_done=on_done
        self.step=0
        self.contribute_var=None
        self.root=tk.Tk()
        self.root.title(f"{APP_EN} — স্বাগতম!")
        self.root.geometry("500x660")
        self.root.resizable(False,False)
        self.root.configure(bg="#0A3D1F")
        self.root.attributes("-topmost",True)
        sw=self.root.winfo_screenwidth()
        sh=self.root.winfo_screenheight()
        self.root.geometry(f"500x660+{(sw-500)//2}+{(sh-660)//2}")
        self.steps=[
            {"icon":"🤖◀))","title":"স্বাগতম!","color":"#00E676",
             "desc":f"{APP_NAME}\nযেকোনো অ্যাপে বাংলা বা English বলুন\nলেখা automatically টাইপ হবে!"},
            {"icon":"⌨️","title":"হটকি শিখুন","color":"#F42A41",
             "desc":"বাংলা লিখতে: Ctrl + Shift + B\nEnglish লিখতে: Ctrl + Shift + E\nআবার চাপুন = রেকর্ড বন্ধ"},
            {"icon":"🗣️","title":"বলুন এবং লিখুন","color":"#00C853",
             "desc":"🟢 Ctrl+Shift+B চেপে বাংলায় বলুন\n🔵 Ctrl+Shift+E চেপে English বলুন\nলাল বাতি জ্বললে রেকর্ড চলছে"},
            {"icon":"💡","title":"Punctuation Commands","color":"#F42A41",
             "desc":"বাংলা: কমা→, | দাড়ি→। | সেমি→; | কোলন→:\nবাংলা: জিজ্ঞাসা→? | বিস্ময়→! | ড্যাশ→—\nEnglish: comma→, | period→. | semi→;\nnew line / নতুন লাইন → ↵"},
            {"icon":"🎙️","title":"Mic টিপস","color":"#00C853",
             "desc":"ভালো accuracy-র জন্য ভালো ফলাফল পেতে headphone mic ব্যবহার করুন\nBuilt-in mic-এ ৪-৬ ইঞ্চি কাছে বলুন\nBackground noise কমালে লেখা আরো সঠিক হবে"},
            {"icon":"🇧🇩","title":"বাংলা AI উন্নয়নে সাহায্য করুন","color":"#F42A41",
             "desc":"আপনার voice anonymously contribute করে\nবাংলাদেশের নিজের AI তৈরিতে সাহায্য করুন\nকোনো personal তথ্য collect হবে না",
             "has_toggle":True},
        ]
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW",self._finish)

    def _build_ui(self):
        hdr=tk.Frame(self.root,bg="#0D5C2E",pady=14)
        hdr.pack(fill="x")
        tk.Label(hdr,text="🤖◀))",font=("Segoe UI Emoji",28),bg="#0D5C2E").pack()
        tk.Label(hdr,text=APP_EN,font=("Segoe UI",20,"bold"),bg="#0D5C2E",fg="#F42A41").pack()
        tk.Label(hdr,text=APP_NAME,font=("Segoe UI",10),bg="#0D5C2E",fg="#B9F6CA").pack(pady=(2,0))
        self.content=tk.Frame(self.root,bg="#0A3D1F")
        self.content.pack(fill="both",expand=True,padx=30,pady=12)
        self._show_step(0)
        dots_row=tk.Frame(self.root,bg="#0A3D1F")
        dots_row.pack()
        self.dots=[]
        for i in range(len(self.steps)):
            d=tk.Label(dots_row,text="●",font=("Segoe UI",8),bg="#0A3D1F",fg="#0F6B35")
            d.pack(side="left",padx=3)
            self.dots.append(d)
        nav=tk.Frame(self.root,bg="#0A3D1F",pady=10)
        nav.pack(fill="x",padx=30)
        self.prev_btn=tk.Button(nav,text="← আগে",font=("Segoe UI",10),bg="#0F6B35",fg="#B9F6CA",relief="flat",padx=15,pady=8,cursor="hand2",command=self._prev)
        self.prev_btn.pack(side="left")
        self.next_btn=tk.Button(nav,text="পরে →",font=("Segoe UI",11,"bold"),bg="#F42A41",fg="white",relief="flat",padx=20,pady=8,cursor="hand2",command=self._next)
        self.next_btn.pack(side="right")
        tk.Label(self.root,text=f"{APP_EN} v{VERSION} — Made in Bangladesh 🇧🇩",font=("Segoe UI",8),bg="#0A3D1F",fg="#3A8C6E").pack(pady=(0,8))
        self._update_dots()

    def _show_step(self,idx):
        for w in self.content.winfo_children():
            w.destroy()
        s=self.steps[idx]
        tk.Label(self.content,text=s["icon"],font=("Segoe UI Emoji",40),bg="#0A3D1F").pack(pady=(6,4))
        tk.Label(self.content,text=s["title"],font=("Segoe UI",15,"bold"),bg="#0A3D1F",fg=s["color"]).pack()
        box=tk.Frame(self.content,bg="#0D5C2E")
        box.pack(fill="x",pady=10,ipady=10)
        tk.Label(box,text=s["desc"],font=("Segoe UI",11),bg="#0D5C2E",fg="#E8F5E9",justify="center",wraplength=380).pack(padx=20,pady=6)
        if s.get("has_toggle"):
            self.contribute_var=tk.BooleanVar(value=True)
            trow=tk.Frame(self.content,bg="#0A3D1F")
            trow.pack(pady=8)
            tk.Checkbutton(trow,text="হ্যাঁ, আমি বাংলা AI উন্নয়নে contribute করতে চাই",variable=self.contribute_var,font=("Segoe UI",10),bg="#0A3D1F",fg="#F42A41",selectcolor="#0D5C2E",activebackground="#0A3D1F",cursor="hand2").pack()
            tk.Label(trow,text="(শুধু voice + transcription, কোনো নাম/পরিচয় নয়)",font=("Segoe UI",8),bg="#0A3D1F",fg="#3A8C6E").pack()

    def _update_dots(self):
        for i,d in enumerate(self.dots):
            d.config(fg="#F42A41" if i==self.step else "#0F6B35")
        self.prev_btn.config(state="normal" if self.step>0 else "disabled",fg="#B9F6CA" if self.step>0 else "#3A8C6E")
        self.next_btn.config(text="শুরু করুন ✓" if self.step==len(self.steps)-1 else "পরে →",
                              bg="#00A550" if self.step==len(self.steps)-1 else "#F42A41")

    def _prev(self):
        if self.step>0:
            self.step-=1
            self._show_step(self.step)
            self._update_dots()

    def _next(self):
        if self.step<len(self.steps)-1:
            self.step+=1
            self._show_step(self.step)
            self._update_dots()
        else:
            self._finish()

    def _finish(self):
        contribute=self.contribute_var.get() if self.contribute_var else False
        mark_welcomed(contribute=contribute)
        self.root.destroy()
        self.on_done()

    def run(self):
        self.root.mainloop()


# ─── FLOATING TOOLBAR ─────────────────────────
class ToolbarWindow:
    def __init__(self):
        self.expanded = False
        self.font_size = 8
        self.root = tk.Toplevel()
        self.root.title(APP_EN)
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.configure(bg="#004D38")
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        sw = self.root.winfo_screenwidth()
        self.sw = sw
        # Start compact - centered
        self.compact_w = min(sw - 30, 750)  # fit all buttons incl Facebook
        self.compact_h = 36  # slightly shorter
        self.expanded_w = min(sw - 20, 1000)
        self.expanded_h = 175
        x = (sw - self.compact_w) // 2
        self.root.geometry(f"{self.compact_w}x{self.compact_h}+{x}+5")

        self._build()
        self._drag_init()

    def _build(self):
        # ── Compact bar (always visible) ──
        self.compact_bar = tk.Frame(self.root, bg="#004D38", cursor="hand2")
        self.compact_bar.pack(fill="x")
        self.compact_bar.bind("<ButtonPress-1>", self._drag_start)
        self.compact_bar.bind("<B1-Motion>", self._drag_motion)
        self.compact_bar.bind("<Double-Button-1>", self._toggle_mini)
        self.compact_bar.bind("<Double-Button-1>", lambda e: self.toggle_expand())

        # Logo
        logo_cv = tk.Canvas(self.compact_bar, width=30, height=30,
                             bg="#004D38", highlightthickness=0)
        logo_cv.pack(side="left", padx=(6,4), pady=3)
        logo_cv.create_oval(1,1,29,29, fill="#F42A41", outline="")
        logo_cv.create_text(15,10, text="বলো", font=("Segoe UI",6,"bold"), fill="white")
        logo_cv.create_text(15,22, text="বাংলা", font=("Segoe UI",5,"bold"), fill="white")

        tk.Label(self.compact_bar, text=APP_EN,
                 font=("Segoe UI",10,"bold"), bg="#004D38", fg="#F42A41",
                 cursor="hand2").pack(side="left", padx=(0,6))

        # Expand arrow
        self.arrow_lbl = tk.Label(self.compact_bar, text="▼",
                 font=("Segoe UI",8), bg="#004D38", fg="#00C853",
                 cursor="hand2")
        self.arrow_lbl.pack(side="left")
        self.arrow_lbl.bind("<Button-1>", lambda e: self.toggle_expand())

        # Status (compact)
        self.compact_status = tk.Label(self.compact_bar, text="● প্রস্তুত",
                 font=("Segoe UI",8), bg="#004D38", fg="#00C853")
        self.compact_status.pack(side="left", padx=8)

        self.compact_net = tk.Label(self.compact_bar, text="🌐 Online",
                 font=("Segoe UI",8), bg="#004D38", fg="#00C853")
        self.compact_net.pack(side="left", padx=4)

        # Paste button in compact bar
        self.paste_btn = tk.Button(self.compact_bar, text="📌 Paste",
                  font=("Segoe UI",8,"bold"), bg="#F42A41", fg="white",
                  relief="flat", padx=6, pady=1, cursor="hand2",
                  command=self._do_paste)
        self.paste_btn.pack(side="left", padx=2)

        # Quick record buttons in compact bar
        self.compact_bn_btn = tk.Button(self.compact_bar, text="🎙বাংলা",
                  font=("Segoe UI",8,"bold"), bg="#0D5C2E", fg="#B9F6CA",
                  relief="flat", padx=6, pady=1, cursor="hand2",
                  command=lambda: toggle_recording("bn"))
        self.compact_bn_btn.pack(side="left", padx=2)

        self.compact_en_btn = tk.Button(self.compact_bar, text="🎙EN",
                  font=("Segoe UI",8,"bold"), bg="#0D5C2E", fg="#7EB89A",
                  relief="flat", padx=6, pady=1, cursor="hand2",
                  command=lambda: toggle_recording("en"))
        self.compact_en_btn.pack(side="left", padx=2)

        # Virtual Keyboard button in compact bar
        # KB button - icon only with tooltip
        kb_btn = tk.Button(self.compact_bar, text="KB",
                  font=("Segoe UI",8,"bold"), bg="#1565C0", fg="white",
                  relief="flat", padx=6, pady=2, cursor="hand2",
                  command=self._open_keyboard)
        kb_btn.pack(side="left", padx=2)
        self.root.after(200, lambda: self._add_compact_tooltip(kb_btn, "⌨ Virtual Keyboard — বাংলা ও English"))
        # AI Editor - icon only with tooltip
        ed_btn = tk.Button(self.compact_bar, text="AI",
                  font=("Segoe UI",8,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", padx=6, pady=2, cursor="hand2",
                  command=self._open_editor)
        ed_btn.pack(side="left", padx=2)
        self.root.after(200, lambda: self._add_compact_tooltip(ed_btn, "✏ AI Text Editor — লেখা সাজান"))
        # Last Copy - icon only with tooltip
        self.restore_btn = tk.Button(self.compact_bar, text="📋",
                               font=("Segoe UI Emoji",9),
                               bg="#004D38", fg="#5A9E82",
                               relief="flat", padx=6, pady=2,
                               cursor="hand2",
                               command=self._restore_clipboard)
        self.restore_btn.pack(side="left", padx=2)
        self.root.after(200, lambda: self._add_compact_tooltip(self.restore_btn, "📋 Last Copy Restore"))

        # API Key setup button
        key_btn = tk.Button(self.compact_bar, text="🔑",
                  font=("Segoe UI Emoji",9), bg="#004D38", fg="#FFD700",
                  relief="flat", padx=5, pady=2, cursor="hand2",
                  command=self._open_key_setup)
        key_btn.pack(side="left", padx=2)
        self.root.after(200, lambda: self._add_compact_tooltip(key_btn, "🔑 AI Key সেটআপ"))

        # Facebook feedback button
        fb_btn = tk.Button(self.compact_bar, text="f",
                  font=("Georgia",10,"bold"), bg="#1877F2", fg="white",
                  relief="flat", padx=7, pady=2, cursor="hand2",
                  command=self._open_facebook)
        fb_btn.pack(side="left", padx=2)
        self.root.after(200, lambda: self._add_compact_tooltip(fb_btn, "💬 মতামত দিন (Facebook)"))

        # Manual (Help) button
        manual_btn = tk.Button(self.compact_bar, text="?",
                  font=("Segoe UI",9,"bold"), bg="#004D38", fg="#FFD700",
                  relief="flat", padx=6, pady=2, cursor="hand2",
                  command=self._open_manual)
        manual_btn.pack(side="left", padx=2)
        self.root.after(200, lambda: self._add_compact_tooltip(manual_btn, "📖 ব্যবহার নির্দেশিকা (Manual)"))

        # Close button
        tk.Button(self.compact_bar, text="✕", font=("Segoe UI",10,"bold"),
                  bg="#004D38", fg="#F42A41", relief="flat",
                  cursor="hand2", command=self.hide, bd=0, padx=4).pack(side="left", padx=(2,10))

        # ── Expanded panel (hidden by default) ──
        self.panel = tk.Frame(self.root, bg="#006A4E")
        # Don't pack yet - hidden

        self._build_panel()

    def _build_panel(self):
        body = tk.Frame(self.panel, bg="#006A4E", pady=5)
        body.pack(fill="x", padx=8)

        # Row 1: Language + Status + Online
        row1 = tk.Frame(body, bg="#006A4E")
        row1.pack(fill="x", pady=(0,3))

        self.btn_bn = tk.Button(row1, text="🎙 বাংলা",
                               font=("Segoe UI",9,"bold"),
                               bg="#0D5C2E", fg="#B9F6CA", relief="flat",
                               padx=10, pady=5, cursor="hand2",
                               command=lambda: toggle_recording("bn"))
        self.btn_bn.pack(side="left", padx=(0,5))

        self.btn_en = tk.Button(row1, text="🎙 English",
                               font=("Segoe UI",9,"bold"),
                               bg="#0D5C2E", fg="#7EB89A", relief="flat",
                               padx=10, pady=5, cursor="hand2",
                               command=lambda: toggle_recording("en"))
        self.btn_en.pack(side="left", padx=(0,10))

        self.status_lbl = tk.Label(row1, bg="#006A4E", text="")

        self.net_lbl = tk.Label(row1, bg="#006A4E", text="")
        self._check_internet()

        # Row 2: Normal/Raw + Punctuation
        row2 = tk.Frame(body, bg="#006A4E")
        row2.pack(fill="x", pady=(0,3))

        # Normal button with sublabel
        normal_frame = tk.Frame(row2, bg="#006A4E")
        normal_frame.pack(side="left", padx=(0,4))
        # AI Polish button
        polish_frame = tk.Frame(row2, bg="#006A4E")
        polish_frame.pack(side="left", padx=(0,4))
        self.ai_polish_btn = tk.Button(polish_frame, text="✨ AI Polish",
                               font=("Segoe UI",8,"bold"),
                               bg="#044A33", fg="#a855f7", relief="flat",
                               padx=7, pady=2, cursor="hand2",
                               command=self._toggle_ai_polish)
        self.ai_polish_btn.pack()
        tk.Label(polish_frame, text="AI সংশোধন",
                 font=("Segoe UI",7,"bold"), bg="#006A4E", fg="#c084fc").pack()

        self.raw_normal_btn = tk.Button(normal_frame, text="🟢 Normal",
                               font=("Segoe UI",8,"bold"),
                               bg="#0D5C2E", fg="#00C853", relief="flat",
                               padx=7, pady=2, cursor="hand2",
                               command=self._set_normal)
        self.raw_normal_btn.pack()
        tk.Label(normal_frame, text="with punctuation",
                 font=("Segoe UI",7,"bold"), bg="#006A4E", fg="#00E676").pack()

        # Raw button with sublabel
        raw_frame = tk.Frame(row2, bg="#006A4E")
        raw_frame.pack(side="left", padx=(0,8))
        self.raw_raw_btn = tk.Button(raw_frame, text="🟡 Raw",
                               font=("Segoe UI",8),
                               bg="#044A33", fg="#5A9E82", relief="flat",
                               padx=7, pady=2, cursor="hand2",
                               command=self._set_raw)
        self.raw_raw_btn.pack()
        tk.Label(raw_frame, text="without punctuation",
                 font=("Segoe UI",7,"bold"), bg="#006A4E", fg="#f9a825").pack()

        tk.Label(row2, text="|", font=("Segoe UI",10),
                 bg="#006A4E", fg="#3A8C6E").pack(side="left", padx=4)

        self.punct_frame = tk.Frame(row2, bg="#006A4E")
        self.punct_frame.pack(side="left", fill="x")
        self._show_punct("bn")

        # Tip bar
        tip = tk.Frame(self.panel, bg="#003D2A", pady=3)
        tip.pack(fill="x")
        tk.Label(tip, text="🎙  ভালো ফলাফল পেতে headphone mic ব্যবহার করুন  |  Internet connection প্রয়োজন",
                 font=("Segoe UI",7), bg="#003D2A", fg="#5A9E82").pack()

    def toggle_expand(self):
        self.expanded = not self.expanded
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        if self.expanded:
            self.panel.pack(fill="x")
            w = min(self.sw-20, 1000)
            self.root.geometry(f"{w}x175+{(self.sw-w)//2}+5")
            self.arrow_lbl.config(text="▲")
        else:
            self.panel.pack_forget()
            self.root.geometry(f"{self.compact_w}x{self.compact_h}+{(self.sw-self.compact_w)//2}+5")
            self.arrow_lbl.config(text="▼")

    def _add_tooltip(self, widget, text):
        def show(e):
            tip = tk.Toplevel()
            tip.wm_overrideredirect(True)
            tip.wm_geometry(f"+{e.x_root+10}+{e.y_root+20}")
            tk.Label(tip, text=text, font=("Segoe UI",8),
                     bg="#333", fg="white", padx=6, pady=3,
                     justify="left").pack()
            widget._tip = tip
        def hide(e):
            if hasattr(widget, "_tip"):
                widget._tip.destroy()
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _show_punct(self, lang):
        for w in self.punct_frame.winfo_children():
            w.destroy()

        def make_btn(parent, lbl, c, sz=8):
            b = tk.Button(parent, text=lbl,
                     font=("Segoe UI", sz, "bold"),
                     bg="#0D5C2E", fg="#B9F6CA",
                     relief="flat", padx=4, pady=2,
                     cursor="hand2")
            def on_enter(e):
                global _prev_hwnd
                import ctypes
                hw = ctypes.windll.user32.GetForegroundWindow()
                if hw != self.root.winfo_id():
                    _prev_hwnd = hw
            def on_release(e, char=c):
                self.root.after(50, lambda: insert_text(char))
            b.bind("<Enter>", on_enter)
            b.bind("<ButtonRelease-1>", on_release)
            return b

        if lang == "bn":
            sym = [(",",","),("।","।"),(";",";"),(":",":")
                   ,("?","?"),("!","!"),("--","--"),("⏎","\n")]
            words = [("কমা",","),("দাড়ি","।"),("সেমি",";"),("কোলন",":")
                     ,("প্রশ্ন","?"),("বিস্ময়","!"),("ড্যাশ","--")]
            digits = [("১","১"),("২","২"),("৩","৩"),("৪","৪"),("৫","৫")
                      ,("৬","৬"),("৭","৭"),("৮","৮"),("৯","৯"),("০","০")]
        else:
            sym = [(",",","),(".","."),(";"," ;"),(":",":")
                   ,("?","?"),("!","!"),("--","--"),("⏎","\n")]
            words = [("comma",","),("period","."),("semi",";"),("colon",":")
                     ,("quest","?"),("exclam","!"),("dash","--")]
            digits = [("1","1"),("2","2"),("3","3"),("4","4"),("5","5")
                      ,("6","6"),("7","7"),("8","8"),("9","9"),("0","0")]

        # Row 1: symbols + digits
        r1 = tk.Frame(self.punct_frame, bg="#006A4E")
        r1.pack(fill="x", pady=(0,2))
        for lbl,ch in sym:
            make_btn(r1, lbl, ch, 10).pack(side="left", padx=2)
        tk.Label(r1, text="|", bg="#006A4E", fg="#3A8C6E",
                 font=("Segoe UI",10)).pack(side="left", padx=3)
        for lbl,ch in digits:
            make_btn(r1, lbl, ch, 10).pack(side="left", padx=2)

        # Row 2: word labels
        r2 = tk.Frame(self.punct_frame, bg="#006A4E")
        r2.pack(fill="x")
        for lbl,ch in words:
            make_btn(r2, lbl, ch, 7).pack(side="left", padx=2)
    def _set_mode(self, lang):
        if lang == "bn":
            self.btn_bn.config(bg="#F42A41", fg="white")
            self.btn_en.config(bg="#0D5C2E", fg="#7EB89A")
        else:
            self.btn_bn.config(bg="#0D5C2E", fg="#7EB89A")
            self.btn_en.config(bg="#1565C0", fg="white")
        self._show_punct(lang)

    def _toggle_mini(self, event=None):
        """Double-click to toggle mini mode (logo + record only)"""
        if not hasattr(self, '_mini_mode'):
            self._mini_mode = False
        self._mini_mode = not self._mini_mode
        sw = self.root.winfo_screenwidth()
        if self._mini_mode:
            # Mini mode - very compact
            self.root.geometry(f"220x{self.compact_h}")
            for child in self.compact_bar.winfo_children():
                try:
                    txt = str(child.cget('text'))
                    # Hide everything except logo, status, record buttons
                    if txt in ['KB','AI','📌 Paste','📋','?','🔑'] or 'Last' in txt or 'Copy' in txt:
                        child.pack_forget()
                except:
                    pass
        else:
            # Restore full
            w = min(sw-40, 760)
            x = (sw-w)//2
            self.root.geometry(f"{w}x{self.compact_h}+{x}+0")
            # Rebuild - restart toolbar
            self.root.after(100, lambda: self.root.destroy())

    def _show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0, bg="#004D38", fg="white",
                       font=("Segoe UI",9), relief="flat",
                       activebackground="#006A4E", activeforeground="white")
        menu.add_command(label="↔ Horizontal (স্বাভাবিক)", command=self._set_horizontal)
        menu.add_command(label="↕ Vertical (খাড়া)", command=self._set_vertical)
        menu.add_separator()
        menu.add_command(label="⬆ উপরে রাখুন", command=lambda: self._snap_position("top"))
        menu.add_command(label="⬇ নিচে রাখুন", command=lambda: self._snap_position("bottom"))
        menu.add_command(label="◀ বামে রাখুন", command=lambda: self._snap_position("left"))
        menu.add_command(label="▶ ডানে রাখুন", command=lambda: self._snap_position("right"))
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _set_horizontal(self):
        self._vertical_mode = False
        sw = self.root.winfo_screenwidth()
        w = min(sw-40, 760)
        x = (sw - w) // 2
        self.root.geometry(f"{w}x{self.compact_h}+{x}+0")
        for child in self.compact_bar.winfo_children():
            try: child.pack_configure(side="left", padx=2, pady=0)
            except: pass

    def _set_vertical(self):
        self._vertical_mode = True
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        # Show only key buttons vertically
        self.root.geometry(f"50x300+{sw-55}+{(sh-300)//2}")
        self.compact_bar.config(width=50)
        # Repack all children vertically
        children = self.compact_bar.winfo_children()
        for child in children:
            try:
                child.pack_forget()
            except:
                pass
        for child in children:
            try:
                child.pack(side="top", pady=1, padx=2, fill="x")
            except:
                pass

    def _snap_position(self, pos):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        positions = {
            "top": (f"+{(sw-w)//2}+0"),
            "bottom": (f"+{(sw-w)//2}+{sh-h-5}"),
            "left": (f"+0+{(sh-h)//2}"),
            "right": (f"+{sw-w-5}+{(sh-h)//2}"),
        }
        self.root.geometry(positions[pos])

    def _toggle_orientation(self):
        """Toggle between horizontal and vertical mode"""
        if not hasattr(self, '_vertical_mode'):
            self._vertical_mode = False
        self._vertical_mode = not self._vertical_mode
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        if self._vertical_mode:
            # Vertical mode - tall and narrow
            self.root.geometry(f"42x{min(sh-40, 320)}+{sw-50}+20")
            # Repack compact_bar vertically
            for w in self.compact_bar.winfo_children():
                w.pack_configure(side="top", padx=0, pady=1)
            self.compact_bar.config(width=42, height=320)
        else:
            # Horizontal mode - restore
            w = min(sw-40, 760)
            x = (sw - w) // 2
            self.root.geometry(f"{w}x{self.compact_h}+{x}+0")
            for child in self.compact_bar.winfo_children():
                child.pack_configure(side="left", padx=2, pady=0)

    def _drag_start(self, event):
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _drag_motion(self, event):
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        # Keep within screen bounds
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, min(x, sw - self.root.winfo_width()))
        y = max(0, min(y, sh - self.root.winfo_height()))
        self.root.geometry(f"+{x}+{y}")

    def _add_compact_tooltip(self, widget, text):
        def show(e):
            tip = tk.Toplevel()
            tip.wm_overrideredirect(True)
            tip.attributes("-topmost", True)
            tip.wm_geometry(f"+{e.x_root}+{self.root.winfo_y()+self.compact_h+2}")
            tk.Label(tip, text=text, font=("Segoe UI",9),
                     bg="#FFFFE0", fg="#000000",
                     padx=6, pady=3, relief="solid", bd=1).pack()
            widget._tip = tip
            tip.lift()
        def hide(e):
            if hasattr(widget,"_tip"):
                try: widget._tip.destroy()
                except: pass
        widget.bind("<Enter>", show)
        widget.bind("<Leave>", hide)

    def _do_paste(self):
        """Paste from toolbar button - hide toolbar first"""
        # Withdraw toolbar so previous window gets focus
        self.root.withdraw()
        time.sleep(0.15)
        keyboard.press_and_release("ctrl+v")
        time.sleep(0.2)
        self.root.deiconify()

    def _open_key_setup(self):
        """Open API key setup window"""
        APIKeySetupWindow()

    def _open_facebook(self):
        """Open Facebook page for feedback/rating"""
        import webbrowser
        webbrowser.open("https://www.facebook.com/share/18vnkfcq68/")

    def _open_facebook(self):
        """Open Facebook page for feedback and ratings"""
        import webbrowser
        webbrowser.open("https://www.facebook.com/share/18vnkfcq68/")

    def _open_manual(self):
        """Open the PDF user manual"""
        import os, subprocess, sys
        # Look for manual in same folder as the script
        candidates = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "BoloBangla_AI_Manual.pdf"),
            os.path.join(os.getcwd(), "BoloBangla_AI_Manual.pdf"),
        ]
        manual_path = None
        for c in candidates:
            if os.path.exists(c):
                manual_path = c
                break
        if manual_path:
            try:
                os.startfile(manual_path)
            except Exception as e:
                print(f"[MANUAL] Error: {e}")
        else:
            # Show message if not found
            import tkinter.messagebox as mb
            mb.showinfo("Manual", "ম্যানুয়াল ফাইল (BoloBangla_AI_Manual.pdf) খুঁজে পাওয়া যায়নি।\nএটি সফটওয়্যারের ফোল্ডারে রাখুন।")

    def _open_keyboard(self):
        lang = "bn" if self.btn_bn.cget("bg") == "#F42A41" else "en"
        kb = VirtualKeyboardWindow(lang=lang)
        kb.root.focus_force()

    def _open_editor(self):
        global _prev_hwnd
        import ctypes
        _prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
        lang = "bn" if self.btn_bn.cget("bg") == "#F42A41" else "en"
        editor = AIEditorWindow(lang=lang)
        editor.root.focus_force()

    def _restore_clipboard(self):
        try:
            if _saved_clipboard:
                pyperclip.copy(_saved_clipboard)
                self.restore_btn.config(text="✓ Restored!", fg="#00C853")
                self.root.after(1500, lambda: self.restore_btn.config(
                    text="📋 Last Copy", fg="#5A9E82"))
        except:
            pass

    def _toggle_ai_polish(self):
        global ai_polish_mode
        ai_polish_mode = not ai_polish_mode
        if ai_polish_mode:
            self.ai_polish_btn.config(bg="#7c3aed", fg="white")
            self.compact_status.config(text="✨ AI Polish", fg="#c084fc")
        else:
            self.ai_polish_btn.config(bg="#044A33", fg="#a855f7")
            self.compact_status.config(text="● প্রস্তুত", fg="#00C853")

    def _set_normal(self):
        global raw_mode
        raw_mode = False
        self.raw_normal_btn.config(bg="#0D5C2E", fg="#00C853")
        self.raw_raw_btn.config(bg="#044A33", fg="#5A9E82")
        self.status_lbl.config(text="● প্রস্তুত", fg="#00C853")
        self.compact_status.config(text="● প্রস্তুত", fg="#00C853")

    def _set_raw(self):
        global raw_mode
        raw_mode = True
        self.raw_normal_btn.config(bg="#044A33", fg="#5A9E82")
        self.raw_raw_btn.config(bg="#f9a825", fg="#000000")
        self.status_lbl.config(text="🟡 Raw Mode", fg="#f9a825")
        self.compact_status.config(text="🟡 Raw", fg="#f9a825")

    def _toggle_raw(self):
        if raw_mode:
            self._set_normal()
        else:
            self._set_raw()

    def _check_internet(self):
        def check():
            import socket as s
            try:
                s.setdefaulttimeout(2)
                s.socket(s.AF_INET, s.SOCK_STREAM).connect(("8.8.8.8",53))
                self.root.after(0, lambda: self.net_lbl.config(text=""))
                self.root.after(0, lambda: self.compact_net.config(text="🌐 Online", fg="#00C853"))
            except:
                self.root.after(0, lambda: self.net_lbl.config(text=""))
                self.root.after(0, lambda: self.compact_net.config(text="❌ Offline", fg="#F42A41"))
            self.root.after(10000, self._check_internet)
        import threading
        threading.Thread(target=check, daemon=True).start()

    def _translate(self, src_lang, tgt_lang):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="⚠️ কোনো লেখা নেই!", fg="#F42A41")
            return
        if not GROQ_API_KEY:
            self.status.config(text="🔑 AI Key সেটআপ করুন...", fg="#f9a825")
            APIKeySetupWindow()
            return
        if src_lang == "bn":
            self.status.config(text="⟳ বাংলা → English অনুবাদ হচ্ছে...", fg="#f9a825")
        else:
            self.status.config(text="⟳ English → বাংলা অনুবাদ হচ্ছে...", fg="#f9a825")
        self.root.update()
        def do_translate():
            try:
                if src_lang == "bn":
                    prompt = f"""Translate the following Bengali text to English. Return only the translated text, nothing else.

Bengali: {text}"""
                else:
                    prompt = f"""নিচের English লেখাটি বাংলায় অনুবাদ করো। শুধু অনুবাদটি দাও, অন্য কিছু লিখবে না।

English: {text}"""
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.2
                }
                r = requests.post(url, headers=headers, json=data, timeout=15)
                if r.status_code == 200:
                    result = r.json()["choices"][0]["message"]["content"].strip()
                    self.root.after(0, lambda: self._show_result(result))
                    if src_lang == "bn":
                        self.root.after(0, lambda: self.status.config(text="✓ বাংলা → English সম্পন্ন!", fg="#00C853"))
                    else:
                        self.root.after(0, lambda: self.status.config(text="✓ English → বাংলা সম্পন্ন!", fg="#00C853"))
                else:
                    self.root.after(0, lambda: self.status.config(text="VPN বন্ধ করে আবার চেষ্টা করুন!" if r.status_code==403 else f"Error: {r.status_code}", fg="#F42A41"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(text=f"⚠️ {str(e)[:40]}", fg="#F42A41"))
        import threading
        threading.Thread(target=do_translate, daemon=True).start()

    def _bn_to_en(self):
        self._translate("bn", "en")

    def _en_to_bn(self):
        self._translate("en", "bn")

    def _paste_to_window(self):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="কোনো লেখা নেই!", fg="#F42A41")
            return
        # Copy to clipboard
        pyperclip.copy(text)
        self.status.config(text="Clipboard-এ copy হয়েছে! Ctrl+V চাপুন", fg="#00C853")
        # Minimize and try to paste
        self.root.iconify()
        import threading
        def try_paste():
            import ctypes, time
            time.sleep(0.4)
            try:
                if _prev_hwnd:
                    ctypes.windll.user32.SetForegroundWindow(_prev_hwnd)
                    time.sleep(0.3)
            except:
                pass
            import keyboard as kb
            kb.press_and_release("ctrl+v")
            time.sleep(0.5)
            self.root.after(0, self.root.deiconify)
        threading.Thread(target=try_paste, daemon=True).start()
    def _zoom_in(self):
        if self.font_size < 14:
            self.font_size += 1
            lang = "bn" if self.btn_bn.cget("bg") == "#F42A41" else "en"
            self._show_punct(lang)

    def _zoom_out(self):
        if self.font_size > 6:
            self.font_size -= 1
            lang = "bn" if self.btn_bn.cget("bg") == "#F42A41" else "en"
            self._show_punct(lang)

    def update_status(self, text, color="#00C853"):
        self.root.after(0, lambda: self.status_lbl.config(text=text, fg=color))
        self.root.after(0, lambda: self.compact_status.config(text=text, fg=color))

    def update_mode(self, lang):
        self.root.after(0, lambda: self._set_mode(lang))

    def show(self):
        self.root.deiconify()

    def hide(self):
        self.root.withdraw()

    def _drag_init(self):
        self._drag_x = 0
        self._drag_y = 0

    def _drag_start(self, e):
        self._drag_x = e.x
        self._drag_y = e.y

    def _drag_motion(self, e):
        x = self.root.winfo_x() + e.x - self._drag_x
        y = self.root.winfo_y() + e.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")


# ─── INDICATOR ────────────────────────────────
class IndicatorWindow:
    def __init__(self):
        self.root=tk.Tk()
        self.root.title("")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost",True)
        self.root.attributes("-alpha",0.93)
        self.root.configure(bg="#0A3D1F")
        w,h=310,70
        sw=self.root.winfo_screenwidth()
        sh=self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{sw-w-20}+{sh-h-60}")
        self.cv=tk.Canvas(self.root,width=w,height=h,bg="#0A3D1F",highlightthickness=0)
        self.cv.pack()
        pts=[22,4,w-22,4,w,4,w,22,w,h-22,w,h,w-22,h,22,h,4,h,4,h-22,4,22,4,4]
        self.cv.create_polygon(pts,smooth=True,fill="#0D5C2E",outline="#00A550",width=2)
        self.dot=self.cv.create_oval(18,26,34,42,fill="#4a4a6a",outline="")
        self.txt1=self.cv.create_text(48,24,anchor="w",text=f"{LOGO} {APP_EN} | {APP_NAME}",fill="#E8F5E9",font=("Segoe UI",9,"bold"))
        self.txt2=self.cv.create_text(48,44,anchor="w",text="Ctrl+Shift+B/E চাপুন",fill="#5A9E82",font=("Segoe UI",8))
        self._pulse_on=False
        self._pulse_job=None
        self.root.withdraw()

    def show_idle(self):
        self.root.deiconify()
        self.cv.itemconfig(self.dot,fill="#00A550")
        self.cv.itemconfig(self.txt1,text=f"{LOGO} {APP_EN}",fill="#E8F5E9")
        self.cv.itemconfig(self.txt2,text="Ctrl+Shift+B/E চাপুন",fill="#5A9E82")
        self._stop_pulse()
        if toolbar_win:
            toolbar_win.update_status("● প্রস্তুত","#00C853")

    def show_recording(self,lang="bn"):
        self.root.deiconify()
        self.cv.itemconfig(self.dot,fill="#e63946")
        if lang=="bn":
            self.cv.itemconfig(self.txt1,text="🟢 বাংলা রেকর্ড হচ্ছে...",fill="#ff6b6b")
        else:
            self.cv.itemconfig(self.txt1,text="🔵 English recording...",fill="#58a6ff")
        self.cv.itemconfig(self.txt2,text="থামাতে আবার চাপুন",fill="#aaaacc")
        self._start_pulse()
        if toolbar_win:
            toolbar_win.update_status("● রেকর্ড হচ্ছে","#F42A41")
            toolbar_win.update_mode(lang)

    def show_processing(self):
        self.cv.itemconfig(self.dot,fill="#f9a825")
        self.cv.itemconfig(self.txt1,text="⟳ প্রসেস হচ্ছে...",fill="#ffd166")
        self.cv.itemconfig(self.txt2,text="একটু অপেক্ষা করুন",fill="#aaaacc")
        self._stop_pulse()
        self.root.after(8000,self.root.withdraw)

    def show_ai_polish(self):
        self.root.deiconify()
        self.cv.itemconfig(self.dot,fill="#a855f7")
        self.cv.itemconfig(self.txt1,text="✨ AI সাজাচ্ছে...",fill="#c084fc")
        self.cv.itemconfig(self.txt2,text="একটু অপেক্ষা করুন",fill="#aaaacc")
        self._stop_pulse()
        if toolbar_win:
            toolbar_win.update_status("⟳ প্রসেস হচ্ছে","#f9a825")

    def show_done(self,text=""):
        s=text[:26]+"..." if len(text)>26 else text
        self.cv.itemconfig(self.dot,fill="#06d6a0")
        self.cv.itemconfig(self.txt1,text="✓ পেস্ট হয়েছে",fill="#06d6a0")
        self.cv.itemconfig(self.txt2,text=s if s else "সফল!",fill="#aaaacc")
        self._stop_pulse()
        self.root.after(2500,self.root.withdraw)

    def show_click_paste(self, text=""):
        """Show indicator with Ctrl+V instruction"""
        s = text[:20]+"..." if len(text)>20 else text
        self.root.deiconify()
        self.cv.itemconfig(self.dot, fill="#00C853")
        self.cv.itemconfig(self.txt1, text="✓ Ready! Ctrl+V চাপুন", fill="#00E676")
        self.cv.itemconfig(self.txt2, text=s if s else "লেখা clipboard-এ আছে", fill="#ffd166")
        self._stop_pulse()
        self.root.after(8000, self._auto_hide)

    def _do_paste(self, event=None):
        """Paste when indicator clicked - minimize indicator first then paste"""
        self.cv.unbind("<Button-1>")
        self.root.withdraw()
        time.sleep(0.1)
        # Now paste - active window should be whatever was before
        keyboard.press_and_release("ctrl+v")
        print(f"[PASTE] ctrl+v sent")
        # Show done after brief delay
        self.root.after(300, self._show_paste_done)

    def _show_paste_done(self):
        self.root.deiconify()
        self.cv.itemconfig(self.txt1, text="✓ পেস্ট হয়েছে!", fill="#06d6a0")
        self.cv.itemconfig(self.txt2, text="সফল!", fill="#aaaacc")
        self.root.after(2000, self.root.withdraw)
        if toolbar_win:
            toolbar_win.update_status("✓ সফল", "#06d6a0")

    def _auto_hide(self):
        self.cv.unbind("<Button-1>")
        self.root.withdraw()

    def show_done_restore(self,text=""):
        """Show done with restore clipboard button"""
        s=text[:20]+"..." if len(text)>20 else text
        self.root.deiconify()
        self.cv.itemconfig(self.dot,fill="#06d6a0")
        self.cv.itemconfig(self.txt1,text="✓ পেস্ট হয়েছে",fill="#06d6a0")
        self.cv.itemconfig(self.txt2,text="📋 Ctrl+Shift+Z = Restore clipboard",fill="#ffd166")
        self._stop_pulse()
        # Click to restore clipboard
        self.cv.bind("<Button-1>", self._restore_clipboard)
        self.root.after(4000, self._auto_hide_restore)

    def _restore_clipboard(self, event=None):
        try:
            if _saved_clipboard:
                pyperclip.copy(_saved_clipboard)
                self.cv.itemconfig(self.txt2,text="📋 Clipboard restored!",fill="#06d6a0")
                self.cv.unbind("<Button-1>")
                self.root.after(1500,self.root.withdraw)
        except:
            pass

    def _auto_hide_restore(self):
        self.cv.unbind("<Button-1>")
        self.root.withdraw()
        if toolbar_win:
            toolbar_win.update_status("✓ সফল","#06d6a0")

    def show_error(self,msg=""):
        self.cv.itemconfig(self.dot,fill="#e63946")
        self.cv.itemconfig(self.txt1,text="✗ সমস্যা হয়েছে",fill="#ff6b6b")
        self.cv.itemconfig(self.txt2,text=msg[:35] if msg else "আবার চেষ্টা করুন",fill="#ff9999")
        self._stop_pulse()
        self.root.after(3000,self.root.withdraw)
        if toolbar_win:
            toolbar_win.update_status("✗ সমস্যা","#F42A41")

    def _start_pulse(self):
        self._pulse_on=True
        self._pulse(True)

    def _stop_pulse(self):
        self._pulse_on=False
        if self._pulse_job:
            self.root.after_cancel(self._pulse_job)

    def _pulse(self,big):
        if not self._pulse_on:
            return
        d=2 if big else 0
        self.cv.coords(self.dot,18+d,26+d,34-d,42-d)
        self.cv.itemconfig(self.dot,fill="#e63946" if big else "#ff4d6d")
        self._pulse_job=self.root.after(500,lambda:self._pulse(not big))

    def run(self):
        self.root.mainloop()

    def safe(self,fn,*args):
        self.root.after(0,lambda:fn(*args))


# ─── AUDIO ────────────────────────────────────
def audio_callback(indata,frames,time_info,status):
    if is_recording:
        audio_frames.append(indata.copy())

def save_wav(frames,path):
    audio=np.concatenate(frames,axis=0)
    audio=(audio*32767).astype(np.int16)
    with wave.open(path,"wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio.tobytes())

def paste_text_win32(text):
    """Paste using WM_CHAR - works with Unicode Bangla"""
    try:
        import ctypes
        WM_CHAR = 0x0102
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return False
        # Get focused child window
        tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
        focused = ctypes.windll.user32.GetFocus()
        target = focused if focused else hwnd
        
        for char in text:
            if char == "\n":
                ctypes.windll.user32.PostMessageW(target, WM_CHAR, 13, 0)
            else:
                ctypes.windll.user32.PostMessageW(target, WM_CHAR, ord(char), 0)
        return True
    except Exception as e:
        print(f"[!] WM_CHAR failed: {e}")
        return False


def ai_polish_text(text, lang):
    """Use Groq to polish/correct the text"""
    if not GROQ_API_KEY:
        return text
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        if lang == "bn":
            prompt = f"""You must respond in Bengali (Bangla) script only. Do NOT translate to English.

Task: Edit and polish the following Bengali text. Keep it in Bengali.

Rules:
- Correct Bengali grammar and spelling
- Add proper punctuation (।, ?, !, ,)
- Convert spoken Bengali to written Bengali
- Do NOT translate to English
- Return ONLY the edited Bengali text

Bengali text to edit: {text}

Edited Bengali text (in Bengali script):"""
        else:
            prompt = f"""You are a professional English editor. Polish the following spoken or rough English text into proper written English.

Rules:
- Fix grammar, spelling, and punctuation
- Convert spoken language to written form
- Keep the original meaning intact
- Return ONLY the polished text, nothing else

Text: {text}"""

        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2500,
            "temperature": 0.1
        }
        r = requests.post(url, headers=headers, json=data, timeout=25)
        if r.status_code == 200:
            result = r.json()["choices"][0]["message"]["content"].strip()
            print(f"[AI] Polish: {result[:50]}...")
            return result
        elif r.status_code == 403:
            print(f"[AI] 403 - VPN/network blocked")
            return "__ERROR_403__"
        else:
            print(f"[AI] Error status: {r.status_code}")
            return "__ERROR__"
    except Exception as e:
        print(f"[AI] Error: {e}")
        return "__ERROR__"
    return "__ERROR__"


def apply_punct(text,lang):
    if raw_mode:
        return text.strip()
    pmap=PUNCT_BN if lang=="bn" else PUNCT_EN
    for cmd,sym in pmap.items():
        text=text.replace(cmd,sym)
    return text.strip()

# Bengali digit map
BN_DIGITS = {"0":"০","1":"১","2":"২","3":"৩","4":"৪","5":"৫","6":"৬","7":"৭","8":"৮","9":"৯"}

# Bengali number words
BN_NUM_WORDS = {
    "শূন্য":"০","এক":"১","দুই":"২","তিন":"৩","চার":"৪",
    "পাঁচ":"৫","ছয়":"৬","সাত":"৭","আট":"৮","নয়":"৯",
    "দশ":"১০","এগারো":"১১","বারো":"১২","তেরো":"১৩","চোদ্দ":"১৪",
    "পনেরো":"১৫","ষোলো":"১৬","সতেরো":"১৭","আঠারো":"১৮","উনিশ":"১৯",
    "বিশ":"২০","ত্রিশ":"৩০","চল্লিশ":"৪০","পঞ্চাশ":"৫০",
    "ষাট":"৬০","সত্তর":"৭০","আশি":"৮০","নব্বই":"৯০","একশো":"১০০",
}

# English number words
EN_NUM_WORDS = {
    "zero":"0","one":"1","two":"2","three":"3","four":"4",
    "five":"5","six":"6","seven":"7","eight":"8","nine":"9",
    "ten":"10","eleven":"11","twelve":"12","thirteen":"13","fourteen":"14",
    "fifteen":"15","sixteen":"16","seventeen":"17","eighteen":"18","nineteen":"19",
    "twenty":"20","thirty":"30","forty":"40","fifty":"50",
    "sixty":"60","seventy":"70","eighty":"80","ninety":"90","hundred":"100",
}

class APIKeySetupWindow:
    def __init__(self):
        self.root = tk.Toplevel()
        self.root.title("API Key সেটআপ — BoloBangla AI")
        self.root.configure(bg="#0A3D1F")
        self.root.attributes("-topmost", True)
        self.root.resizable(False, False)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"560x640+{(sw-560)//2}+{(sh-640)//2}")
        self._build()

    def _build(self):
        # Header
        head = tk.Frame(self.root, bg="#004D38", pady=10)
        head.pack(fill="x")
        tk.Label(head, text="🔑 AI Feature চালু করুন",
                 font=("Segoe UI",15,"bold"), bg="#004D38", fg="#F42A41").pack()
        tk.Label(head, text="ভয়েস টাইপিং key ছাড়াই চলে। শুধু AI সুবিধার জন্য একটি free key লাগবে।",
                 font=("Segoe UI",8), bg="#004D38", fg="#B9F6CA").pack(pady=(2,0))

        body = tk.Frame(self.root, bg="#0A3D1F")
        body.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(body, text="কীভাবে FREE Key নেবেন — ৪টি সহজ ধাপ",
                 font=("Segoe UI",11,"bold"), bg="#0A3D1F", fg="#FFD700").pack(anchor="w", pady=(0,8))

        steps = [
            ("ধাপ ১", "নিচের 'Groq সাইট খুলুন' বোতামে ক্লিক করুন।\nব্রাউজারে console.groq.com খুলবে।"),
            ("ধাপ ২", "Google/Email দিয়ে free অ্যাকাউন্ট খুলুন (Sign up)।\nকোনো টাকা লাগবে না।"),
            ("ধাপ ৩", "বাম পাশে 'API Keys' এ যান → 'Create API Key' চাপুন।\nএকটি নাম দিন (যেমন: bolobangla)।"),
            ("ধাপ ৪", "key-টি কপি করুন (gsk_ দিয়ে শুরু) এবং নিচের বক্সে\npaste করে 'Save করুন' চাপুন।"),
        ]
        for tag, desc in steps:
            row = tk.Frame(body, bg="#0D5C2E")
            row.pack(fill="x", pady=3)
            tk.Label(row, text=tag, font=("Segoe UI",9,"bold"), bg="#1565C0",
                     fg="white", width=7, pady=4).pack(side="left", padx=(4,8), pady=4)
            tk.Label(row, text=desc, font=("Segoe UI",9), bg="#0D5C2E",
                     fg="#E8F5E9", justify="left", anchor="w").pack(side="left", pady=4)

        # Open Groq site button
        tk.Button(body, text="🌐 Groq সাইট খুলুন (console.groq.com)",
                  font=("Segoe UI",10,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", padx=10, pady=8, cursor="hand2",
                  command=self._open_groq).pack(fill="x", pady=(12,8))

        # Key input
        tk.Label(body, text="আপনার API Key এখানে paste করুন:",
                 font=("Segoe UI",10,"bold"), bg="#0A3D1F", fg="white").pack(anchor="w", pady=(6,3))
        self.key_entry = tk.Entry(body, font=("Consolas",10), bg="white", fg="black",
                                  relief="flat", show="•")
        self.key_entry.pack(fill="x", ipady=6)
        # Pre-fill if key exists
        if GROQ_API_KEY:
            self.key_entry.insert(0, GROQ_API_KEY)

        # Show/hide toggle
        self.show_var = tk.IntVar(value=0)
        tk.Checkbutton(body, text="Key দেখান", variable=self.show_var,
                       bg="#0A3D1F", fg="#B9F6CA", selectcolor="#0D5C2E",
                       activebackground="#0A3D1F", font=("Segoe UI",8),
                       command=self._toggle_show).pack(anchor="w", pady=(4,0))

        self.status = tk.Label(body, text="", font=("Segoe UI",9),
                               bg="#0A3D1F", fg="#00C853")
        self.status.pack(pady=(6,0))

        # Buttons
        btnf = tk.Frame(body, bg="#0A3D1F")
        btnf.pack(fill="x", pady=(10,0))
        tk.Button(btnf, text="✓ Save করুন", font=("Segoe UI",11,"bold"),
                  bg="#006A4E", fg="white", relief="flat", padx=12, pady=8,
                  cursor="hand2", command=self._save).pack(side="left", expand=True, fill="x", padx=(0,4))
        tk.Button(btnf, text="বন্ধ করুন", font=("Segoe UI",11),
                  bg="#3D0A0A", fg="#ff9999", relief="flat", padx=12, pady=8,
                  cursor="hand2", command=self.root.destroy).pack(side="left", expand=True, fill="x", padx=(4,0))

    def _toggle_show(self):
        self.key_entry.config(show="" if self.show_var.get() else "•")

    def _open_groq(self):
        import webbrowser
        webbrowser.open("https://console.groq.com/keys")

    def _save(self):
        key = self.key_entry.get().strip()
        if not key:
            self.status.config(text="⚠️ Key বক্স খালি!", fg="#F42A41")
            return
        if not key.startswith("gsk_"):
            self.status.config(text="⚠️ সঠিক key নয় (gsk_ দিয়ে শুরু হওয়ার কথা)", fg="#F42A41")
            return
        # Save to config
        try:
            cfg = load_config()
            cfg["groq_api_key"] = key
            save_config(cfg)
            global GROQ_API_KEY
            GROQ_API_KEY = key
            self.status.config(text="✓ Key সংরক্ষিত হয়েছে! এখন সব AI feature কাজ করবে।", fg="#00C853")
            self.root.after(1500, self.root.destroy)
        except Exception as e:
            self.status.config(text=f"⚠️ {str(e)[:40]}", fg="#F42A41")


class VirtualKeyboardWindow:
    def __init__(self, lang="bn"):
        self.lang = lang
        self.root = tk.Toplevel()
        self.root.title("Virtual Keyboard — BoloBangla AI")
        self.font_size = 10
        self.root.configure(bg="#1a5c2e")
        self.root.attributes("-topmost", True)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"750x430+{(sw-750)//2}+{(sh-430)//2}")
        self._build()

    def _make_key(self, parent, label, char, bg="#3a9e5f", fg="#ffffff"):
        def on_enter(e):
            global _prev_hwnd
            import ctypes
            hw = ctypes.windll.user32.GetForegroundWindow()
            if hw != self.root.winfo_id():
                _prev_hwnd = hw
        def on_release(e):
            if char is None:
                keyboard.press_and_release("backspace")
            else:
                self.root.after(50, lambda: insert_text(char))
        w = max(3, len(label)+1)
        btn = tk.Button(parent, text=label,
                 font=("Segoe UI",self.font_size,"bold"),
                 bg="#3a9e5f", fg="#ffffff",
                 relief="flat", padx=4, pady=4,
                 cursor="hand2", width=w)
        btn.bind("<Enter>", on_enter)
        btn.bind("<ButtonRelease-1>", on_release)
        return btn

    def _build(self):
        title_f = tk.Frame(self.root, bg="#2d7a4f", pady=6)
        title_f.pack(fill="x")
        tk.Label(title_f, text="Virtual Keyboard",
                 font=("Segoe UI",12,"bold"), bg="#2d7a4f", fg="#F42A41").pack(side="left", padx=10)
        self.lang_var = tk.StringVar(value=self.lang)
        tk.Radiobutton(title_f, text="বাংলা", variable=self.lang_var, value="bn",
                      bg="#2d7a4f", fg="#E8F5E9", selectcolor="#1a5c2e",
                      activebackground="#2d7a4f", font=("Segoe UI",9),
                      command=self._rebuild).pack(side="left", padx=6)
        tk.Radiobutton(title_f, text="English", variable=self.lang_var, value="en",
                      bg="#2d7a4f", fg="#E8F5E9", selectcolor="#1a5c2e",
                      activebackground="#2d7a4f", font=("Segoe UI",9),
                      command=self._rebuild).pack(side="left", padx=6)
        tk.Button(title_f, text="X", font=("Segoe UI",11,"bold"),
                  bg="#2d7a4f", fg="#F42A41", relief="flat",
                  cursor="hand2", command=self.root.destroy).pack(side="right", padx=8)
        tk.Button(title_f, text="🔍+", font=("Segoe UI Emoji",9),
                  bg="#1a5c2e", fg="white", relief="flat",
                  cursor="hand2", command=self._zoom_in).pack(side="right", padx=2)
        tk.Button(title_f, text="🔍-", font=("Segoe UI Emoji",9),
                  bg="#1a5c2e", fg="white", relief="flat",
                  cursor="hand2", command=self._zoom_out).pack(side="right", padx=2)
        self.kb_f = tk.Frame(self.root, bg="#1a5c2e")
        self.kb_f.pack(fill="both", expand=True, padx=8, pady=6)
        self._rebuild()

    def _translate(self, src_lang, tgt_lang):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="⚠️ কোনো লেখা নেই!", fg="#F42A41")
            return
        if not GROQ_API_KEY:
            self.status.config(text="🔑 AI Key সেটআপ করুন...", fg="#f9a825")
            APIKeySetupWindow()
            return
        if src_lang == "bn":
            self.status.config(text="⟳ বাংলা → English অনুবাদ হচ্ছে...", fg="#f9a825")
        else:
            self.status.config(text="⟳ English → বাংলা অনুবাদ হচ্ছে...", fg="#f9a825")
        self.root.update()
        def do_translate():
            try:
                if src_lang == "bn":
                    prompt = f"""Translate the following Bengali text to English. Return only the translated text, nothing else.

Bengali: {text}"""
                else:
                    prompt = f"""নিচের English লেখাটি বাংলায় অনুবাদ করো। শুধু অনুবাদটি দাও, অন্য কিছু লিখবে না।

English: {text}"""
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.2
                }
                r = requests.post(url, headers=headers, json=data, timeout=15)
                if r.status_code == 200:
                    result = r.json()["choices"][0]["message"]["content"].strip()
                    self.root.after(0, lambda: self._show_result(result))
                    if src_lang == "bn":
                        self.root.after(0, lambda: self.status.config(text="✓ বাংলা → English সম্পন্ন!", fg="#00C853"))
                    else:
                        self.root.after(0, lambda: self.status.config(text="✓ English → বাংলা সম্পন্ন!", fg="#00C853"))
                else:
                    self.root.after(0, lambda: self.status.config(text="VPN বন্ধ করে আবার চেষ্টা করুন!" if r.status_code==403 else f"Error: {r.status_code}", fg="#F42A41"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(text=f"⚠️ {str(e)[:40]}", fg="#F42A41"))
        import threading
        threading.Thread(target=do_translate, daemon=True).start()

    def _bn_to_en(self):
        self._translate("bn", "en")

    def _en_to_bn(self):
        self._translate("en", "bn")

    def _paste_to_window(self):
        """Copy text and paste to last active window"""
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="⚠️ কোনো লেখা নেই!", fg="#F42A41")
            return
        try:
            import ctypes
            old_clip = pyperclip.paste()
            pyperclip.copy(text)
            # Minimize editor first
            self.root.iconify()
            time.sleep(0.25)
            if _prev_hwnd:
                keyboard.press("alt")
                time.sleep(0.05)
                ctypes.windll.user32.SetForegroundWindow(_prev_hwnd)
                time.sleep(0.05)
                keyboard.release("alt")
                time.sleep(0.25)
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.2)
            if old_clip:
                pyperclip.copy(old_clip)
            self.status.config(text="✓ Paste সম্পন্ন!", fg="#00C853")
            self.root.after(1000, self.root.deiconify)
        except Exception as e:
            self.status.config(text=f"⚠️ {str(e)[:30]}", fg="#F42A41")

    def _zoom_in(self):
        if self.font_size < 16:
            self.font_size += 1
            self._rebuild()

    def _zoom_out(self):
        if self.font_size > 7:
            self.font_size -= 1
            self._rebuild()


    def _rebuild(self):
        for w in self.kb_f.winfo_children():
            w.destroy()

        lang = self.lang_var.get()

        if lang == "bn":
            # Tab buttons
            tab_f = tk.Frame(self.kb_f, bg="#1a5c2e")
            tab_f.pack(fill="x", pady=(0,2))
            if not hasattr(self, "tab_var"):
                self.tab_var = tk.StringVar(value="main")
            for val, lbl in [("main","মূল বর্ণ"),("conjunct","যুক্তাক্ষর"),("symbols","কার/চিহ্ন")]:
                tk.Radiobutton(tab_f, text=lbl, variable=self.tab_var, value=val,
                              bg="#1a5c2e", fg="white", selectcolor="#2d7a4f",
                              activebackground="#1a5c2e", font=("Segoe UI",9,"bold"),
                              command=self._rebuild).pack(side="left", padx=6)

            # Color legend
            leg_f = tk.Frame(self.kb_f, bg="#1a5c2e")
            leg_f.pack(fill="x", pady=(0,4))
            for clr, lbl in [("#c8960c","স্বরবর্ণ"),("#2d7a4f","ব্যঞ্জনবর্ণ"),
                              ("#cc6600","কার/মাত্রা"),("#c0392b","বিরামচিহ্ন"),
                              ("#1565C0","যুক্তাক্ষর"),("#555","সংখ্যা")]:
                tk.Label(leg_f, text="■", font=("Segoe UI",10), bg="#1a5c2e", fg=clr).pack(side="left")
                tk.Label(leg_f, text=lbl, font=("Segoe UI",7), bg="#1a5c2e", fg="white").pack(side="left", padx=(0,5))

            tab = self.tab_var.get()

            if tab == "conjunct":
                rows = [
                    [("ক্ক","ক্ক","#1565C0"),("ক্ট","ক্ট","#1565C0"),("ক্ত","ক্ত","#1565C0"),("ক্ন","ক্ন","#1565C0"),("ক্ব","ক্ব","#1565C0"),("ক্ম","ক্ম","#1565C0"),("ক্য","ক্য","#1565C0"),("ক্র","ক্র","#1565C0"),("ক্ল","ক্ল","#1565C0"),("ক্ষ","ক্ষ","#1565C0"),("ক্স","ক্স","#1565C0")],
                    [("গ্ন","গ্ন","#1565C0"),("গ্ব","গ্ব","#1565C0"),("গ্ম","গ্ম","#1565C0"),("গ্য","গ্য","#1565C0"),("গ্র","গ্র","#1565C0"),("ঘ্ন","ঘ্ন","#1565C0"),("ঙ্ক","ঙ্ক","#1565C0"),("ঙ্গ","ঙ্গ","#1565C0"),("চ্চ","চ্চ","#1565C0"),("চ্ছ","চ্ছ","#1565C0"),("জ্জ","জ্জ","#1565C0")],
                    [("জ্ঝ","জ্ঝ","#1565C0"),("জ্ঞ","জ্ঞ","#1565C0"),("ট্ট","ট্ট","#1565C0"),("ড্ড","ড্ড","#1565C0"),("ণ্ট","ণ্ট","#1565C0"),("ণ্ড","ণ্ড","#1565C0"),("ত্ত","ত্ত","#1565C0"),("ত্থ","ত্থ","#1565C0"),("ত্ন","ত্ন","#1565C0"),("ত্ব","ত্ব","#1565C0"),("ত্র","ত্র","#1565C0")],
                    [("দ্দ","দ্দ","#1565C0"),("দ্ধ","দ্ধ","#1565C0"),("দ্ব","দ্ব","#1565C0"),("দ্ভ","দ্ভ","#1565C0"),("দ্র","দ্র","#1565C0"),("ন্ত","ন্ত","#1565C0"),("ন্দ","ন্দ","#1565C0"),("ন্ধ","ন্ধ","#1565C0"),("ন্ন","ন্ন","#1565C0"),("ন্ব","ন্ব","#1565C0"),("ন্ম","ন্ম","#1565C0")],
                    [("প্ত","প্ত","#1565C0"),("প্প","প্প","#1565C0"),("প্র","প্র","#1565C0"),("ব্দ","ব্দ","#1565C0"),("ব্ধ","ব্ধ","#1565C0"),("ব্ব","ব্ব","#1565C0"),("ব্র","ব্র","#1565C0"),("ম্ব","ম্ব","#1565C0"),("ম্ভ","ম্ভ","#1565C0"),("ম্ম","ম্ম","#1565C0"),("ম্র","ম্র","#1565C0")],
                    [("র্ক","র্ক","#1565C0"),("র্গ","র্গ","#1565C0"),("র্ত","র্ত","#1565C0"),("র্থ","র্থ","#1565C0"),("র্দ","র্দ","#1565C0"),("র্ধ","র্ধ","#1565C0"),("র্ন","র্ন","#1565C0"),("র্ব","র্ব","#1565C0"),("র্ম","র্ম","#1565C0"),("র্য","র্য","#1565C0"),("র্শ","র্শ","#1565C0")],
                    [("ল্ক","ল্ক","#1565C0"),("ল্প","ল্প","#1565C0"),("ল্ব","ল্ব","#1565C0"),("ল্ম","ল্ম","#1565C0"),("ল্ল","ল্ল","#1565C0"),("শ্চ","শ্চ","#1565C0"),("শ্ব","শ্ব","#1565C0"),("শ্র","শ্র","#1565C0"),("ষ্ক","ষ্ক","#1565C0"),("ষ্ট","ষ্ট","#1565C0"),("ষ্ণ","ষ্ণ","#1565C0")],
                    [("স্ক","স্ক","#1565C0"),("স্ত","স্ত","#1565C0"),("স্থ","স্থ","#1565C0"),("স্ন","স্ন","#1565C0"),("স্ব","স্ব","#1565C0"),("স্ম","স্ম","#1565C0"),("স্র","স্র","#1565C0"),("হ্ন","হ্ন","#1565C0"),("হ্ম","হ্ম","#1565C0"),("হ্র","হ্র","#1565C0"),("ক্ষ্ম","ক্ষ্ম","#1565C0")],
                ]
            elif tab == "symbols":
                rows = [
                    [("া","া","#cc6600"),("ি","ি","#cc6600"),("ী","ী","#cc6600"),("ু","ু","#cc6600"),("ূ","ূ","#cc6600"),("ৃ","ৃ","#cc6600"),("ে","ে","#cc6600"),("ৈ","ৈ","#cc6600"),("ো","ো","#cc6600"),("ৌ","ৌ","#cc6600"),("্","্","#cc6600"),("ঁ","ঁ","#cc6600"),("ং","ং","#cc6600"),("ঃ","ঃ","#cc6600")],
                    [("।","।","#c0392b"),(",",",","#c0392b"),("?","?","#c0392b"),("!","!","#c0392b"),(":",":","#c0392b"),(";",";","#c0392b"),("—","—","#c0392b"),("(",")","#c0392b"),(")",")","#c0392b"),('"','"',"#c0392b"),("'","'","#c0392b")],
                    [("১","১","#555"),("২","২","#555"),("৩","৩","#555"),("৪","৪","#555"),("৫","৫","#555"),("৬","৬","#555"),("৭","৭","#555"),("৮","৮","#555"),("৯","৯","#555"),("০","০","#555")],
                ]
            else:  # main
                rows = [
                    [("অ","অ","#c8960c"),("আ","আ","#c8960c"),("ই","ই","#c8960c"),("ঈ","ঈ","#c8960c"),("উ","উ","#c8960c"),("ঊ","ঊ","#c8960c"),("ঋ","ঋ","#c8960c"),("এ","এ","#c8960c"),("ঐ","ঐ","#c8960c"),("ও","ও","#c8960c"),("ঔ","ঔ","#c8960c"),("ং","ং","#c8960c"),("ঃ","ঃ","#c8960c"),("ঁ","ঁ","#c8960c")],
                    [("ক","ক","#2d7a4f"),("খ","খ","#2d7a4f"),("গ","গ","#2d7a4f"),("ঘ","ঘ","#2d7a4f"),("ঙ","ঙ","#2d7a4f"),("চ","চ","#2d7a4f"),("ছ","ছ","#2d7a4f"),("জ","জ","#2d7a4f"),("ঝ","ঝ","#2d7a4f"),("ঞ","ঞ","#2d7a4f"),("ট","ট","#2d7a4f"),("ঠ","ঠ","#2d7a4f"),("ড","ড","#2d7a4f"),("ঢ","ঢ","#2d7a4f")],
                    [("ণ","ণ","#2d7a4f"),("ত","ত","#2d7a4f"),("থ","থ","#2d7a4f"),("দ","দ","#2d7a4f"),("ধ","ধ","#2d7a4f"),("ন","ন","#2d7a4f"),("প","প","#2d7a4f"),("ফ","ফ","#2d7a4f"),("ব","ব","#2d7a4f"),("ভ","ভ","#2d7a4f"),("ম","ম","#2d7a4f"),("য","য","#2d7a4f"),("র","র","#2d7a4f"),("ল","ল","#2d7a4f")],
                    [("শ","শ","#2d7a4f"),("ষ","ষ","#2d7a4f"),("স","স","#2d7a4f"),("হ","হ","#2d7a4f"),("ড়","ড়","#2d7a4f"),("ঢ়","ঢ়","#2d7a4f"),("য়","য়","#2d7a4f"),("ৎ","ৎ","#2d7a4f"),("া","া","#cc6600"),("ি","ি","#cc6600"),("ী","ী","#cc6600"),("ু","ু","#cc6600"),("ূ","ূ","#cc6600"),("ৃ","ৃ","#cc6600")],
                    [("ে","ে","#cc6600"),("ৈ","ৈ","#cc6600"),("ো","ো","#cc6600"),("ৌ","ৌ","#cc6600"),("্","্","#cc6600"),("।","।","#c0392b"),("?","?","#c0392b"),("!","!","#c0392b"),(",",",","#c0392b"),(":",":","#c0392b"),(";",";","#c0392b"),("—","—","#c0392b")],
                    [("১","১","#555"),("২","২","#555"),("৩","৩","#555"),("৪","৪","#555"),("৫","৫","#555"),("৬","৬","#555"),("৭","৭","#555"),("৮","৮","#555"),("৯","৯","#555"),("০","০","#555"),("<-",None,"#8B0000")],
                ]

        else:  # English
            rows = [
                [("q","q"),("w","w"),("e","e"),("r","r"),("t","t"),("y","y"),("u","u"),("i","i"),("o","o"),("p","p"),("[","["),("]","]"),("<-",None)],
                [("a","a"),("s","s"),("d","d"),("f","f"),("g","g"),("h","h"),("j","j"),("k","k"),("l","l"),(";",";"),(":",":")],
                [("z","z"),("x","x"),("c","c"),("v","v"),("b","b"),("n","n"),("m","m"),(",",","),(".","."),(  "/","/"),(  "?","?")],
                [("Q","Q"),("W","W"),("E","E"),("R","R"),("T","T"),("Y","Y"),("U","U"),("I","I"),("O","O"),("P","P"),("{","{"),("}","}")],
                [("A","A"),("S","S"),("D","D"),("F","F"),("G","G"),("H","H"),("J","J"),("K","K"),("L","L"),("!","!"),('"','"')],
                [("Z","Z"),("X","X"),("C","C"),("V","V"),("B","B"),("N","N"),("M","M"),("1","1"),("2","2"),("3","3"),("4","4"),("5","5")],
                [("6","6"),("7","7"),("8","8"),("9","9"),("0","0"),("@","@"),("#","#"),("$","$"),("%","%"),("^","^"),("&","&"),("*","*")],
            ]

        # Render rows
        for row in rows:
            rf = tk.Frame(self.kb_f, bg="#1a5c2e")
            rf.pack(pady=1)
            for item in row:
                if len(item) == 3:
                    label, char, bg = item
                elif len(item) == 2:
                    label, char = item
                    bg = "#3a9e5f"
                else:
                    continue
                if label == "":
                    continue
                self._make_key(rf, label, char, bg=bg).pack(side="left", padx=1)

        # Space bar
        sf = tk.Frame(self.kb_f, bg="#1a5c2e")
        sf.pack(pady=2)
        sp = tk.Button(sf, text="Space / স্পেস",
                  font=("Segoe UI", self.font_size,"bold"),
                  bg="#2d7a4f", fg="#ffffff",
                  relief="flat", padx=50, pady=4,
                  cursor="hand2")
        def on_enter_sp(e):
            global _prev_hwnd
            import ctypes
            hw = ctypes.windll.user32.GetForegroundWindow()
            if hw != self.root.winfo_id():
                _prev_hwnd = hw
        sp.bind("<Enter>", on_enter_sp)
        sp.bind("<ButtonRelease-1>", lambda e: self.root.after(50, lambda: insert_text(" ")))
        sp.pack()
    def _switch_lang(self):
        self._rebuild()


class AIEditorWindow:
    def __init__(self, lang="bn"):
        self.lang = lang
        self.root = tk.Toplevel()
        self.root.title("✨ AI Text Editor — BoloBangla AI")
        self.root.geometry("1050x600")
        self.root.configure(bg="#0A3D1F")
        self.root.attributes("-topmost", True)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"1050x600+{(sw-1050)//2}+{(sh-600)//2}")
        self._build()

    def _build(self):
        # Title
        self.editor_font_size = 11
        title_row = tk.Frame(self.root, bg="#0A3D1F")
        title_row.pack(pady=(10,2))
        tk.Label(title_row, text="✨ AI Text Editor",
                 font=("Segoe UI",13,"bold"), bg="#0A3D1F", fg="#F42A41").pack(side="left", padx=8)
        tk.Button(title_row, text="🔍+", font=("Segoe UI Emoji",9),
                  bg="#0D5C2E", fg="#B9F6CA", relief="flat", padx=6,
                  cursor="hand2", command=self._zoom_in).pack(side="left", padx=2)
        tk.Button(title_row, text="🔍-", font=("Segoe UI Emoji",9),
                  bg="#0D5C2E", fg="#B9F6CA", relief="flat", padx=6,
                  cursor="hand2", command=self._zoom_out).pack(side="left", padx=2)
        tk.Label(self.root, text="লেখা paste করুন বা টাইপ করুন, তারপর AI দিয়ে সাজান",
                 font=("Segoe UI",8), bg="#0A3D1F", fg="#5A9E82").pack(pady=(0,8))

        # Language toggle
        lang_frame = tk.Frame(self.root, bg="#0A3D1F")
        lang_frame.pack(pady=(0,6))
        self.lang_var = tk.StringVar(value=self.lang)
        tk.Radiobutton(lang_frame, text="বাংলা", variable=self.lang_var, value="bn",
                      bg="#0A3D1F", fg="#E8F5E9", selectcolor="#0D5C2E",
                      activebackground="#0A3D1F", font=("Segoe UI",9)).pack(side="left", padx=8)
        tk.Radiobutton(lang_frame, text="English", variable=self.lang_var, value="en",
                      bg="#0A3D1F", fg="#E8F5E9", selectcolor="#0D5C2E",
                      activebackground="#0A3D1F", font=("Segoe UI",9)).pack(side="left", padx=8)

        # Text input
        input_frame = tk.Frame(self.root, bg="#0D5C2E", padx=2, pady=2)
        input_frame.pack(fill="both", expand=True, padx=15, pady=(0,6))
        sb = tk.Scrollbar(input_frame)
        sb.pack(side="right", fill="y")
        self.txt = tk.Text(input_frame, font=("Segoe UI",11), bg="white", fg="#000000",
                           insertbackground="black", relief="flat",
                           wrap="word", padx=8, pady=8, height=12,
                           undo=True, maxundo=50,
                           yscrollcommand=sb.set)
        self.txt.pack(fill="both", expand=True)
        sb.config(command=self.txt.yview)
        def do_undo(e):
            try:
                self.txt.edit_undo()
            except:
                pass
            return "break"
        def do_redo(e):
            try:
                self.txt.edit_redo()
            except:
                pass
            return "break"
        self.txt.bind("<Control-z>", do_undo)
        self.txt.bind("<Control-Z>", do_undo)
        self.txt.bind("<Control-y>", do_redo)
        self.txt.bind("<Control-Y>", do_redo)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0A3D1F")
        btn_frame.pack(pady=8)

        tk.Button(btn_frame, text="📋 Paste করুন",
                  font=("Segoe UI",9), bg="#0D5C2E", fg="#B9F6CA",
                  relief="flat", padx=10, pady=5, cursor="hand2",
                  command=self._paste).pack(side="left", padx=4)

        tk.Button(btn_frame, text="🖼 Image to Text",
                  font=("Segoe UI",9,"bold"), bg="#1565C0", fg="white",
                  relief="flat", padx=8, pady=5, cursor="hand2",
                  command=self._image_to_text).pack(side="left", padx=3)

        tk.Button(btn_frame, text="✨ AI সাজাও",
                  font=("Segoe UI",9,"bold"), bg="#7c3aed", fg="white",
                  relief="flat", padx=10, pady=5, cursor="hand2",
                  command=self._polish).pack(side="left", padx=3)

        tk.Button(btn_frame, text="📜 বিজয়→Unicode",
                  font=("Segoe UI",9,"bold"), bg="#5d4037", fg="white",
                  relief="flat", padx=8, pady=5, cursor="hand2",
                  command=self._bijoy_convert).pack(side="left", padx=3)

        tk.Button(btn_frame, text="🔤 Banglish→বাংলা",
                  font=("Segoe UI",9,"bold"), bg="#e65100", fg="white",
                  relief="flat", padx=8, pady=5, cursor="hand2",
                  command=self._banglish_to_bn).pack(side="left", padx=3)

        tk.Button(btn_frame, text="🔄 বাংলা→EN",
                  font=("Segoe UI",9,"bold"), bg="#1565C0", fg="white",
                  relief="flat", padx=8, pady=5, cursor="hand2",
                  command=self._bn_to_en).pack(side="left", padx=3)

        tk.Button(btn_frame, text="🔄 EN→বাংলা",
                  font=("Segoe UI",9,"bold"), bg="#006A4E", fg="white",
                  relief="flat", padx=8, pady=5, cursor="hand2",
                  command=self._en_to_bn).pack(side="left", padx=3)

        tk.Button(btn_frame, text="📤 Copy",
                  font=("Segoe UI",9), bg="#006A4E", fg="#B9F6CA",
                  relief="flat", padx=8, pady=5, cursor="hand2",
                  command=self._copy).pack(side="left", padx=3)

        tk.Button(btn_frame, text="🗑 Clear",
                  font=("Segoe UI",9), bg="#3D0A0A", fg="#ff9999",
                  relief="flat", padx=10, pady=5, cursor="hand2",
                  command=lambda: self.txt.delete("1.0","end")).pack(side="left", padx=4)

        self.status = tk.Label(self.root, text="",
                 font=("Segoe UI",8), bg="#0A3D1F", fg="#5A9E82")
        self.status.pack(pady=(0,6))

    def _translate(self, src_lang, tgt_lang):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="⚠️ কোনো লেখা নেই!", fg="#F42A41")
            return
        if not GROQ_API_KEY:
            self.status.config(text="🔑 AI Key সেটআপ করুন...", fg="#f9a825")
            APIKeySetupWindow()
            return
        if src_lang == "bn":
            self.status.config(text="⟳ বাংলা → English অনুবাদ হচ্ছে...", fg="#f9a825")
        else:
            self.status.config(text="⟳ English → বাংলা অনুবাদ হচ্ছে...", fg="#f9a825")
        self.root.update()
        def do_translate():
            try:
                if src_lang == "bn":
                    prompt = f"""Translate the following Bengali text to English. Return only the translated text, nothing else.

Bengali: {text}"""
                else:
                    prompt = f"""নিচের English লেখাটি বাংলায় অনুবাদ করো। শুধু অনুবাদটি দাও, অন্য কিছু লিখবে না।

English: {text}"""
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.2
                }
                r = requests.post(url, headers=headers, json=data, timeout=15)
                if r.status_code == 200:
                    result = r.json()["choices"][0]["message"]["content"].strip()
                    self.root.after(0, lambda: self._show_result(result))
                    if src_lang == "bn":
                        self.root.after(0, lambda: self.status.config(text="✓ বাংলা → English সম্পন্ন!", fg="#00C853"))
                    else:
                        self.root.after(0, lambda: self.status.config(text="✓ English → বাংলা সম্পন্ন!", fg="#00C853"))
                else:
                    self.root.after(0, lambda: self.status.config(text="VPN বন্ধ করে আবার চেষ্টা করুন!" if r.status_code==403 else f"Error: {r.status_code}", fg="#F42A41"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(text=f"⚠️ {str(e)[:40]}", fg="#F42A41"))
        import threading
        threading.Thread(target=do_translate, daemon=True).start()

    def _bn_to_en(self):
        self._translate("bn", "en")

    def _en_to_bn(self):
        self._translate("en", "bn")

    def _paste_to_window(self):
        """Copy text and paste to last active window"""
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="⚠️ কোনো লেখা নেই!", fg="#F42A41")
            return
        try:
            import ctypes
            old_clip = pyperclip.paste()
            pyperclip.copy(text)
            # Minimize editor first
            self.root.iconify()
            time.sleep(0.25)
            if _prev_hwnd:
                keyboard.press("alt")
                time.sleep(0.05)
                ctypes.windll.user32.SetForegroundWindow(_prev_hwnd)
                time.sleep(0.05)
                keyboard.release("alt")
                time.sleep(0.25)
            keyboard.press_and_release("ctrl+v")
            time.sleep(0.2)
            if old_clip:
                pyperclip.copy(old_clip)
            self.status.config(text="✓ Paste সম্পন্ন!", fg="#00C853")
            self.root.after(1000, self.root.deiconify)
        except Exception as e:
            self.status.config(text=f"⚠️ {str(e)[:30]}", fg="#F42A41")

    def _image_to_text(self):
        from tkinter import filedialog
        import base64 as b64
        file_path = filedialog.askopenfilename(
            title="Image Select করুন",
            filetypes=[("Image files","*.png *.jpg *.jpeg *.bmp *.webp"),("All files","*.*")]
        )
        if not file_path:
            return
        if not GROQ_API_KEY:
            self.status.config(text="🔑 AI Key সেটআপ করুন...", fg="#f9a825")
            APIKeySetupWindow()
            return
        self.status.config(text="Image থেকে Text বের হচ্ছে...", fg="#f9a825")
        self.root.update()
        def do_ocr():
            try:
                with open(file_path, "rb") as f:
                    img_data = b64.b64encode(f.read()).decode("utf-8")
                ext = file_path.lower().split(".")[-1]
                media_map = {"jpg":"image/jpeg","jpeg":"image/jpeg","png":"image/png","webp":"image/webp","bmp":"image/png"}
                media_type = media_map.get(ext, "image/jpeg")
                lang = self.lang_var.get()
                prompt = "এই image-এ যা লেখা আছে হুবহু বাংলায় লিখে দাও।" if lang=="bn" else "Extract all text from this image exactly as written."
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [{"role": "user", "content": [
                        {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{img_data}"}},
                        {"type": "text", "text": prompt}
                    ]}],
                    "max_tokens": 2000, "temperature": 0.1
                }
                r = requests.post(url, headers=headers, json=data, timeout=30)
                if r.status_code == 200:
                    result = r.json()["choices"][0]["message"]["content"].strip()
                    self.root.after(0, lambda: self._show_result(result))
                    self.root.after(0, lambda: self.status.config(text="Image থেকে Text বের হয়েছে!", fg="#00C853"))
                else:
                    emsg = "VPN বন্ধ করে আবার চেষ্টা করুন!" if r.status_code == 403 else f"Error: {r.status_code}"
                    self.root.after(0, lambda: self.status.config(text=emsg, fg="#F42A41"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(text=f"{str(e)[:40]}", fg="#F42A41"))
        import threading
        threading.Thread(target=do_ocr, daemon=True).start()

    def _translate(self, src_lang, tgt_lang):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="কোনো লেখা নেই!", fg="#F42A41")
            return
        if src_lang == "bn":
            self.status.config(text="বাংলা to English...", fg="#f9a825")
            prompt = f"Translate to English. Return only translation. Text: {text}"
        else:
            self.status.config(text="English to বাংলা...", fg="#f9a825")
            prompt = f"বাংলায় অনুবাদ করো। শুধু অনুবাদ দাও। Text: {text}"
        self.root.update()
        def do_translate():
            try:
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                data = {"model": "llama-3.3-70b-versatile", "messages": [{"role":"user","content":prompt}], "max_tokens":1000, "temperature":0.2}
                r = requests.post(url, headers=headers, json=data, timeout=15)
                if r.status_code == 200:
                    result = r.json()["choices"][0]["message"]["content"].strip()
                    self.root.after(0, lambda: self._show_result(result))
                    self.root.after(0, lambda: self.status.config(text="অনুবাদ সম্পন্ন!", fg="#00C853"))
                else:
                    emsg = "VPN বন্ধ করে আবার চেষ্টা করুন!" if r.status_code == 403 else f"Error: {r.status_code}"
                    self.root.after(0, lambda: self.status.config(text=emsg, fg="#F42A41"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(text=f"{str(e)[:40]}", fg="#F42A41"))
        import threading
        threading.Thread(target=do_translate, daemon=True).start()

    def _bijoy_convert(self):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="কোনো লেখা নেই!", fg="#F42A41")
            return
        result = bijoy_to_unicode(text)
        self._show_result(result)
        self.status.config(text="বিজয় → Unicode সম্পন্ন!", fg="#00C853")

    def _banglish_to_bn(self):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="কোনো লেখা নেই!", fg="#F42A41")
            return
        if not GROQ_API_KEY:
            self.status.config(text="🔑 AI Key সেটআপ করুন...", fg="#f9a825")
            APIKeySetupWindow()
            return
        self.status.config(text="Banglish → বাংলা হচ্ছে...", fg="#f9a825")
        self.root.update()
        def do_convert():
            try:
                prompt = f"""Convert the following Banglish (Bengali written in English letters) to proper Bengali script.
Example: "ami tomake bhalobashi" → "আমি তোমাকে ভালোবাসি"
IMPORTANT: Return ONLY the Bengali script text, nothing else.

Banglish text: {text}

Bengali script:"""
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                data = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                    "temperature": 0.1
                }
                r = requests.post(url, headers=headers, json=data, timeout=15)
                if r.status_code == 200:
                    result = r.json()["choices"][0]["message"]["content"].strip()
                    self.root.after(0, lambda: self._show_result(result))
                    self.root.after(0, lambda: self.status.config(text="Banglish to Bengali done!", fg="#00C853"))
                else:
                    err = str(r.status_code)
                    emsg = "VPN বন্ধ করে আবার চেষ্টা করুন!" if err == "403" else f"Error: {err}"
                    self.root.after(0, lambda: self.status.config(text=emsg, fg="#F42A41"))
            except Exception as e:
                err = str(e)[:40]
                self.root.after(0, lambda: self.status.config(text=err, fg="#F42A41"))
        import threading
        threading.Thread(target=do_convert, daemon=True).start()

    def _bn_to_en(self): self._translate("bn","en")
    def _en_to_bn(self): self._translate("en","bn")

    def _zoom_in(self):
        if self.editor_font_size < 20:
            self.editor_font_size += 1
            self.txt.config(font=("Segoe UI", self.editor_font_size))

    def _zoom_out(self):
        if self.editor_font_size > 8:
            self.editor_font_size -= 1
            self.txt.config(font=("Segoe UI", self.editor_font_size))

    def _paste(self):
        try:
            text = pyperclip.paste()
            self.txt.delete("1.0","end")
            self.txt.insert("1.0", text)
        except:
            pass

    def _polish(self):
        text = self.txt.get("1.0","end").strip()
        if not text:
            self.status.config(text="⚠️ কোনো লেখা নেই!", fg="#F42A41")
            return
        if not GROQ_API_KEY:
            self.status.config(text="🔑 AI Key সেটআপ করুন...", fg="#f9a825")
            APIKeySetupWindow()
            return
        self.status.config(text="⟳ AI সাজাচ্ছে...", fg="#f9a825")
        self.root.update()
        def do_polish():
            try:
                lang = self.lang_var.get()
                result = ai_polish_text(text, lang)
                if result == "__ERROR_403__":
                    self.root.after(0, lambda: self.status.config(text="VPN বন্ধ করে আবার চেষ্টা করুন!", fg="#F42A41"))
                elif result == "__ERROR__":
                    self.root.after(0, lambda: self.status.config(text="Internet সমস্যা — আবার চেষ্টা করুন", fg="#F42A41"))
                elif result:
                    self.root.after(0, lambda: self._show_result(result))
                    self.root.after(0, lambda: self.status.config(text="✓ সম্পন্ন!", fg="#00C853"))
                else:
                    self.root.after(0, lambda: self.status.config(text="সমস্যা হয়েছে", fg="#F42A41"))
            except Exception as e:
                self.root.after(0, lambda: self.status.config(text=f"⚠️ {str(e)[:40]}", fg="#F42A41"))
        import threading
        threading.Thread(target=do_polish, daemon=True).start()
    def _show_result(self, result):
        self.txt.delete("1.0","end")
        self.txt.insert("1.0", result)
        self.status.config(text="✓ AI সাজানো সম্পন্ন!", fg="#00C853")

    def _copy(self):
        text = self.txt.get("1.0","end").strip()
        if text:
            pyperclip.copy(text)
            self.status.config(text="✓ Clipboard-এ copy হয়েছে!", fg="#00C853")

    def run(self):
        self.root.mainloop()


def bijoy_to_unicode(text):
    """Proper Bijoy ANSI to Unicode converter with kar reordering"""
    # Step 1: Direct character mappings (longest first to avoid partial matches)
    # Conjuncts and special combinations first
    conjuncts = [
        ("¯‹", "স্ক"), ("¯’", "স্থ"), ("¯Í", "স্ত"), ("¯ú", "স্প"), ("¯^", "স্ব"), ("¯§", "স্ম"),
        ("š¿", "ন্ত্র"), ("›¿", "ন্ত্র"), ("šÍ", "ন্ত"), ("›`", "ন্দ"), ("Û", "ন্ড"), ("Ê", "ন্ট"),
        ("¤ú", "ম্প"), ("¤^", "ম্ব"), ("¤§", "ম্ম"), ("¤¢", "ম্ভ"),
        ("¶", "ক্ষ"), ("ÿ", "ক্ষ"), ("²", "ত্ত"), ("£", "ট্ট"),
        ("Œ", "ৌ"), ("•", "ক্স"), ("ž", "ঞ্জ"), ("Ý", "ন্স"), ("‚", "ষ্ণ"),
        ("é", "হ্ন"), ("ý", "হ্ম"), ("`¦", "দ্ব"), ("˜", "দ্ব"), ("™", "দ্দ"),
        ("×", "ত্র"), ("Ÿ", "্য"), ("¨", "্য"), ("ª", "্র"), ("Ö", "্র"),
        ("ò", "ষ্ণ"), ("ó", "ষ্ট"), ("ô", "ষ্ঠ"), ("¦", "্ব"), ("~", "ূ"),
        ("¡", "ু"), ("…", "ৃ"),
    ]
    for a, u in conjuncts:
        text = text.replace(a, u)

    # Step 2: Main character map
    charmap = {
        # Vowels (independent)
        "A": "অ", "Av": "আ", "B": "ই", "C": "ঈ", "D": "উ", "E": "ঊ",
        "F": "ঋ", "G": "এ", "H": "ঐ", "I": "ও", "J": "ঔ",
        # Consonants
        "K": "ক", "L": "খ", "M": "গ", "N": "ঘ", "O": "ঙ",
        "P": "চ", "Q": "ছ", "R": "জ", "S": "ঝ", "T": "ঞ",
        "U": "ট", "V": "ঠ", "W": "ড", "X": "ঢ", "Y": "ণ",
        "Z": "ত", "_": "থ", "`": "দ", "a": "ধ", "b": "ন",
        "c": "প", "d": "ফ", "e": "ব", "f": "ভ", "g": "ম",
        "h": "য", "i": "র", "j": "ল", "k": "শ", "l": "ষ",
        "m": "স", "n": "হ", "o": "ড়", "p": "ঢ়", "q": "য়",
        "r": "ৎ", "s": "ং", "t": "ঃ", "u": "ঁ",
        # Kar (dependent vowels)
        "v": "া", "w": "ি", "x": "ী", "y": "ু", "z": "ূ",
        "…": "ৃ", "‡": "ে", "Š": "ৈ", "†": "ো",
        # Special
        "&": "্",  # hasanta
        "/": "্",
        # Numbers
        "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪",
        "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯",
        # Punctuation
        "|": "।",
        # Ref (র্) marker — handled in post-step, placed before preceding consonant
        "©": "\uE000",
    }
    # Apply 2-char first (Av), then 1-char
    result = []
    i = 0
    while i < len(text):
        two = text[i:i+2]
        if two in charmap:
            result.append(charmap[two])
            i += 2
        elif text[i] in charmap:
            result.append(charmap[text[i]])
            i += 1
        else:
            result.append(text[i])
            i += 1
    converted = "".join(result)

    # Step 2b: Ref (র্) — marker \uE000 comes AFTER its consonant in Bijoy,
    # but in Unicode র্ goes BEFORE the consonant. Move "র্" before preceding consonant cluster.
    if "\uE000" in converted:
        chars2 = list(converted)
        res2 = []
        k = 0
        while k < len(chars2):
            if chars2[k] == "\uE000":
                # The ref attaches to the consonant just placed in res2.
                # Insert "র" + hasanta before that consonant cluster.
                if res2:
                    # find start of the last consonant cluster in res2
                    pos = len(res2) - 1
                    # walk back over hasanta-joined clusters
                    while pos > 0 and res2[pos-1] == "্":
                        pos -= 2
                    res2.insert(max(pos,0), "র্")
                k += 1
            else:
                res2.append(chars2[k])
                k += 1
        converted = "".join(res2)

    # Step 3: Reorder pre-base kar (ি ে ৈ come BEFORE consonant in Bijoy, AFTER in Unicode)
    # Pattern: kar + consonant => consonant + kar
    pre_kars = ["ি", "ে", "ৈ"]
    chars = list(converted)
    out = []
    j = 0
    while j < len(chars):
        if chars[j] in pre_kars and j+1 < len(chars):
            # This kar should come after the next consonant cluster
            kar = chars[j]
            j += 1
            # Collect the consonant cluster (consonant + any hasanta combos)
            cluster = chars[j]
            j += 1
            # Handle conjunct: if next is hasanta, keep collecting
            while j < len(chars) and chars[j] == "্" and j+1 < len(chars):
                cluster += chars[j] + chars[j+1]
                j += 2
            out.append(cluster)
            out.append(kar)
        else:
            out.append(chars[j])
            j += 1
    return "".join(out)


def insert_text(text):
    """Insert text - restore focus then paste"""
    print(f"[BTN] Inserting: {repr(text)}")
    try:
        import ctypes
        # Restore previous window focus
        if _prev_hwnd:
            ctypes.windll.user32.SetForegroundWindow(_prev_hwnd)
            time.sleep(0.2)
        # Save clipboard
        try:
            old_clip = pyperclip.paste()
        except:
            old_clip = ""
        # Paste character
        pyperclip.copy(text)
        time.sleep(0.15)
        keyboard.press_and_release("ctrl+v")
        time.sleep(0.2)
        # Restore clipboard
        try:
            if old_clip:
                pyperclip.copy(old_clip)
        except:
            pass
        print(f"[BTN] Done!")
    except Exception as e:
        print(f"[!] insert_text error: {e}")


def convert_numbers(text, lang):
    """Convert Arabic numerals to Bengali, and number words"""
    if lang == "bn":
        # Convert Arabic digits to Bengali digits
        result = ""
        for ch in text:
            result += BN_DIGITS.get(ch, ch)
        text = result
        # Convert Bengali number words to Bengali digits (optional - keep words)
        # Not converting words to digits - keep "এক দুই তিন" as words
    return text


def transcribe(path,lang):
    import speech_recognition as sr
    r=sr.Recognizer()
    r.energy_threshold=200
    r.dynamic_energy_threshold=True
    r.operation_timeout=8
    with sr.AudioFile(path) as src:
        r.adjust_for_ambient_noise(src,duration=0.2)
        audio=r.record(src)
    gl="bn-BD" if lang=="bn" else "en-US"
    print(f"[LANG] {gl}")
    try:
        text=r.recognize_google(audio,language=gl)
        text = apply_punct(text,lang)
        text = convert_numbers(text,lang)
        return text
    except sr.UnknownValueError:
        if GROQ_API_KEY:
            return transcribe_groq(path,lang)
        return ""
    except sr.RequestError:
        if GROQ_API_KEY:
            return transcribe_groq(path,lang)
        raise Exception("Internet সংযোগ সমস্যা")

def transcribe_groq(path,lang):
    url="https://api.groq.com/openai/v1/audio/transcriptions"
    headers={"Authorization":f"Bearer {GROQ_API_KEY}"}
    with open(path,"rb") as f:
        files={"file":("audio.wav",f,"audio/wav")}
        data={"model":"whisper-large-v3-turbo","response_format":"json",
              "prompt":"বাংলা ও English মিশিয়ে কথা বলা হচ্ছে।"}
        r=requests.post(url,headers=headers,files=files,data=data,timeout=30)
    if r.status_code==200:
        return apply_punct(r.json().get("text","").strip(),lang)
    raise Exception(f"Groq Error {r.status_code}")

def process_recording():
    global audio_frames
    # Show processing immediately
    if indicator_win:
        indicator_win.safe(indicator_win.show_processing)
    if not audio_frames:
        if indicator_win:
            indicator_win.safe(indicator_win.show_error,"কোনো অডিও পাওয়া যায়নি")
        return
    audio=np.concatenate(audio_frames,axis=0)
    volume=np.abs(audio).mean()
    print(f"[DEBUG] Volume: {volume:.6f}")
    if volume<0.0005:
        if indicator_win:
            indicator_win.safe(indicator_win.show_error,"কিছু শোনা যায়নি")
        return
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav",delete=False) as tmp:
            tmp_path=tmp.name
        save_wav(audio_frames,tmp_path)
        text=transcribe(tmp_path,current_lang)
        # AI Polish if enabled
        if ai_polish_mode and text:
            if indicator_win:
                indicator_win.safe(indicator_win.show_ai_polish)
            polished = ai_polish_text(text, current_lang)
            if polished not in ("__ERROR__", "__ERROR_403__") and polished:
                text = polished
            # else keep original text (polish failed, but still paste what we heard)
        if should_contribute() and text:
            log_voice_data(tmp_path,text)
        os.unlink(tmp_path)
        if text:
            time.sleep(0.2)
            global _saved_clipboard
            try:
                _saved_clipboard = pyperclip.paste()
            except:
                _saved_clipboard = ""
            pyperclip.copy(text)
            print(f"[✓] Ready to paste: {text[:30]}")
            if indicator_win:
                indicator_win.safe(indicator_win.show_click_paste, text)
            if toolbar_win:
                toolbar_win.update_status("● প্রস্তুত", "#00C853")
            print(f"[✓] {text}")
        else:
            indicator_win.safe(indicator_win.show_error,"কিছু শোনা যায়নি")
            if toolbar_win:
                toolbar_win.update_status("● প্রস্তুত", "#00C853")
    except Exception as e:
        print(f"[✗] {e}")
        indicator_win.safe(indicator_win.show_error,str(e)[:40])

def _start_mic_stream():
    """প্রতিবার recording-এর সময় নতুন fresh mic stream খোলে।
    এতে mic busy/sleep থেকে ফেরার পরও সবসময় কাজ করে।"""
    global mic_stream
    _stop_mic_stream()  # পুরনো কিছু থাকলে আগে বন্ধ
    try:
        mic_stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                    dtype="float32", callback=audio_callback,
                                    blocksize=1024)
        mic_stream.start()
        return True
    except Exception as e:
        print(f"[✗] Mic খুলতে সমস্যা: {e}")
        mic_stream = None
        # শেষ চেষ্টা: default device reset করে আবার
        try:
            sd._terminate(); sd._initialize()
            mic_stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                                        dtype="float32", callback=audio_callback,
                                        blocksize=1024)
            mic_stream.start()
            print("[✓] Mic পুনরায় চালু হলো")
            return True
        except Exception as e2:
            print(f"[✗] Mic reset ব্যর্থ: {e2}")
            mic_stream = None
            return False

def _stop_mic_stream():
    global mic_stream
    if mic_stream is not None:
        try:
            mic_stream.stop()
            mic_stream.close()
        except Exception:
            pass
        mic_stream = None

def toggle_recording(lang="bn"):
    global is_recording,audio_frames,current_lang,_last_toggle_time
    now=time.time()
    if now-_last_toggle_time<0.5:
        return
    _last_toggle_time=now
    if not is_recording:
        current_lang=lang
        audio_frames=[]
        # নতুন fresh mic stream খোলো — mic আটকে গেলেও এতে ঠিক হয়ে যায়
        if not _start_mic_stream():
            if indicator_win:
                indicator_win.safe(indicator_win.show_error,"মাইক্রোফোন চালু করা যায়নি")
            if toolbar_win:
                toolbar_win.update_status("● প্রস্তুত", "#00C853")
            return
        is_recording=True
        # Save active window before recording
        global _prev_hwnd
        try:
            import ctypes
            _prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
            print(f"[WIN] Saved hwnd: {_prev_hwnd}")
        except:
            pass
        if indicator_win:
            indicator_win.safe(indicator_win.show_recording,lang)
        if toolbar_win:
            toolbar_win.update_mode(lang)
        print(f"[🎤] রেকর্ডিং শুরু... [{'বাংলা 🟢' if lang=='bn' else 'English 🔵'}]")
    elif current_lang==lang:
        is_recording=False
        _stop_mic_stream()  # stream বন্ধ করো, পরের বার fresh খুলবে
        print("[⏹] রেকর্ডিং শেষ...")
        # Reset toolbar status/buttons
        if toolbar_win:
            toolbar_win.update_status("⟳ প্রসেসিং...", "#f9a825")
        threading.Thread(target=process_recording,daemon=True).start()


# ─── TRAY ─────────────────────────────────────
def quit_app(icon,item):
    global app_running
    app_running=False
    icon.stop()
    indicator_win.root.after(0,indicator_win.root.destroy)

def show_toolbar(icon,item):
    if toolbar_win:
        toolbar_win.root.after(0,toolbar_win.show)

def setup_tray():
    img=Image.new("RGBA",(64,64),(0,0,0,0))
    d=ImageDraw.Draw(img)
    d.ellipse([4,4,60,60],fill="#006A4E")
    d.ellipse([16,16,48,48],fill="#F42A41")
    menu=pystray.Menu(
        pystray.MenuItem(f"{LOGO} {APP_EN} v{VERSION}",None,enabled=False),
        pystray.MenuItem(f"বাংলা: {HOTKEY_BN.upper()} / {HOTKEY_BN_ALT.upper()}",None,enabled=False),
        pystray.MenuItem(f"English: {HOTKEY_EN.upper()} / {HOTKEY_EN_ALT.upper()}",None,enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Toolbar দেখাও",show_toolbar),
        pystray.MenuItem("বন্ধ করো",quit_app),
    )
    icon = pystray.Icon(APP_EN,img,APP_EN,menu)
    icon.default_action = show_toolbar
    return icon

def setup_autostart():
    try:
        import winreg
        key=winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Run",
                           0,winreg.KEY_SET_VALUE)
        pythonw = sys.executable.replace('python.exe','pythonw.exe')
        winreg.SetValueEx(key,APP_EN,0,winreg.REG_SZ,
                          f'"{pythonw}" "{os.path.abspath(__file__)}"')
        winreg.CloseKey(key)
        print("[✓] Auto-startup সেট হয়েছে")
    except Exception as e:
        print(f"[!] Auto-startup: {e}")

def hotkey_listener():
    # মূল hotkey + বিকল্প hotkey — দুটোই register করি, যাতে একটা দখল হলেও অন্যটা চলে
    def _reg(suppress):
        keyboard.add_hotkey(HOTKEY_BN,lambda:toggle_recording("bn"),suppress=suppress)
        keyboard.add_hotkey(HOTKEY_EN,lambda:toggle_recording("en"),suppress=suppress)
        # বিকল্প — আলাদা try, যাতে একটা fail করলেও বাকিগুলো register হয়
        try: keyboard.add_hotkey(HOTKEY_BN_ALT,lambda:toggle_recording("bn"),suppress=suppress)
        except: pass
        try: keyboard.add_hotkey(HOTKEY_EN_ALT,lambda:toggle_recording("en"),suppress=suppress)
        except: pass

    registered = False
    try:
        _reg(True)
        registered = True
    except Exception as e:
        print(f"[!] Hotkey (suppress) সমস্যা: {e} — fallback চেষ্টা")
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass
        try:
            _reg(False)
            registered = True
        except Exception as e2:
            print(f"[!] Hotkey register ব্যর্থ: {e2}")
    if registered:
        print(f"[\u2713] বাংলা: {HOTKEY_BN.upper()} (বা {HOTKEY_BN_ALT.upper()})")
        print(f"[\u2713] English: {HOTKEY_EN.upper()} (বা {HOTKEY_EN_ALT.upper()})")
    while app_running:
        time.sleep(0.5)


# ─── MAIN ─────────────────────────────────────
def start_app():
    global indicator_win,toolbar_win

    # Mic এখন প্রতি recording-এ আলাদা খোলা হয় (_start_mic_stream), একটানা নয়
    try:
        mic_name = sd.query_devices(sd.default.device[0])['name']
        print(f"[✓] Mic: {mic_name}")
    except Exception as e:
        print(f"[!] Mic check: {e}")
    setup_autostart()

    indicator_win=IndicatorWindow()
    toolbar_win=ToolbarWindow()

    threading.Thread(target=hotkey_listener,daemon=True).start()
    tray=setup_tray()
    threading.Thread(target=tray.run,daemon=True).start()

    indicator_win.root.after(500,indicator_win.show_idle)
    indicator_win.root.after(4000,indicator_win.root.withdraw)

    print(f"[✓] {LOGO} {APP_EN} v{VERSION} চালু!")
    print(f"    {HOTKEY_BN.upper()} = বাংলা | {HOTKEY_EN.upper()} = English\n")
    indicator_win.run()
    _stop_mic_stream()


def main():
    instance_lock=check_single_instance()
    print("="*50)
    print(f"  {LOGO} {APP_EN} v{VERSION}")
    print(f"  {APP_NAME}")
    print("="*50)

    def run_app():
        if is_first_run():
            print("[→] প্রথমবার — Welcome screen...")
            WelcomeScreen(on_done=start_app).run()
        else:
            start_app()

    # Run with crash recovery
    while True:
        try:
            run_app()
            break
        except Exception as e:
            print(f"[!] Crash: {e} — restarting...")
            time.sleep(2)
            # Reset state
            global is_recording, audio_frames, indicator_win, toolbar_win
            is_recording = False
            audio_frames = []
            indicator_win = None
            toolbar_win = None


if __name__=="__main__":
    main()
