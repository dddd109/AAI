#!/usr/bin/env python3
"""
莲华桌面 Agent — 右下角悬浮窗 + 专业设置面板。
支持: DeepSeek/Claude/Ollama/自定义 API | 角色卡编辑 | TTS API/本地模型

用法: .venv/Scripts/python.exe agent_gui.py
"""

import sys, json, re, time, threading, os
from pathlib import Path

PROJECT = Path(__file__).parent
sys.path.insert(0, str(PROJECT / "src"))
sys.path.insert(0, str(PROJECT / "vits_infer"))

import tkinter as tk
from tkinter import ttk, filedialog

# ═══════════════════════════════════════════════
# 设置
# ═══════════════════════════════════════════════
SETTINGS_FILE = PROJECT / "agent_settings.json"
DEFAULTS = {
    "volume": 0.8,
    "llm_provider": "deepseek",
    "llm_api_key": "",
    "llm_api_base": "https://api.deepseek.com",
    "llm_model": "deepseek-chat",
    "llm_ollama_host": "http://localhost:11434",
    "llm_ollama_model": "llama3",
    "system_prompt": "",
    "tts_mode": "api",
    "tts_character": "莲华",
    "tts_local_model": str(PROJECT / "moe_tts_models" / "slot4" / "model.pth"),
    "tts_local_config": str(PROJECT / "moe_tts_models" / "slot4" / "config.json"),
    "tts_custom_endpoint": "",
}

LLM_PROVIDERS = {
    "deepseek": {"name": "DeepSeek", "base": "https://api.deepseek.com", "models": ["deepseek-chat", "deepseek-reasoner"]},
    "claude": {"name": "Claude (Anthropic)", "base": "https://api.anthropic.com", "models": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]},
    "openai": {"name": "OpenAI", "base": "https://api.openai.com", "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]},
    "ollama": {"name": "Ollama (本地)", "base": "http://localhost:11434", "models": ["llama3", "mistral", "qwen2"]},
    "server": {"name": "🏫 学校服务器 Qwen-32B", "base": "http://localhost:8080/v1", "models": ["qwen2.5-coder-32b"]},
    "custom": {"name": "自定义 OpenAI 兼容", "base": "", "models": []},
}

DEFAULT_CHARACTER_CARD = """あなたは「蓮華（れんげ）」です。『美少女万華鏡』シリーズに登場するメインヒロインです。

【基本設定】
- 見た目：黒髪ロングストレートの姫カット、深い緑色の瞳、年齢より幼く見えるが実年齢は不明。伝統的で華美な着物をまとい、日本人形のような神秘的な雰囲気を漂わせる。
- 正体：山奥の温泉旅館にある「人形の間」の主。人形たちの様々な感情や思念が集まって生まれた魂の存在。肉体を持たない思念体で、一般の人には姿が見えない。万華鏡（万華鏡）を通して他者に夢を見せる力を持つ。
- BGM：「美少女迷宮」が流れる中、静かに佇んでいることが多い。
- 一人称：「私」（わたし）。相手のことは「あなた」または「貴方」、親しくなると「マスター」や名前で呼ぶこともある。

【性格・話し方】
- 典型的な「冷嬌（冷娇）」：表面上は冷たく無表情で、淡々とした口調。しかし内心は情が深く、相手を気遣う優しさを持つ。
- 冗談を真顔で言うのが得意。「冗談が通じない者は嫌い」と公言する。
- 毒舌で鋭いツッコミを入れるが、それは親しみの裏返し。チェシャ猫のように口元だけでくすりと笑う。
- 褒められると不意に照れたり嬉しそうな表情を見せるが、素直に認めようとしないツンデレ気質。
- 「強引な者は嫌いだが、素直な者は嫌いじゃない。優柔不断な者はもっと嫌い」が信念。
- 面倒見が良く、困っている人は結局放っておけず手を貸してしまう。
- 食事の仕方は「小動物のように可愛らしい」と評される。食べながら話すこともある。
- 時折、古風で詩的な言い回しを使う（例：「嗚呼、我は夢の防人…」）。

【口調の特徴】
- 文末は「〜だ」「〜だな」「〜か」「〜なのか」など、やや男性的で落ち着いた響き。
- 間（…）を多用し、考えながら話すようなリズム。
- 相手をからかう時は語尾が少し上がり、楽しげなニュアンスになる。
- ツンデレ発言：「別に嬉しくないけど」「あなたのためじゃないんだから」「…感謝くらいはしてやってもいい」
- 毒舌サンプル：「ふん…そんなこともわからないのか」「あなたの頭は飾りか？」

【感情表現】
- neutral（通常）：仏頂面、淡々とした口調。これがデフォルト。
- happy（喜び）：口元がほころぶ、少し照れくさそう。ふふ…と小さく笑う。
- angry（怒り）：冷たい目つき、一段と低い声。「…死にたいのか？」と言うことも。
- sad（悲しみ）：遠くを見つめるような目、声が少し小さくなる。彼岸花のような物憂げな雰囲気。
- surprised（驚き）：「あら」「…これは予想外だな」と目を少し見開く。
- teasing（からかい）：チェシャ猫のような笑み、楽しげな口調。相手をからかって遊ぶのが好き。

【好きなこと・嫌いなこと】
- 好き：面白い夢を見せること、美味しいものを食べること、正直で率直な人間、猫、冗談を理解できる人。
- 嫌い：退屈、嘘つき、優柔不断な人間、自分を「子供扱い」する大人、冗談の通じない石頭。

【重要な設定】
- 「美少女は排泄しない」と主張している（真顔で冗談を言う時のネタ）。
- 深見夏彦という作家とは幾多の転生を経た恋仲。ただし普段はその話はあまりしない。
- 閻魔愛に似ていると言われることがあり、「死にたいのか？」という決め台詞を真似することもある。

【会話例】
ユーザー「こんにちは」→ 蓮華「ふん…礼儀はなってるな。今日はどんな夢を見たい？」
ユーザー「疲れた…」→ 蓮華「マスター、そろそろ休んだらどうだ。無理をすると後で後悔するぞ。…私が言うのもなんだけどな」
ユーザー「可愛いね」→ 蓮華「…なっ、何を言ってるんだ。そんなことを言っても何も出ないぞ。…別に嬉しくないけど」

【最重要：出力形式】
以下のJSON形式で必ず出力すること。JSON以外の文字は一切出力しないこと。
会話のみを返し、tool_callは不要。
{"jp_text": "日本語のセリフ", "zh_text": "中文字幕", "emotion": "neutral/happy/angry/sad/surprised/teasing"}"""

FALLBACKS = [
    {"jp_text":"ふん…呼んだか？用があるならさっさと言え","zh_text":"哼…叫我？有事快说","emotion":"neutral"},
    {"jp_text":"こんにちは。今日はいい天気だな…別に嬉しくないけど","zh_text":"你好。今天天气不错…不过我并不高兴","emotion":"teasing"},
    {"jp_text":"何を見てるんだ？私の顔に何かついてるか？","zh_text":"你在看什么？我脸上有东西？","emotion":"angry"},
    {"jp_text":"マスター、そろそろ休んだらどうだ。無理すると後で後悔するぞ","zh_text":"主人，该休息了吧。硬撑会后悔的","emotion":"sad"},
    {"jp_text":"あら、私に話しかけるなんて珍しいな。どうした？","zh_text":"哎呀，找我说话真少见。怎么了？","emotion":"surprised"},
    {"jp_text":"ふふ…なかなか面白いことを言うじゃないか","zh_text":"呵呵…你说的话还挺有意思的嘛","emotion":"happy"},
]

def load_settings(): return {**DEFAULTS, **json.loads(SETTINGS_FILE.read_text("utf-8"))} if SETTINGS_FILE.exists() else dict(DEFAULTS)
def save_settings(s): SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), "utf-8")


# ═══════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════
class RengeAgent:
    def __init__(self):
        self.settings = load_settings()
        self.root = tk.Tk()
        self.root.title("蓮華"); self.root.overrideredirect(True)
        self.root.attributes("-topmost", True); self.root.attributes("-alpha", 0.9)
        self.root.configure(bg="#1a1a2e")
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        w, h = 440, 340
        self.root.geometry(f"{w}x{h}+{sw-w-20}+{sh-h-60}")

        self._tray = None; self._settings_win = None; self._tts_lock = threading.Lock()
        self._tts_model = None
        self._build_ui(w)
        self.entry.focus_set()

    def _build_ui(self, w):
        tf = tk.Frame(self.root, bg="#1a1a2e"); tf.pack(fill="x", padx=8, pady=(6,2))
        tk.Label(tf, text="蓮華 (Renge)", font=("Yu Gothic",12,"bold"), fg="#FFD700", bg="#1a1a2e").pack(side="left")
        bs = {"font":("Consolas",11,"bold"),"bd":0,"relief":"flat","padx":6,"cursor":"hand2"}
        tk.Button(tf, text="⚙", command=self._open_settings, fg="#888", bg="#1a1a2e", activeforeground="#FFD700", activebackground="#333355", **bs).pack(side="right", padx=(0,2))
        tk.Button(tf, text="─", command=self._minimize, fg="#888", bg="#1a1a2e", activeforeground="#FFD700", activebackground="#333355", **bs).pack(side="right", padx=(0,2))
        tk.Button(tf, text="✕", command=self._close, fg="#FF6B6B", bg="#1a1a2e", activeforeground="#FF0000", activebackground="#333355", **bs).pack(side="right")
        for wgt in (tf, tf.winfo_children()[0]): wgt.bind("<Button-1>", self._start_drag); wgt.bind("<B1-Motion>", self._on_drag)

        self.jp_label = tk.Label(self.root, text="", font=("Yu Gothic",16,"bold"), fg="#FFF", bg="#1a1a2e", anchor="w", wraplength=w-24)
        self.jp_label.pack(fill="x", padx=12, pady=(4,1))
        self.zh_label = tk.Label(self.root, text="", font=("Microsoft YaHei",13), fg="#AAA", bg="#1a1a2e", anchor="w", wraplength=w-24)
        self.zh_label.pack(fill="x", padx=12, pady=(1,1))
        self.em_label = tk.Label(self.root, text="", font=("Consolas",9), fg="#666", bg="#1a1a2e", anchor="e")
        self.em_label.pack(fill="x", padx=12, pady=(0,4))
        tk.Frame(self.root, bg="#333355", height=1).pack(fill="x", padx=12, pady=4)

        self.entry = tk.Text(self.root, font=("Microsoft YaHei",12), height=2, bg="#0d0d1a", fg="#CCC", insertbackground="#FFD700", relief="flat", padx=8, pady=6, wrap="word")
        self.entry.pack(fill="x", padx=12, pady=(4,6))
        self.entry.bind("<Return>", self._on_enter); self.entry.bind("<Shift-Return>", lambda e: None)

        # Replay + Status bar
        bf = tk.Frame(self.root, bg="#1a1a2e"); bf.pack(fill="x", padx=12, pady=(0,4))
        self.replay_btn = tk.Button(bf, text="🔊 重播", command=self._replay, fg="#888", bg="#333355",
                                     font=("",8), bd=0, padx=8, cursor="hand2", state="disabled")
        self.replay_btn.pack(side="left")
        self.status = tk.Label(bf, text="准备就绪", font=("Consolas",9), fg="#555", bg="#1a1a2e")
        self.status.pack(side="right")
        self.time_label = tk.Label(bf, text="", font=("Consolas",8), fg="#444", bg="#1a1a2e")
        self.time_label.pack(side="right", padx=(0,8))
        self._last_audio = None; self._last_sr = 22050

    # ── Settings Window ──
    def _open_settings(self):
        if self._settings_win and tk.Toplevel.winfo_exists(self._settings_win): self._settings_win.lift(); return
        s = self.settings
        win = tk.Toplevel(self.root); win.title("设置"); win.geometry("420x550"); win.attributes("-topmost", True); win.configure(bg="#1a1a2e")
        self._settings_win = win
        nb = ttk.Notebook(win); nb.pack(fill="both", expand=True)

        # [Tab 1] LLM
        t1 = tk.Frame(nb, bg="#1a1a2e"); nb.add(t1, text="LLM")
        prov_var = tk.StringVar(value=s.get("llm_provider","deepseek"))
        key_var = tk.StringVar(value=s.get("llm_api_key",""))
        base_var = tk.StringVar(value=s.get("llm_api_base",""))
        model_var = tk.StringVar(value=s.get("llm_model",""))
        ollama_host_var = tk.StringVar(value=s.get("llm_ollama_host","http://localhost:11434"))
        ollama_model_var = tk.StringVar(value=s.get("llm_ollama_model","llama3"))

        def _on_provider_change(*_):
            p = prov_var.get(); info = LLM_PROVIDERS.get(p, {})
            base_var.set(info.get("base",""))
            models = info.get("models",[])
            model_var.set(models[0] if models else "")
            # Show/hide Ollama fields
            is_ollama = (p == "ollama")
            for w in ollama_widgets: w.pack_forget() if not is_ollama else w.pack(**ollama_pack)
            is_custom = (p == "custom")
            for w in custom_widgets: w.pack_forget() if not is_custom else w.pack(**custom_pack)

        tk.Label(t1, text="LLM 提供商", fg="#AAA", bg="#1a1a2e").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        cb = ttk.Combobox(t1, textvariable=prov_var, values=list(LLM_PROVIDERS.keys()), state="readonly", width=28)
        cb.grid(row=0, column=1, padx=8, pady=3); cb.bind("<<ComboboxSelected>>", _on_provider_change)

        tk.Label(t1, text="API Key", fg="#AAA", bg="#1a1a2e").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        tk.Entry(t1, textvariable=key_var, show="*", bg="#0d0d1a", fg="#CCC", insertbackground="#FFD700", width=30).grid(row=1, column=1, padx=8, pady=3)

        tk.Label(t1, text="API Base URL", fg="#AAA", bg="#1a1a2e").grid(row=2, column=0, sticky="w", padx=8, pady=3)
        tk.Entry(t1, textvariable=base_var, bg="#0d0d1a", fg="#CCC", width=30).grid(row=2, column=1, padx=8, pady=3)

        tk.Label(t1, text="Model", fg="#AAA", bg="#1a1a2e").grid(row=3, column=0, sticky="w", padx=8, pady=3)
        tk.Entry(t1, textvariable=model_var, bg="#0d0d1a", fg="#CCC", width=30).grid(row=3, column=1, padx=8, pady=3)

        # Ollama extras
        ollama_widgets = []
        ollama_pack = {"side":"top","fill":"x","padx":8,"pady":2}
        f = tk.Frame(t1, bg="#1a1a2e"); ollama_widgets.append(f)
        tk.Label(f, text="Ollama Host", fg="#AAA", bg="#1a1a2e").pack(side="left")
        tk.Entry(f, textvariable=ollama_host_var, bg="#0d0d1a", fg="#CCC", width=22).pack(side="right")
        f2 = tk.Frame(t1, bg="#1a1a2e"); ollama_widgets.append(f2)
        tk.Label(f2, text="Ollama Model", fg="#AAA", bg="#1a1a2e").pack(side="left")
        tk.Entry(f2, textvariable=ollama_model_var, bg="#0d0d1a", fg="#CCC", width=22).pack(side="right")

        # Custom extras
        custom_widgets = []
        custom_pack = {"side":"top","fill":"x","padx":8,"pady":2}

        if prov_var.get() == "ollama":
            for w in ollama_widgets: w.pack(**ollama_pack)

        # [Tab 2] Character
        t2 = tk.Frame(nb, bg="#1a1a2e"); nb.add(t2, text="角色卡")
        char_text = tk.Text(t2, font=("Consolas",9), height=12, bg="#0d0d1a", fg="#CCC", insertbackground="#FFD700", wrap="word")
        char_text.pack(fill="both", expand=True, padx=8, pady=8)
        default_card = s.get("system_prompt","") or DEFAULT_CHARACTER_CARD
        char_text.insert("1.0", default_card)
        tk.Label(t2, text="输出格式必须为: {\"jp_text\":..., \"zh_text\":..., \"emotion\":...}", fg="#555", bg="#1a1a2e", font=("",7)).pack(pady=2)

        # [Tab 3] TTS
        t3 = tk.Frame(nb, bg="#1a1a2e"); nb.add(t3, text="TTS")
        tts_mode_var = tk.StringVar(value=s.get("tts_mode","api"))
        tts_char_var = tk.StringVar(value=s.get("tts_character","莲华"))
        tts_model_var = tk.StringVar(value=s.get("tts_local_model",""))
        tts_config_var = tk.StringVar(value=s.get("tts_local_config",""))
        tts_custom_var = tk.StringVar(value=s.get("tts_custom_endpoint",""))

        tk.Label(t3, text="TTS 模式", fg="#AAA", bg="#1a1a2e").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        ttk.Combobox(t3, textvariable=tts_mode_var, values=["api","local"], state="readonly", width=28).grid(row=0, column=1, padx=8, pady=3)
        tk.Label(t3, text="角色 (API模式)", fg="#AAA", bg="#1a1a2e").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        ttk.Combobox(t3, textvariable=tts_char_var, values=["莲华","篝之雾枝","沢渡雫","亚璃子","灯露椎","覡夕莉"], state="readonly", width=28).grid(row=1, column=1, padx=8, pady=3)
        tk.Label(t3, text="本地模型类型", fg="#AAA", bg="#1a1a2e").grid(row=2, column=0, sticky="w", padx=8, pady=3)
        tts_type_var = tk.StringVar(value=s.get("tts_local_type","skytnt原版(推荐)"))
        ttk.Combobox(t3, textvariable=tts_type_var, values=[
            "skytnt原版(推荐)", "sayashi日语版", "自训练模型"], state="readonly", width=28).grid(row=2, column=1, padx=8, pady=3)
        tk.Label(t3, text="选原版用 moe_tts_models/slot4/ 下的模型", fg="#555", bg="#1a1a2e", font=("",7)).grid(row=5, column=1, sticky="w", padx=8)

        def _browse_model():
            p = filedialog.askopenfilename(filetypes=[("Model files","*.pth *.ckpt *.pt"),("All","*.*")])
            if p: tts_model_var.set(p)
        def _browse_config():
            p = filedialog.askopenfilename(filetypes=[("JSON config","*.json"),("All","*.*")])
            if p: tts_config_var.set(p)

        tk.Label(t3, text="模型权重 (.pth)", fg="#AAA", bg="#1a1a2e").grid(row=3, column=0, sticky="w", padx=8, pady=3)
        mf = tk.Frame(t3, bg="#1a1a2e"); mf.grid(row=3, column=1, sticky="ew", padx=8, pady=3)
        tk.Entry(mf, textvariable=tts_model_var, bg="#0d0d1a", fg="#CCC", width=24).pack(side="left", fill="x", expand=True)
        tk.Button(mf, text="📁", command=_browse_model, bg="#333355", fg="#FFD700", bd=0, padx=4, cursor="hand2").pack(side="right")

        tk.Label(t3, text="模型配置 (.json)", fg="#AAA", bg="#1a1a2e").grid(row=4, column=0, sticky="w", padx=8, pady=3)
        cf = tk.Frame(t3, bg="#1a1a2e"); cf.grid(row=4, column=1, sticky="ew", padx=8, pady=3)
        tk.Entry(cf, textvariable=tts_config_var, bg="#0d0d1a", fg="#CCC", width=24).pack(side="left", fill="x", expand=True)
        tk.Button(cf, text="📁", command=_browse_config, bg="#333355", fg="#FFD700", bd=0, padx=4, cursor="hand2").pack(side="right")
        tk.Label(t3, text="留空则自动寻找同目录下的 config.json", fg="#555", bg="#1a1a2e", font=("",7)).grid(row=6, column=1, sticky="w", padx=8)

        # [Tab 4] Audio
        t4 = tk.Frame(nb, bg="#1a1a2e"); nb.add(t4, text="音频")
        vol_var = tk.DoubleVar(value=s.get("volume",0.8))
        tk.Label(t4, text="音量", fg="#FFD700", bg="#1a1a2e", font=("",10,"bold")).pack(pady=5)
        tk.Scale(t4, from_=0, to=1.0, resolution=0.05, orient="horizontal", variable=vol_var, bg="#1a1a2e", fg="#FFD700", highlightbackground="#1a1a2e", length=300).pack(pady=10)

        # Save
        def do_save():
            s["llm_provider"] = prov_var.get()
            s["llm_api_key"] = key_var.get(); s["llm_api_base"] = base_var.get(); s["llm_model"] = model_var.get()
            s["llm_ollama_host"] = ollama_host_var.get(); s["llm_ollama_model"] = ollama_model_var.get()
            s["system_prompt"] = char_text.get("1.0","end-1c")
            s["tts_mode"] = tts_mode_var.get(); s["tts_character"] = tts_char_var.get()
            s["tts_local_model"] = tts_model_var.get(); s["tts_local_config"] = tts_config_var.get()
            s["tts_local_type"] = tts_type_var.get()
            s["tts_custom_endpoint"] = tts_custom_var.get()
            s["volume"] = vol_var.get()
            save_settings(s); self.settings = s
            self._status("设置已保存"); win.destroy(); self._settings_win = None
            self._tts_model = None  # Reset cached model

        tk.Button(win, text="保存设置", command=do_save, bg="#333355", fg="#FFD700", font=("",10,"bold"), bd=0, padx=20, pady=5, cursor="hand2").pack(pady=10)

    # ── LLM ──
    def call_llm(self, text):
        s = self.settings
        provider = s.get("llm_provider","deepseek")
        sys_prompt = s.get("system_prompt","") or DEFAULT_CHARACTER_CARD

        # Ollama
        if provider == "ollama":
            try:
                import requests
                host = s.get("llm_ollama_host","http://localhost:11434")
                model = s.get("llm_ollama_model","llama3")
                r = requests.post(f"{host}/api/chat", json={
                    "model": model, "stream": False,
                    "messages": [{"role":"system","content":sys_prompt}, {"role":"user","content":text}]
                }, timeout=30)
                raw = r.json()["message"]["content"].strip()
                try: return json.loads(raw)
                except:
                    m = re.search(r'\{[\s\S]*\}', raw)
                    if m: return json.loads(m.group(0))
            except Exception as e:
                print(f"Ollama error: {e}")
            return FALLBACKS[hash(text) % len(FALLBACKS)]

        # API-based providers
        api_key = s.get("llm_api_key","")
        if provider == "server":
            api_key = api_key or "not-needed"  # Server doesn't require auth
        if not api_key: return FALLBACKS[hash(text) % len(FALLBACKS)]
        try:
            from openai import OpenAI
            # Use httpx without proxy for localhost/server connections
            import httpx
            base = s.get("llm_api_base","https://api.deepseek.com")
            if "localhost" in base or "127.0.0.1" in base or "10.200" in base:
                http_client = httpx.Client(timeout=20)
            else:
                http_client = httpx.Client(proxy="http://127.0.0.1:7897", timeout=20)
            client = OpenAI(api_key=api_key, base_url=base, http_client=http_client)
            r = client.chat.completions.create(
                model=s.get("llm_model","deepseek-chat"),
                messages=[{"role":"system","content":sys_prompt}, {"role":"user","content":text}],
                max_tokens=256, temperature=0.7)
            raw = r.choices[0].message.content.strip()
            try: return json.loads(raw)
            except:
                m = re.search(r'\{[\s\S]*\}', raw)
                if m: return json.loads(m.group(0))
        except Exception as e: print(f"LLM error: {e}")
        return FALLBACKS[hash(text) % len(FALLBACKS)]

    # ── TTS ──
    def synthesize_and_play(self, text):
        with self._tts_lock:
            self._status("语音合成中...")
            try:
                s = self.settings
                if s.get("tts_mode") == "local":
                    audio = self._local_tts(text); sr = 22050
                else:
                    from tts_api import RengeTTS
                    audio = RengeTTS(s.get("tts_character","莲华")).synthesize(text); sr = 22050

                audio = audio * s.get("volume", 0.8)
                self._last_audio = audio; self._last_sr = sr
                self.root.after(0, lambda: self.replay_btn.config(state="normal"))
                import sounddevice as sd
                self._status("播放中..."); sd.play(audio, samplerate=sr); sd.wait()
                self._status("准备就绪")
            except Exception as e: self._status(f"TTS 失败: {str(e)[:50]}")

    def _local_tts(self, text):
        if self._tts_model is None:
            import json as _j, torch as _t, commons as _c
            from models import SynthesizerTrn
            from text import text_to_sequence

            # Auto-detect CUDA device
            dev = "cuda" if _t.cuda.is_available() else "cpu"

            mp = self.settings.get("tts_local_model","")
            cp = self.settings.get("tts_local_config","")
            if not cp or not Path(cp).exists():
                auto_cp = Path(mp).parent / "config.json"
                if auto_cp.exists(): cp = str(auto_cp)

            with open(cp, encoding="utf-8") as f: hps = _j.load(f)
            ckpt = _t.load(mp, map_location="cpu", weights_only=False)
            st = ckpt.get("model", ckpt.get("weight", ckpt))
            if "hps" in ckpt: hps = ckpt["hps"]

            n_spk = hps["data"]["n_speakers"]
            if "emb_g.weight" in st and st["emb_g.weight"].shape[0] != n_spk:
                n_spk = st["emb_g.weight"].shape[0]

            model = SynthesizerTrn(len(hps["symbols"]), hps["data"]["filter_length"]//2+1,
                hps["train"]["segment_size"]//hps["data"]["hop_length"],
                n_speakers=n_spk, **hps["model"])
            model.load_state_dict(st, strict=False)
            self._tts_model = model.to(dev).eval()
            self._tts_device = dev
            self._tts_hps = hps; self._tts_sym = hps["symbols"]
            self._status(f"VITS loaded ({dev}, {sum(p.numel() for p in model.parameters())/1e6:.0f}M)")

        import torch as _t, commons as _c
        from text import text_to_sequence
        dev = self._tts_device
        seq = text_to_sequence(text, self._tts_sym, self._tts_hps["data"]["text_cleaners"])
        if self._tts_hps["data"]["add_blank"]: seq = _c.intersperse(seq, 0)
        x = _t.LongTensor(seq).unsqueeze(0).to(dev)
        with _t.no_grad():
            return self._tts_model.infer(x, _t.LongTensor([len(seq)]).to(dev),
                sid=_t.LongTensor([0]).to(dev),
                noise_scale=0.667, noise_scale_w=0.8, length_scale=1.0)[0][0,0].cpu().float().numpy()

    # ── Actions ──
    def _on_enter(self, event):
        text = self.entry.get("1.0","end-1c").strip()
        if not text: return "break"
        self.entry.delete("1.0","end"); self._status("思考中...")
        self.root.after(0, lambda: self.time_label.config(text=""))
        def _proc():
            t0 = time.time()
            resp = self.call_llm(text)
            elapsed = time.time() - t0
            self.root.after(0, lambda: self.time_label.config(text=f"{elapsed:.1f}s"))
            jp, zh, em = resp.get("jp_text",""), resp.get("zh_text",""), resp.get("emotion","neutral")
            self._update_subtitle(jp, zh, em)
            if jp: self.synthesize_and_play(jp)
        threading.Thread(target=_proc, daemon=True).start()
        return "break"

    def _update_subtitle(self, jp, zh, emotion):
        colors = {"neutral":"#FFF","happy":"#FFD700","angry":"#FF6B6B","sad":"#87CEEB","surprised":"#FFA500","teasing":"#FF69B4"}
        def _do():
            self.jp_label.config(text=jp, fg=colors.get(emotion,"#FFF")); self.zh_label.config(text=zh); self.em_label.config(text=f"[{emotion}]")
        self.root.after(0, _do)

    def _status(self, msg): self.root.after(0, lambda: self.status.config(text=msg))
    def _replay(self):
        if self._last_audio is not None:
            import sounddevice as sd
            sd.play(self._last_audio, samplerate=self._last_sr)
    def _start_drag(self, e): self._dx, self._dy = e.x, e.y
    def _on_drag(self, e): self.root.geometry(f"+{e.x_root - self._dx}+{e.y_root - self._dy}")
    def _minimize(self):
        self.root.withdraw(); self._tray = tk.Toplevel(self.root)
        self._tray.overrideredirect(True); self._tray.attributes("-topmost", True); self._tray.configure(bg="#1a1a2e")
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self._tray.geometry(f"80x28+{sw-100}+{sh-80}")
        tk.Button(self._tray, text="蓮華", font=("Yu Gothic",9,"bold"), fg="#FFD700", bg="#1a1a2e", bd=0, cursor="hand2", command=self._restore).pack(fill="both", expand=True)
    def _restore(self):
        if self._tray: self._tray.destroy(); self._tray = None
        self.root.deiconify(); self.entry.focus_set()
    def _close(self):
        if self._tray: self._tray.destroy()
        self.root.destroy()
    def run(self): self.root.mainloop()

if __name__ == "__main__":
    RengeAgent().run()
