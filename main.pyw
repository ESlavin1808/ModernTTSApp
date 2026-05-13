import pyperclip
import customtkinter as ctk
import tkinter as tk
import asyncio
import edge_tts
import whisper
import sounddevice as sd
import numpy as np
import threading
import os
import html
import json
import re
import wave
import pygame
from datetime import datetime
from tkinter import filedialog
from pathlib import Path
from tkinterdnd2.TkinterDnD import _require as _dnd_require

# Color scheme
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_light": "#1f4068",
    "accent": "#e94560",
    "accent_secondary": "#0f3460",
    "success": "#00d9a5",
    "warning": "#ffc107",
    "text": "#ffffff",
    "text_dim": "#a0a0a0",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

APP_DIR = Path(__file__).parent
HISTORY_FILE = APP_DIR / "history.json"
SETTINGS_FILE = APP_DIR / "settings.json"
AUDIO_DIR = APP_DIR / "audio_temp"
MODELS_DIR = APP_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)

# Cleanup old temp files on startup - keep only last 3
def cleanup_audio_temp():
    try:
        files = sorted(AUDIO_DIR.glob("*.wav"), key=lambda x: x.stat().st_mtime)
        for f in files[:-3]:  # Keep last 3
            try: f.unlink()
            except: pass
    except: pass
cleanup_audio_temp()

# Security: sanitize text for SSML injection prevention
def sanitize_ssml(text):
    """Escape XML special chars to prevent SSML injection into edge-tts."""
    if not text:
        return text
    # Remove any SSML tags
    text = re.sub(r'<[^>]*>', '', text)
    # Escape XML entities
    return html.escape(text)

# Security: validate file path is within allowed directory
ALLOWED_SAVE_DIRS = [str(APP_DIR), str(Path.home())]
def is_safe_path(path, allowed_dirs=None):
    """Check if the given path is within allowed directories."""
    if allowed_dirs is None:
        allowed_dirs = ALLOWED_SAVE_DIRS
    try:
        resolved = os.path.realpath(path)
        for d in allowed_dirs:
            if resolved.startswith(os.path.realpath(d)):
                return True
        return False
    except:
        return False

os.environ["XDG_CACHE_HOME"] = str(MODELS_DIR)

# Language
LANG = {"current": "ru"}

TEXTS = {
    "ru": {
        "title": "VOICE STUDIO",
        "subtitle": "Текст <-> Речь",
        "tts": "TTS",
        "stt": "STT",
        "history": "ИСТОРИЯ",
        "ready": "Готово",
        # TTS
        "enter_text": "Введите текст для синтеза:",
        "select_voice": "Выберите голос:",
        "speed": "Скорость:",
        "normal": "Обычная",
        "slower": "Медленнее",
        "faster": "Быстрее",
        "generate": "СГЕНЕРИРОВАТЬ",
        "generating": "ГЕНЕРАЦИЯ...",
        "preview": "Предпросмотр:",
        "no_audio": "Аудио не создано",
        "audio_ready": "Аудио готово! Воспроизведите или сохраните",
        "play": "ВОСПР.",
        "stop": "СТОП",
        "duration": "Длительность:",
        "save_audio": "СОХРАНИТЬ АУДИО",
        "enter_text_warning": "Введите текст",
        "saved": "Сохранено:",
        "error": "Ошибка:",
        # STT
        "voice_recording": "Запись голоса",
        "ready_record": "Готов к записи",
        "recording": "Запись...",
        "processing": "Обработка...",
        "done": "Готово!",
        "too_short": "Слишком коротко! Говорите дольше.",
        "no_audio_detected": "Звук не обнаружен",
        "quiet": "Тихо...",
        "good_level": "Хороший уровень!",
        "start_record": "НАЧАТЬ ЗАПИСЬ",
        "stop_record": "ОСТАНОВИТЬ ЗАПИСЬ",
        "upload_audio": "ЗАГРУЗИТЬ АУДИО",
        "whisper_model": "Модель Whisper:",
        "transcription": "Транскрибация:",
        "copy_text": "КОПИРОВАТЬ",
        "save_text": "СОХРАНИТЬ ТЕКСТ",
        "copied": "Скопировано!",
        # History
        "no_history": "История пуста",
        "clear_all": "ОЧИСТИТЬ",
        "total": "Всего:",
        "items": "элементов",
        "delete": "УДАЛИТЬ",
        "play_file": "ВОСПР.",
        # Drag & Drop
        "drop_audio": "Перетащите аудиофайл сюда",
        "drop_here": "Отпустите для загрузки",
        "invalid_file": "Неподдерживаемый формат",
        "load_more": "Загрузить ещё",
    },
    "en": {
        "title": "VOICE STUDIO",
        "subtitle": "Text <-> Speech",
        "tts": "TTS",
        "stt": "STT",
        "history": "HISTORY",
        "ready": "Ready",
        # TTS
        "enter_text": "Enter text to synthesize:",
        "select_voice": "Select voice:",
        "speed": "Speed:",
        "normal": "Normal",
        "slower": "Slower",
        "faster": "Faster",
        "generate": "GENERATE SPEECH",
        "generating": "GENERATING...",
        "preview": "Preview:",
        "no_audio": "No audio generated",
        "audio_ready": "Audio ready! Play or Save",
        "play": "PLAY",
        "stop": "STOP",
        "duration": "Duration:",
        "save_audio": "SAVE AUDIO FILE",
        "enter_text_warning": "Please enter text",
        "saved": "Saved:",
        "error": "Error:",
        # STT
        "voice_recording": "Voice Recording",
        "ready_record": "Ready to record",
        "recording": "Recording...",
        "processing": "Processing...",
        "done": "Done!",
        "too_short": "Too short! Speak longer.",
        "no_audio_detected": "No audio detected",
        "quiet": "Quiet...",
        "good_level": "Good level!",
        "start_record": "START RECORDING",
        "stop_record": "STOP RECORDING",
        "upload_audio": "UPLOAD AUDIO FILE",
        "whisper_model": "Whisper Model:",
        "transcription": "Transcription:",
        "copy_text": "COPY TEXT",
        "save_text": "SAVE AS TEXT",
        "copied": "Copied!",
        # History
        "no_history": "No history yet",
        "clear_all": "CLEAR ALL",
        "total": "Total:",
        "items": "items",
        "delete": "DELETE",
        "play_file": "PLAY",
        # Drag & Drop
        "drop_audio": "Drop audio file here",
        "drop_here": "Release to upload",
        "invalid_file": "Unsupported format",
        "load_more": "Load more",
    }
}

def t(key):
    return TEXTS[LANG["current"]][key]

def load_history():
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Validate: must be list of dicts with required keys
                if not isinstance(data, list):
                    return []
                return [item for item in data if isinstance(item, dict) and "id" in item and "type" in item]
    except (json.JSONDecodeError, OSError):
        return []
    return []

def save_history(history):
    # Limit history to 500 records
    MAX_HISTORY = 500
    if len(history) > MAX_HISTORY:
        history = history[-MAX_HISTORY:]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

def load_settings():
    """Load user settings from settings.json."""
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}

def save_settings(settings):
    """Save user settings to settings.json."""
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except OSError:
        pass

class ModernTTSApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        # Register Drag & Drop support via tkdnd
        _dnd_require(self)
        self.title("Voice Studio")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        self.history = load_history()
        self.current_audio = None
        self.is_recording = False
        self.recording_data = []
        self.stream = None
        self.whisper_model = None
        self.current_tab = "tts"
        self.model_loading = False
        self.model_loaded = False
        self._whisper_model_name = None
        self._speed_debounce = None
        self._history_save_pending = False
        self._settings = load_settings()
        self._history_page = 0
        self._history_page_size = 20
        
        # Apply saved settings
        saved_lang = self._settings.get("lang", "ru")
        LANG["current"] = saved_lang if saved_lang in ("ru", "en") else "ru"
        
        # Initialize pygame mixer once
        pygame.mixer.init()
        
        self.create_ui()
        self.refresh_history()
        
        # Apply saved voice and model after UI creation
        saved_voice = self._settings.get("voice", "")
        if saved_voice and hasattr(self, 'voice_var'):
            try:
                self.voice_var.set(saved_voice)
            except: pass
        saved_model = self._settings.get("whisper_model", "")
        if saved_model and hasattr(self, 'whisper_model_var'):
            try:
                self.whisper_model_var.set(saved_model)
            except: pass
        
        # Apply saved window geometry
        saved_geo = self._settings.get("geometry", "")
        if saved_geo:
            try:
                self.geometry(saved_geo)
            except: pass
        
        # Save settings on close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        # Pre-load Whisper model in background
        self._ensure_whisper_model_async()
        
        # Global hotkeys
        self.bind("<Control-Return>", lambda e: self.generate_tts())
        self.bind("<Control-r>", lambda e: self.toggle_recording())
        self.bind("<Control-1>", lambda e: self.go_tts())
        self.bind("<Control-2>", lambda e: self.go_stt())
        self.bind("<Control-3>", lambda e: self.go_history())
    
    def _save_settings(self):
        """Save current settings to settings.json."""
        self._settings["lang"] = LANG["current"]
        if hasattr(self, 'voice_var'):
            self._settings["voice"] = self.voice_var.get()
        if hasattr(self, 'whisper_model_var'):
            self._settings["whisper_model"] = self.whisper_model_var.get()
        self._settings["geometry"] = self.geometry()
        save_settings(self._settings)
    
    def _on_close(self):
        """Save settings and close."""
        self._save_settings()
        self.destroy()
        
    def create_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=COLORS["bg_card"], corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.create_sidebar()
        
        self.content = ctk.CTkFrame(self, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.content.grid(row=0, column=1, sticky="nsew")
        
        self.tabview = ctk.CTkTabview(self.content, fg_color="transparent")
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tts_tab = self.tabview.add("TTS")
        self.stt_tab = self.tabview.add("STT")
        self.history_tab = self.tabview.add("HISTORY")
        
        self.tabview.configure(command=self.on_tab_change)
        
        self.create_tts_tab()
        self.create_stt_tab()
        self.create_history_tab()
        
        self.update_nav_buttons()
    
    def on_tab_change(self):
        tab = self.tabview.get()
        if tab == "TTS":
            self.current_tab = "tts"
        elif tab == "STT":
            self.current_tab = "stt"
        else:
            self.current_tab = "history"
        self.update_nav_buttons()
    
    def switch_lang(self):
        LANG["current"] = "en" if LANG["current"] == "ru" else "ru"
        self.refresh_ui_texts()
        self._save_settings()
    
    def refresh_ui_texts(self):
        # Update sidebar
        self.title_label.configure(text=t("title"))
        self.subtitle_label.configure(text=t("subtitle"))
        self.nav_tts.configure(text=t("tts"))
        self.nav_stt.configure(text=t("stt"))
        self.nav_history.configure(text=t("history"))
        self.lang_btn.configure(text="EN/RU" if LANG["current"] == "ru" else "RU/EN")
        
        # Update TTS tab
        self.enter_text_label.configure(text=t("enter_text"))
        self.select_voice_label.configure(text=t("select_voice"))
        self.speed_label.configure(text=t("speed"))
        self.generate_btn.configure(text=t("generate"))
        self.preview_label.configure(text=t("preview"))
        self.play_btn.configure(text=t("play"))
        self.stop_btn.configure(text=t("stop"))
        self.save_btn.configure(text=t("save_audio"))
        
        # Update STT tab
        self.voice_recording_label.configure(text=t("voice_recording"))
        self.record_btn.configure(text=t("start_record"))
        self.upload_btn.configure(text=t("upload_audio"))
        self.whisper_model_label.configure(text=t("whisper_model"))
        self.transcription_label.configure(text=t("transcription"))
        self.copy_btn.configure(text=t("copy_text"))
        self.save_text_btn.configure(text=t("save_text"))
        
        # Update History tab
        self.history_header_label.configure(text=t("history"))
        self.clear_btn.configure(text=t("clear_all"))
        
        self.refresh_history()
    
    def update_nav_buttons(self):
        self.nav_tts.configure(fg_color=COLORS["bg_light"])
        self.nav_stt.configure(fg_color=COLORS["bg_light"])
        self.nav_history.configure(fg_color=COLORS["bg_light"])
        
        if self.current_tab == "tts":
            self.nav_tts.configure(fg_color=COLORS["accent"])
        elif self.current_tab == "stt":
            self.nav_stt.configure(fg_color=COLORS["accent"])
        else:
            self.nav_history.configure(fg_color=COLORS["accent"])
    
    def create_sidebar(self):
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", pady=20, padx=15)
        
        self.title_label = ctk.CTkLabel(logo_frame, text=t("title"),
                             font=ctk.CTkFont(size=24, weight="bold"),
                             text_color="#ffffff")
        self.title_label.pack()
        
        self.subtitle_label = ctk.CTkLabel(logo_frame, text=t("subtitle"),
                               font=ctk.CTkFont(size=12),
                               text_color="#c0c0c0")
        self.subtitle_label.pack()
        
        ctk.CTkFrame(self.sidebar, height=2, fg_color=COLORS["accent"]).pack(fill="x", padx=15, pady=10)
        
        nav_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", pady=10, padx=10)
        
        self.nav_tts = ctk.CTkButton(nav_frame, text=t("tts"),
                                     command=self.go_tts,
                                     fg_color=COLORS["bg_light"],
                                     hover_color=COLORS["accent"],
                                     text_color="#ffffff",
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     height=50, corner_radius=10)
        self.nav_tts.pack(fill="x", pady=5)
        
        self.nav_stt = ctk.CTkButton(nav_frame, text=t("stt"),
                                     command=self.go_stt,
                                     fg_color=COLORS["bg_light"],
                                     hover_color=COLORS["accent"],
                                     text_color="#ffffff",
                                     font=ctk.CTkFont(size=16, weight="bold"),
                                     height=50, corner_radius=10)
        self.nav_stt.pack(fill="x", pady=5)
        
        self.nav_history = ctk.CTkButton(nav_frame, text=t("history"),
                                        command=self.go_history,
                                        fg_color=COLORS["bg_light"],
                                        hover_color=COLORS["accent"],
                                        text_color="#ffffff",
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        height=50, corner_radius=10)
        self.nav_history.pack(fill="x", pady=5)
        
        # Language switcher
        lang_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        lang_frame.pack(fill="x", pady=10, padx=10)
        
        self.lang_btn = ctk.CTkButton(lang_frame, text="EN/RU",
                                      command=self.switch_lang,
                                      fg_color=COLORS["bg_light"],
                                      hover_color=COLORS["accent"],
                                      text_color="#ffffff",
                                      font=ctk.CTkFont(size=12),
                                      height=35, corner_radius=8)
        self.lang_btn.pack()
        
        status_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        status_frame.pack(side="bottom", fill="x", pady=20, padx=15)
        
        self.status_label = ctk.CTkLabel(status_frame, text=t("ready"),
                                        text_color=COLORS["success"],
                                        font=ctk.CTkFont(size=12))
        self.status_label.pack()
    
    def go_tts(self):
        self.current_tab = "tts"
        self.tabview.set("TTS")
        self.update_nav_buttons()
    
    def go_stt(self):
        self.current_tab = "stt"
        self.tabview.set("STT")
        self.update_nav_buttons()
    
    def go_history(self):
        self.current_tab = "history"
        self.tabview.set("HISTORY")
        self.update_nav_buttons()
        
    def create_tts_tab(self):
        frame = ctk.CTkFrame(self.tts_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        
        left = ctk.CTkFrame(frame, fg_color=COLORS["bg_card"], corner_radius=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        self.enter_text_label = ctk.CTkLabel(left, text=t("enter_text"),
                           font=ctk.CTkFont(size=16, weight="bold"),
                           text_color="#ffffff")
        self.enter_text_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        self.tts_text = ctk.CTkTextbox(left, height=180, font=("Segoe UI", 13),
                                       fg_color=COLORS["bg_dark"], text_color="#ffffff",
                                       border_color=COLORS["accent_secondary"], corner_radius=10)
        self.tts_text.pack(fill="x", padx=15, pady=5)
        self.tts_text._textbox.bind("<Control-v>", self.paste_tts)
        self.tts_text._textbox.bind("<<Paste>>", self.paste_tts)
        self.tts_text._textbox.bind("<Key>", self.on_key_press)
        self._add_context_menu(self.tts_text._textbox)
        
        self.select_voice_label = ctk.CTkLabel(left, text=t("select_voice"),
                            font=ctk.CTkFont(size=14, weight="bold"),
                            text_color="#ffffff")
        self.select_voice_label.pack(anchor="w", padx=20, pady=(15, 5))
        
        self.voice_var = ctk.StringVar(value="en-US-AriaNeural")
        voices = [
            "en-US-AriaNeural", "en-US-GuyNeural", "en-US-JennyNeural",
            "ru-RU-DmitryNeural", "ru-RU-SvetlanaNeural",
            "de-DE-KatjaNeural", "fr-FR-DeniseNeural", "es-ES-ElviraNeural"
        ]
        self.voice_menu = ctk.CTkOptionMenu(left, variable=self.voice_var, values=voices,
                                            fg_color=COLORS["bg_light"],
                                            button_color=COLORS["accent"],
                                            text_color="#ffffff",
                                            dropdown_fg_color=COLORS["bg_card"])
        self.voice_menu.pack(fill="x", padx=15, pady=5)
        
        self.speed_label = ctk.CTkLabel(left, text=t("speed"),
                            font=ctk.CTkFont(size=14, weight="bold"),
                            text_color="#ffffff")
        self.speed_label.pack(anchor="w", padx=20, pady=(15, 5))
        
        speed_frame = ctk.CTkFrame(left, fg_color="transparent")
        speed_frame.pack(fill="x", padx=15, pady=5)
        
        self.speed_var = ctk.DoubleVar(value=0)
        self._speed_debounce = None
        self.speed_slider = ctk.CTkSlider(speed_frame, from_=-50, to=50,
                                          variable=self.speed_var,
                                          command=self._on_speed_change,
                                          progress_color=COLORS["success"],
                                          button_color=COLORS["success"],
                                          fg_color=COLORS["bg_dark"])
        self.speed_slider.pack(side="left", fill="x", expand=True)
        
        self.speed_value_label = ctk.CTkLabel(speed_frame, text=t("normal"),
                                        text_color="#c0c0c0",
                                        font=ctk.CTkFont(size=11))
        self.speed_value_label.pack(side="left", padx=10)
        self.speed_slider.bind("<Motion>", lambda e: self.update_speed_label())
        
        self.generate_btn = ctk.CTkButton(left, text=t("generate"),
                                          command=self.generate_tts,
                                          fg_color=COLORS["success"],
                                          hover_color="#00c090",
                                          text_color="#000000",
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          height=50, corner_radius=12)
        self.generate_btn.pack(fill="x", padx=15, pady=20)
        
        right = ctk.CTkFrame(frame, fg_color=COLORS["bg_card"], corner_radius=15)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        self.preview_label = ctk.CTkLabel(right, text=t("preview"),
                            font=ctk.CTkFont(size=16, weight="bold"),
                            text_color="#ffffff")
        self.preview_label.pack(anchor="w", padx=20, pady=(20, 15))
        
        self.tts_status = ctk.CTkLabel(right, text=t("no_audio"),
                                       text_color="#c0c0c0",
                                       font=ctk.CTkFont(size=13))
        self.tts_status.pack(pady=10)
        
        self.progress = ctk.CTkProgressBar(right, width=250, height=8,
                                          progress_color=COLORS["success"],
                                          fg_color=COLORS["bg_dark"])
        self.progress.pack(pady=15)
        self.progress.set(0)
        
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        self.paste_tts_btn = ctk.CTkButton(btn_frame, text="📋 ВСТАВИТЬ",
                                           command=self.paste_tts_click,
                                           width=110, height=45,
                                           fg_color="#9C27B0",
                                           hover_color="#7B1FA2",
                                           text_color="#ffffff",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           corner_radius=10)
        self.paste_tts_btn.pack(side="left", padx=5)
        
        self.play_btn = ctk.CTkButton(btn_frame, text=t("play"),
                                       command=self.play_audio,
                                       width=110, height=45,
                                       state="disabled",
                                       fg_color="#2196F3",
                                       hover_color="#1976D2",
                                       text_color="#ffffff",
                                       font=ctk.CTkFont(size=14, weight="bold"),
                                       corner_radius=10)
        self.play_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(btn_frame, text=t("stop"),
                                      command=self.stop_audio,
                                      width=110, height=45,
                                      state="disabled",
                                      fg_color="#f44336",
                                      hover_color="#d32f2f",
                                      text_color="#ffffff",
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      corner_radius=10)
        self.stop_btn.pack(side="left", padx=5)
        
        self.duration_label = ctk.CTkLabel(right, text=f"{t('duration')} --:--",
                                           text_color="#c0c0c0",
                                           font=ctk.CTkFont(size=12))
        self.duration_label.pack(pady=5)
        
        self.save_btn = ctk.CTkButton(right, text=t("save_audio"),
                                      command=self.save_audio,
                                      width=230, height=50,
                                      state="disabled",
                                      fg_color=COLORS["warning"],
                                      hover_color="#e6ac00",
                                      text_color="#000000",
                                      font=ctk.CTkFont(size=14, weight="bold"),
                                      corner_radius=10)
        self.save_btn.pack(pady=15)
        
    def _on_speed_change(self, val):
        # Debounce: wait 50ms before updating label
        if self._speed_debounce:
            self.after_cancel(self._speed_debounce)
        self._speed_debounce = self.after(50, self._do_update_speed)
    
    def _do_update_speed(self):
        self._speed_debounce = None
        val = int(self.speed_var.get())
        if val < 0:
            self.speed_value_label.configure(text=f"{val}% ({t('slower')})")
        elif val > 0:
            self.speed_value_label.configure(text=f"+{val}% ({t('faster')})")
        else:
            self.speed_value_label.configure(text=t("normal"))
    
    # Old method kept for compatibility
    def update_speed_label(self):
        self._do_update_speed()
    
    def create_stt_tab(self):
        frame = ctk.CTkFrame(self.stt_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        
        left = ctk.CTkFrame(frame, fg_color=COLORS["bg_card"], corner_radius=15)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=10)
        
        self.voice_recording_label = ctk.CTkLabel(left, text=t("voice_recording"),
                           font=ctk.CTkFont(size=18, weight="bold"),
                           text_color="#ffffff")
        self.voice_recording_label.pack(pady=20)
        
        self.recording_label = ctk.CTkLabel(left, text=t("ready_record"),
                                            text_color="#c0c0c0",
                                            font=ctk.CTkFont(size=24))
        self.recording_label.pack(pady=20)
        
        level_frame = ctk.CTkFrame(left, fg_color="transparent")
        level_frame.pack(fill="x", padx=20, pady=10)
        
        self.level_label = ctk.CTkLabel(level_frame, text=t("no_audio_detected"),
                                        font=ctk.CTkFont(size=14),
                                        text_color="#888888")
        self.level_label.pack()
        
        self.level_bar = ctk.CTkProgressBar(level_frame, height=15,
                                            progress_color="#00d9a5",
                                            fg_color=COLORS["bg_dark"])
        self.level_bar.pack(fill="x", pady=5)
        self.level_bar.set(0)
        
        self.recording_duration_label = ctk.CTkLabel(left, text="00:00",
                                          font=ctk.CTkFont(size=16),
                                          text_color="#c0c0c0")
        self.recording_duration_label.pack(pady=5)
        
        self.whisper_model_label = ctk.CTkLabel(left, text=t("whisper_model"),
                            font=ctk.CTkFont(size=12),
                            text_color="#c0c0c0")
        self.whisper_model_label.pack(pady=(15, 5))
        
        self.whisper_model_var = ctk.StringVar(value="base")
        self.whisper_model_var.trace_add("write", self._on_model_change)
        models = ["tiny", "base", "small", "medium", "large"]
        self.model_menu = ctk.CTkOptionMenu(left, variable=self.whisper_model_var, values=models,
                                            fg_color=COLORS["bg_light"],
                                            button_color=COLORS["success"],
                                            text_color="#ffffff",
                                            dropdown_fg_color=COLORS["bg_card"])
        self.model_menu.pack()
        
        # Model loading progress
        self.model_progress_frame = ctk.CTkFrame(left, fg_color="transparent")
        self.model_progress_frame.pack(fill="x", padx=20, pady=(5, 0))
        self.model_progress_label = ctk.CTkLabel(self.model_progress_frame, text="",
                                                 font=ctk.CTkFont(size=11),
                                                 text_color="#c0c0c0")
        self.model_progress_label.pack(anchor="w")
        self.model_progress_bar = ctk.CTkProgressBar(self.model_progress_frame, height=6,
                                                     progress_color=COLORS["accent"],
                                                     fg_color=COLORS["bg_dark"])
        self.model_progress_bar.pack(fill="x", pady=(2, 0))
        self.model_progress_bar.set(0)
        self.model_progress_frame.pack_forget()  # Hidden initially
        
        self.record_btn = ctk.CTkButton(left, text=t("start_record"),
                                        command=self.toggle_recording,
                                        width=200, height=55,
                                        fg_color=COLORS["accent"],
                                        hover_color="#d13a52",
                                        text_color="#ffffff",
                                        font=ctk.CTkFont(size=16, weight="bold"),
                                        corner_radius=12)
        self.record_btn.pack(pady=20)
        
        self.upload_btn = ctk.CTkButton(left, text=t("upload_audio"),
                                        command=self.upload_audio_file,
                                        width=200, height=45,
                                        fg_color=COLORS["bg_light"],
                                        hover_color=COLORS["accent_secondary"],
                                        text_color="#ffffff",
                                        font=ctk.CTkFont(size=14),
                                        corner_radius=10)
        self.upload_btn.pack(pady=10)
        
        # Drop zone for audio files
        self.drop_zone = ctk.CTkFrame(left, fg_color=COLORS["bg_dark"], corner_radius=12,
                                      height=80, border_width=2,
                                      border_color=COLORS["accent_secondary"])
        self.drop_zone.pack(fill="x", padx=20, pady=(5, 15))
        self.drop_zone.pack_propagate(False)
        
        self.drop_label = ctk.CTkLabel(self.drop_zone, text="🎵 " + t("drop_audio"),
                                       font=ctk.CTkFont(size=13),
                                       text_color="#888888")
        self.drop_label.pack(expand=True)
        
        # Register drop target via tkdnd
        try:
            self.drop_zone.drop_target_register('DND_Files')
            self.drop_zone.dnd_bind('<<Drop>>', self._on_file_drop)
            self.drop_zone.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.drop_zone.dnd_bind('<<DragLeave>>', self._on_drag_leave)
        except:
            pass  # tkdnd not available
        
        right = ctk.CTkFrame(frame, fg_color=COLORS["bg_card"], corner_radius=15)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=10)
        
        self.transcription_label = ctk.CTkLabel(right, text=t("transcription"),
                            font=ctk.CTkFont(size=16, weight="bold"),
                            text_color="#ffffff")
        self.transcription_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        self.stt_result = ctk.CTkTextbox(right, font=("Segoe UI", 13),
                                        fg_color=COLORS["bg_dark"], text_color="#ffffff",
                                        border_color=COLORS["accent_secondary"], corner_radius=10)
        self.stt_result.pack(fill="both", expand=True, padx=15, pady=5)
        self.stt_result._textbox.bind("<Control-v>", self.paste_stt)
        self.stt_result._textbox.bind("<Key>", self.on_key_press)
        self._add_context_menu(self.stt_result._textbox)
        
        btn_frame = ctk.CTkFrame(right, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)
        
        self.paste_stt_btn = ctk.CTkButton(btn_frame, text="📋 ВСТАВИТЬ",
                                           command=self.paste_stt_click,
                                           width=140, height=40,
                                           fg_color="#9C27B0",
                                           hover_color="#7B1FA2",
                                           text_color="#ffffff",
                                           font=ctk.CTkFont(size=12, weight="bold"),
                                           corner_radius=8)
        self.paste_stt_btn.pack(side="left", padx=5)
        
        self.copy_btn = ctk.CTkButton(btn_frame, text=t("copy_text"),
                                      command=self.copy_stt,
                                      width=140, height=40,
                                      state="disabled",
                                      fg_color="#4CAF50",
                                      hover_color="#45a049",
                                      text_color="#ffffff",
                                      font=ctk.CTkFont(size=13, weight="bold"),
                                      corner_radius=8)
        self.copy_btn.pack(side="left", padx=5)
        
        self.save_text_btn = ctk.CTkButton(btn_frame, text=t("save_text"),
                                           command=self.save_stt_text,
                                           width=140, height=40,
                                           state="disabled",
                                           fg_color=COLORS["warning"],
                                           hover_color="#e6ac00",
                                           text_color="#000000",
                                           font=ctk.CTkFont(size=13, weight="bold"),
                                           corner_radius=8)
        self.save_text_btn.pack(side="left", padx=5)
        
    def create_history_tab(self):
        frame = ctk.CTkFrame(self.history_tab, fg_color="transparent")
        frame.pack(fill="both", expand=True)
        
        header = ctk.CTkFrame(frame, fg_color=COLORS["bg_card"], corner_radius=15)
        header.pack(fill="x", pady=(0, 15))
        
        self.history_header_label = ctk.CTkLabel(header, text=t("history"),
                           font=ctk.CTkFont(size=18, weight="bold"),
                           text_color="#ffffff")
        self.history_header_label.pack(side="left", padx=20, pady=15)
        
        self.history_count_label = ctk.CTkLabel(header, text=f"{t('total')} {len(self.history)} {t('items')}",
                                text_color="#c0c0c0",
                                font=ctk.CTkFont(size=12))
        self.history_count_label.pack(side="right", padx=20, pady=15)
        
        self.clear_btn = ctk.CTkButton(header, text=t("clear_all"),
                                  command=self.clear_history,
                                  width=120, height=35,
                                  fg_color="#f44336",
                                  hover_color="#d32f2f",
                                  text_color="#ffffff",
                                  font=ctk.CTkFont(size=12),
                                  corner_radius=8)
        self.clear_btn.pack(side="right", padx=10)
        
        self.history_scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        self.history_scroll.pack(fill="both", expand=True)
        
    def refresh_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()
        
        self.history_count_label.configure(text=f"{t('total')} {len(self.history)} {t('items')}")
        
        if not self.history:
            empty = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            empty.pack(fill="both", expand=True)
            lbl = ctk.CTkLabel(empty, text=t("no_history"),
                               text_color="#c0c0c0",
                               font=ctk.CTkFont(size=18))
            lbl.pack(pady=50)
            return
        
        # Reset page when refreshing
        self._history_page = 0
        self._show_history_page()
    
    def _show_history_page(self):
        """Show current page of history items."""
        # Remove load-more button if exists
        for w in self.history_scroll.winfo_children():
            if getattr(w, '_load_more_btn', False):
                w.destroy()
        
        start = self._history_page * self._history_page_size
        end = start + self._history_page_size
        items = list(reversed(self.history))[start:end]
        
        for item in items:
            self.create_history_item(item)
        
        # Add load-more button if there are more items
        total = len(self.history)
        if end < total:
            remaining = total - end
            more_frame = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            more_frame._load_more_btn = True
            more_frame.pack(fill="x", pady=10)
            more_btn = ctk.CTkButton(more_frame, text=f"{t('load_more')} ({remaining})",
                                     command=self._load_more_history,
                                     fg_color=COLORS["bg_light"],
                                     hover_color=COLORS["accent_secondary"],
                                     text_color="#ffffff",
                                     font=ctk.CTkFont(size=12),
                                     corner_radius=8)
            more_btn.pack()
    
    def _load_more_history(self):
        """Load next page of history items."""
        self._history_page += 1
        # Remove load-more button, then show next page
        for w in self.history_scroll.winfo_children():
            if getattr(w, '_load_more_btn', False):
                w.destroy()
        self._show_history_page()
    
    def create_history_item(self, item):
        card = ctk.CTkFrame(self.history_scroll, fg_color=COLORS["bg_card"], corner_radius=12)
        card.pack(fill="x", pady=5, padx=5)
        
        icon = "TTS" if item["type"] == "tts" else "STT"
        color = COLORS["success"] if item["type"] == "tts" else COLORS["accent"]
        
        badge = ctk.CTkFrame(card, width=50, fg_color=color, corner_radius=8)
        badge.pack(side="left", padx=10, pady=10)
        badge.pack_propagate(False)
        badge_lbl = ctk.CTkLabel(badge, text=icon, font=ctk.CTkFont(size=12, weight="bold"))
        badge_lbl.place(relx=0.5, rely=0.5, anchor="center")
        
        info_frame = ctk.CTkFrame(card, fg_color="transparent")
        info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        lbl = ctk.CTkLabel(info_frame, text=f"{item['date']}",
                           font=ctk.CTkFont(weight="bold", size=13),
                           text_color="#ffffff", anchor="w")
        lbl.pack(anchor="w")
        
        preview = item.get("text", item.get("transcription", ""))[:100]
        lbl2 = ctk.CTkLabel(info_frame, text=preview or "Audio file",
                           text_color="#c0c0c0", anchor="w",
                           font=ctk.CTkFont(size=11))
        lbl2.pack(anchor="w")
        
        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(side="right", padx=10, pady=10)
        
        if item.get("audio_path") and os.path.exists(item["audio_path"]):
            play_btn = ctk.CTkButton(actions, text=t("play_file"), width=60, height=35,
                                     fg_color="#2196F3",
                                     hover_color="#1976D2",
                                     text_color="#ffffff",
                                     font=ctk.CTkFont(size=12, weight="bold"),
                                     corner_radius=8,
                                     command=lambda p=item["audio_path"]: self.play_file(p))
            play_btn.pack(pady=2)
        
        del_btn = ctk.CTkButton(actions, text=t("delete"), width=60, height=35,
                                fg_color="#f44336",
                                hover_color="#d32f2f",
                                text_color="#ffffff",
                                font=ctk.CTkFont(size=12),
                                corner_radius=8,
                                command=lambda id=item["id"]: self.delete_item(id))
        del_btn.pack(pady=2)
    
    def play_file(self, path):
        if os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
            except:
                import subprocess
                subprocess.Popen(f'start "" "{path}"', shell=True)
    
    def delete_item(self, item_id):
        self.history = [h for h in self.history if h["id"] != item_id]
        self._schedule_save_history()
        self.refresh_history()
    
    def clear_history(self):
        if self.history:
            self.history = []
            self._schedule_save_history()
            self.refresh_history()
    
    def paste_tts(self, event=None):
        return self._do_paste(self.tts_text)
    
    def paste_tts_click(self):
        self._do_paste(self.tts_text)
    
    def _add_context_menu(self, widget):
        """Add right-click context menu (Cut/Copy/Paste) to a text widget."""
        menu = tk.Menu(self, tearoff=False, bg="#2d2d2d", fg="#ffffff",
                       activebackground="#404040", activeforeground="#ffffff")
        menu.add_command(label="Вырезать" if LANG["current"]=="ru" else "Cut",
                         command=lambda: (widget.event_generate("<<Cut>>"), self.focus_set()))
        menu.add_command(label="Копировать" if LANG["current"]=="ru" else "Copy",
                         command=lambda: (widget.event_generate("<<Copy>>"), self.focus_set()))
        menu.add_command(label="Вставить" if LANG["current"]=="ru" else "Paste",
                         command=lambda: (widget.event_generate("<<Paste>>"), self.focus_set()))
        
        def show_menu(event):
            menu.tk_popup(event.x_root, event.y_root)
            menu.grab_release()
        
        widget.bind("<Button-3>", show_menu, add="+")
        widget.bind("<Button-2>", show_menu, add="+")  # macOS
    
    def _do_paste(self, widget):
        try:
            text = pyperclip.paste()
            if text:
                try:
                    widget._textbox.insert("insert", text)
                except:
                    widget.insert("insert", text)
        except: pass
        return "break"
    
    def generate_tts(self):
        text = self.tts_text.get("1.0", tk.END).strip()
        if not text:
            self.tts_status.configure(text=t("enter_text_warning"), text_color=COLORS["warning"])
            return
        
        self.generate_btn.configure(state="disabled", text=t("generating"))
        self.progress.set(0)
        
        def run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                output = AUDIO_DIR / f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                
                async def progress(current, total):
                    pct = current / total if total else 0
                    self.after(0, lambda p=pct: self.progress.set(p))
                
                communicate = edge_tts.Communicate(sanitize_ssml(text), self.voice_var.get())
                communicate.progress_callback = progress
                loop.run_until_complete(communicate.save(str(output)))
                loop.close()
                
                self.current_audio = str(output)
                
                item = {
                    "id": datetime.now().strftime('%Y%m%d%H%M%S'),
                    "type": "tts",
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "text": text[:100],
                    "voice": self.voice_var.get(),
                    "audio_path": str(output)
                }
                self.history.append(item)
                self._schedule_save_history()
                
                self.after(0, self.on_tts_complete)
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self.on_tts_error(err))
        
        threading.Thread(target=run, daemon=True).start()
    
    def on_tts_complete(self):
        self.generate_btn.configure(state="normal", text=t("generate"))
        self.progress.set(1)
        self.tts_status.configure(text=t("audio_ready"), text_color=COLORS["success"])
        self.play_btn.configure(state="normal")
        self.save_btn.configure(state="normal")
        self.refresh_history()
    
    def on_tts_error(self, error):
        self.generate_btn.configure(state="normal", text=t("generate"))
        self.tts_status.configure(text=f"{t('error')}{error}", text_color="#f44336")
    
    def play_audio(self):
        if self.current_audio and os.path.exists(self.current_audio):
            try:
                pygame.mixer.music.load(self.current_audio)
                pygame.mixer.music.play()
                self.play_btn.configure(state="disabled")
                self.stop_btn.configure(state="normal")
            except Exception as e:
                self.tts_status.configure(text=f"{t('error')}{e}", text_color="#f44336")
    
    def stop_audio(self):
        try:
            pygame.mixer.music.stop()
            self.play_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
        except: pass
    
    def save_audio(self):
        if not self.current_audio:
            return
        
        file = filedialog.asksaveasfilename(
            defaultextension=".mp3",
            filetypes=[("MP3 files", "*.mp3"), ("WAV files", "*.wav"), ("All files", "*.*")],
            initialdir=str(Path.home())
        )
        
        if file:
            import shutil
            shutil.copy2(self.current_audio, file)
            self.tts_status.configure(text=f"{t('saved')}{os.path.basename(file)}", text_color=COLORS["success"])
            # Cleanup after save - keep only last 3
            cleanup_audio_temp()
    
    # STT Functions
    def paste_stt(self, event=None):
        return self._do_paste(self.stt_result)
    
    def paste_stt_click(self):
        self._do_paste(self.stt_result)
    
    def on_key_press(self, event):
        # Detect Ctrl+V by checking multiple conditions
        try:
            ctrl = hasattr(event, 'state') and (event.state & 0x4)
            
            # Detection method 1: char == control-V character (0x16)
            if ctrl and hasattr(event, 'char') and event.char == '\x16':
                self._do_paste_for_event(event)
                return "break"
            
            # Detection method 2: keysym.lower() == 'v' with Ctrl
            if ctrl and hasattr(event, 'keysym') and event.keysym.lower() == 'v':
                self._do_paste_for_event(event)
                return "break"
            
            # Detection method 3: keycode for V is 86 on most keyboards
            if ctrl and hasattr(event, 'keycode') and event.keycode == 86:
                self._do_paste_for_event(event)
                return "break"
        except:
            pass
        return None
    
    def _do_paste_for_event(self, event):
        widget = event.widget
        for w in (self.tts_text, self.stt_result):
            textbox = getattr(w, '_textbox', None)
            if widget == w or widget == textbox:
                self._do_paste(w)
                return
    
    def _ensure_whisper_model_async(self):
        """Pre-load Whisper model in background thread."""
        def show_progress(visible=True, status=""):
            if not hasattr(self, 'model_progress_frame'):
                return
            if visible:
                self.model_progress_label.configure(text=status)
                self.model_progress_bar.set(0.5)  # indeterminate-ish
                self.model_progress_frame.pack(fill="x", padx=20, pady=(5, 0), before=self.record_btn)
            else:
                self.model_progress_bar.set(0)
                self.model_progress_frame.pack_forget()
        
        def load():
            try:
                self.after(0, lambda: show_progress(True, "Loading model..."))
                model_name = self.whisper_model_var.get()
                self._whisper_model_name = model_name
                self.whisper_model = whisper.load_model(model_name, download_root=str(MODELS_DIR))
                self.model_loaded = True
                self.after(0, lambda: show_progress(False))
                self.after(0, lambda: self.recording_label.configure(
                    text=t("ready_record"), text_color="#c0c0c0"))
            except Exception as e:
                self.after(0, lambda: show_progress(False))
                self.after(0, lambda: self.recording_label.configure(
                    text=f"Model error: {e}", text_color="#f44336"))
                self.model_loaded = False
        
        threading.Thread(target=load, daemon=True).start()
    
    def _ensure_whisper_model(self):
        """Ensure model is loaded (synchronous, called from worker threads)."""
        model_name = self.whisper_model_var.get()
        # If model is not loaded or model name changed, load it
        if self.whisper_model is None or self._whisper_model_name != model_name:
            self._whisper_model_name = model_name
            self.whisper_model = whisper.load_model(model_name, download_root=str(MODELS_DIR))
        return self.whisper_model
    
    def _schedule_save_history(self):
        """Save history asynchronously (debounced, non-blocking)."""
        if self._history_save_pending:
            return
        self._history_save_pending = True
        def do_save():
            save_history(self.history)
            self._history_save_pending = False
        self.after_idle(do_save)
    
    def _on_file_drop(self, event):
        """Handle file drop event from tkdnd."""
        # Restore drop zone style
        self.drop_zone.configure(border_color=COLORS["accent_secondary"])
        self.drop_label.configure(text="🎵 " + t("drop_audio"), text_color="#888888")
        
        # Parse dropped files
        files = []
        raw = event.data
        if raw:
            # tkdnd returns files with {} wrapping or separated by space
            import re as _re
            files = _re.findall(r'\{([^}]*)\}|(\S+)', raw)
            files = [f[0] or f[1] for f in files if f[0] or f[1]]
        
        if files:
            audio_ext = ('.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac', '.wma')
            for f in files:
                if f.lower().endswith(audio_ext):
                    self.upload_audio_file(file_path=f)
                    return
        
        # No valid audio file found
        self.drop_label.configure(text="❌ " + t("invalid_file"), text_color="#f44336")
        self.after(2000, lambda: self.drop_label.configure(text="🎵 " + t("drop_audio"), text_color="#888888"))
    
    def _on_drag_enter(self, event):
        """Highlight drop zone on drag enter."""
        self.drop_zone.configure(border_color=COLORS["success"])
        self.drop_label.configure(text="📥 " + t("drop_here"), text_color=COLORS["success"])
    
    def _on_drag_leave(self, event):
        """Restore drop zone on drag leave."""
        self.drop_zone.configure(border_color=COLORS["accent_secondary"])
        self.drop_label.configure(text="🎵 " + t("drop_audio"), text_color="#888888")
    
    def _on_model_change(self, *args):
        """Called when model dropdown changes - reload model in background."""
        self._ensure_whisper_model_async()
    
    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        self.is_recording = True
        self.recording_data = []
        self.recording_start_time = datetime.now()
        self.record_btn.configure(text=t("stop_record"), fg_color=COLORS["success"])
        self.recording_label.configure(text=t("recording"), text_color="#f44336")
        
        self.update_duration()
        
        try:
            device_info = sd.query_devices(kind='input')
            samplerate = int(device_info['default_samplerate'])
            
            self.stream = sd.InputStream(samplerate=samplerate, channels=1, dtype='int16',
                                         callback=self.audio_callback)
            self.stream.start()
        except Exception as e:
            self.recording_label.configure(text=f"{t('error')}{e}", text_color="#f44336")
            self.is_recording = False
            self.record_btn.configure(text=t("start_record"), fg_color=COLORS["accent"])
    
    def update_duration(self):
        if self.is_recording:
            elapsed = datetime.now() - self.recording_start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.recording_duration_label.configure(text=f"{minutes:02d}:{seconds:02d}")
            self.after(500, self.update_duration)
    
    def audio_callback(self, indata, frames, time, status):
        if status:
            pass
        self.recording_data.append(indata.copy())
        
        audio_level = np.abs(indata).mean()
        max_level = 32768
        level_percent = min(audio_level / max_level * 100, 100)
        
        self.after(0, lambda: self.update_audio_level(level_percent))
    
    def update_audio_level(self, level):
        self.level_bar.set(level / 100)
        
        if level < 1:
            level_text = t("no_audio_detected")
            color = "#888888"
        elif level < 10:
            level_text = t("quiet")
            color = "#ffc107"
        else:
            level_text = t("good_level")
            color = "#00d9a5"
        
        self.level_label.configure(text=level_text, text_color=color)
    
    def stop_recording(self):
        self.is_recording = False
        if self.stream:
            self.stream.stop()
            self.stream = None
        
        self.record_btn.configure(text=t("start_record"), fg_color=COLORS["accent"])
        self.recording_label.configure(text=t("processing"), text_color=COLORS["warning"])
        self.level_bar.set(0)
        self.level_label.configure(text="", text_color="#c0c0c0")
        self.recording_duration_label.configure(text="00:00")
        
        if self.recording_data:
            self.process_recording()
        else:
            self.recording_label.configure(text=t("ready_record"), text_color="#c0c0c0")
    
    def process_recording(self):
        if self.model_loading:
            return
        
        self.model_loading = True
        
        def run():
            try:
                audio = np.concatenate(self.recording_data, axis=0)
                
                device_info = sd.query_devices(kind='input')
                samplerate = int(device_info['default_samplerate'])
                
                temp_wav = AUDIO_DIR / f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
                with wave.open(str(temp_wav), 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(samplerate)
                    wf.writeframes(audio.tobytes())
                
                if len(audio) < samplerate * 0.5:
                    self.after(0, lambda: self.on_stt_error(t("too_short")))
                    self.model_loading = False
                    return
                
                # Load model if not cached or model changed
                self._ensure_whisper_model()
                if self.whisper_model is None:
                    self.after(0, lambda: self.on_stt_error("Failed to load model"))
                    self.model_loading = False
                    return
                
                result = self.whisper_model.transcribe(str(temp_wav))
                
                item = {
                    "id": datetime.now().strftime('%Y%m%d%H%M%S'),
                    "type": "stt",
                    "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                    "transcription": result["text"],
                    "audio_path": str(temp_wav)
                }
                self.history.append(item)
                self._schedule_save_history()
                
                self.after(0, lambda: self.on_stt_complete(result["text"], str(temp_wav)))
                
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda err=error_msg: self.on_stt_error(err))
            finally:
                self.model_loading = False
        
        threading.Thread(target=run, daemon=True).start()
    
    def on_stt_complete(self, text, audio_path):
        self.recording_label.configure(text=t("done"), text_color=COLORS["success"])
        # Insert at cursor position, not erase everything
        self.stt_result.insert(tk.INSERT, text + " ")
        # Move cursor to end for next insertion
        self.stt_result.xview_moveto(1)
        self.copy_btn.configure(state="normal")
        self.save_text_btn.configure(state="normal")
        self.refresh_history()
    
    def on_stt_error(self, error):
        self.recording_label.configure(text=t("error"), text_color="#f44336")
        self.level_label.configure(text=error, text_color="#f44336")
    
    def upload_audio_file(self, file_path=None):
        if self.model_loading:
            return
        
        if file_path is None:
            file = filedialog.askopenfilename(
                filetypes=[("Audio files", "*.mp3 *.wav *.m4a *.flac"), ("All files", "*.*")]
            )
        else:
            file = file_path
        
        if file:
            self.model_loading = True
            self.recording_label.configure(text=t("processing"), text_color=COLORS["warning"])
            self.stt_result.delete("1.0", tk.END)
            self.stt_result.insert("1.0", "Processing audio file...")
            
            def run():
                try:
                    # Load model if not cached or model changed
                    self._ensure_whisper_model()
                    if self.whisper_model is None:
                        self.after(0, lambda: self.on_stt_error("Failed to load model"))
                        self.model_loading = False
                        return
                    
                    result = self.whisper_model.transcribe(file)
                    
                    item = {
                        "id": datetime.now().strftime('%Y%m%d%H%M%S'),
                        "type": "stt",
                        "date": datetime.now().strftime('%Y-%m-%d %H:%M'),
                        "transcription": result["text"],
                        "audio_path": file
                    }
                    self.history.append(item)
                    self._schedule_save_history()
                    
                    self.after(0, lambda: self.on_stt_complete(result["text"], file))
                    
                except Exception as e:
                    error_msg = str(e)
                    self.after(0, lambda err=error_msg: self.on_stt_error(err))
                finally:
                    self.model_loading = False
            
            threading.Thread(target=run, daemon=True).start()
    
    def copy_stt(self):
        text = self.stt_result.get("1.0", tk.END).strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.recording_label.configure(text=t("copied"), text_color=COLORS["success"])
    
    def save_stt_text(self):
        text = self.stt_result.get("1.0", tk.END).strip()
        if not text:
            return
        
        file = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialdir=str(Path.home())
        )
        
        if file:
            with open(file, "w", encoding="utf-8") as f:
                f.write(text)
            self.recording_label.configure(text=t("saved"), text_color=COLORS["success"])

if __name__ == "__main__":
    app = ModernTTSApp()
    app.mainloop()
