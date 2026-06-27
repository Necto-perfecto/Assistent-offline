import os
import json
import threading
import time
import re
from datetime import datetime

from kivy.config import Config
Config.set('kivy', 'log_level', 'info')

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.scrollview import MDScrollView
from kivymd.uix.list import MDList, TwoLineAvatarIconListItem, IconRightWidget
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivy.clock import Clock
from kivy.core.window import Window

NOTES_FILE = "notes.json"
TRIGGER_KEY_CODE = 289  # Код клавиши F8

class OfflineAssistantApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        
        self.is_recording = False
        self.vosk_loaded = False
        self.audio_stream = None
        self.rec = None
        
        screen = MDScreen()
        navigation = MDBottomNavigation()
        
        # --- ВКЛАДКА 1: ГОЛОСОВОЙ ПОМОЩНИК ---
        voice_item = MDBottomNavigationItem(name="voice_screen", text="Помощник", icon="microphone")
        voice_layout = MDBoxLayout(orientation='vertical', padding=40, spacing=25, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        
        voice_layout.add_widget(MDLabel(text="Симуляция сигнала гарнитуры", halign="center", font_style="H5", size_hint_y=None, height=40))
        
        self.voice_status = MDLabel(
            text="Статус: Загрузка Vosk...",
            halign="center",
            theme_text_color="Hint"
        )
        voice_layout.add_widget(self.voice_status)
        
        self.hint_label = MDLabel(
            text="Нажмите [F8] ОДИН РАЗ и говорите команду.\nДоступно: 'заметка...', 'позвони...', 'будильник через...'",
            halign="center",
            font_style="Caption",
            theme_text_color="Secondary"
        )
        voice_layout.add_widget(self.hint_label)
        voice_item.add_widget(voice_layout)
        
        # --- ВКЛАДКА 2: ЗАМЕТКИ ---
        notes_item = MDBottomNavigationItem(name="notes_screen", text="Заметки", icon="note-text-outline")
        notes_layout = MDBoxLayout(orientation='vertical', padding=10)
        scroll = MDScrollView()
        self.notes_list = MDList()
        scroll.add_widget(self.notes_list)
        notes_layout.add_widget(scroll)
        notes_item.add_widget(notes_layout)
        
        # --- ВКЛАДКА 3: NFC ЛОГЕР ---
        nfc_item = MDBottomNavigationItem(name="nfc_screen", text="NFC Метки", icon="nfc")
        nfc_layout = MDBoxLayout(orientation='vertical', padding=30, spacing=15, pos_hint={'center_x': 0.5, 'center_y': 0.5})
        nfc_layout.add_widget(MDLabel(text="Запись и чтение логов NFC", halign="center", font_style="H5", size_hint_y=None, height=40))
        
        self.fio_input = MDTextField(hint_text="Введите ФИО", helper_text="Например: Иванов И.И.", helper_text_mode="on_focus")
        self.id_input = MDTextField(hint_text="Введите ID", helper_text="Например: 1024", helper_text_mode="on_focus")
        nfc_layout.add_widget(self.fio_input)
        nfc_layout.add_widget(self.id_input)
        
        btn_layout = MDBoxLayout(orientation='horizontal', spacing=20, size_hint_y=None, height=50, pos_hint={'center_x': 0.5})
        btn_layout.add_widget(MDRaisedButton(text="Записать по кнопке", on_release=self.prepare_nfc_write))
        btn_layout.add_widget(MDRaisedButton(text="Считать", on_release=self.read_nfc_manual))
        
        nfc_layout.add_widget(btn_layout)
        
        self.nfc_status = MDLabel(text="Статус: Ожидание действий...", halign="center", theme_text_color="Hint")
        nfc_layout.add_widget(self.nfc_status)
        nfc_item.add_widget(nfc_layout)
        
        navigation.add_widget(voice_item)
        navigation.add_widget(notes_item)
        navigation.add_widget(nfc_item)
        screen.add_widget(navigation)
        
        Window.bind(on_key_down=self.on_keyboard_down)
        
        threading.Thread(target=self.init_vosk_backend, daemon=True).start()
        Clock.schedule_once(self.load_notes_to_ui, 1)
        return screen
    def init_vosk_backend(self):
        import vosk
        import pyaudio
        model_path = "model"
        try:
            model = vosk.Model(model_path)
            self.rec = vosk.KaldiRecognizer(model, 16000)
            p = pyaudio.PyAudio()
            self.audio_stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4000)
            self.audio_stream.start_stream()
            self.vosk_loaded = True
            Clock.schedule_once(lambda dt: self.safe_update_status("Статус: Готов. Нажмите F8"), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.safe_update_status(f"Ошибка аудио: {e}"), 0)

    def on_keyboard_down(self, window, key, scancode, codepoint, modifiers):
        if key == TRIGGER_KEY_CODE and self.vosk_loaded and not self.is_recording:
            self.is_recording = True
            self.voice_status.text = "Ассистент: Слушаю команду..."
            self.rec.Reset()
            threading.Thread(target=self.smart_record_loop, daemon=True).start()
        return True

    def smart_record_loop(self):
        time.sleep(0.3) 
        while self.is_recording:
            try:
                data = self.audio_stream.read(2000, exception_on_overflow=False)
                if len(data) > 0:
                    if self.rec.AcceptWaveform(data):
                        self.is_recording = False
                        Clock.schedule_once(lambda dt: self.safe_update_status("Обработка речи..."), 0)
                        
                        result = json.loads(self.rec.Result())
                        command = result.get("text", "").strip()
                        
                        if command:
                            Clock.schedule_once(lambda dt, c=command: self.handle_voice_command(c), 0)
                        else:
                            Clock.schedule_once(lambda dt: self.safe_update_status("Статус: Ничего не услышано"), 0)
                        break
            except: pass

    def safe_update_status(self, text):
        self.voice_status.text = text

    # Умный математический переводчик русских слов-чисел в цифры
    def text_to_numbers_string(self, text):
        units = {"ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9}
        teens = {"десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19}
        tens = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50}
        
        words = text.split()
        res_tokens = []
        
        current_number = None
        
        for w in words:
            if w in tens:
                if current_number is not None:
                    res_tokens.append(str(current_number))
                current_number = tens[w]
            elif w in units:
                if current_number is not None and current_number in tens.values():
                    current_number += units[w]
                else:
                    if current_number is not None:
                        res_tokens.append(str(current_number))
                    current_number = units[w]
            elif w in teens:
                if current_number is not None:
                    res_tokens.append(str(current_number))
                current_number = teens[w]
            else:
                if current_number is not None:
                    res_tokens.append(str(current_number))
                    current_number = None
                res_tokens.append(w)
                
        if current_number is not None:
            res_tokens.append(str(current_number))
            
        return " ".join(res_tokens)

    def handle_voice_command(self, command):
        if "позвони" in command or "набери" in command:
            name = command.replace("позвони", "").replace("набери", "").strip()
            self.voice_status.text = f"Действие: Звонок абоненту -> {name.upper()}" if name else "Ошибка: Кому позвонить?"
            return

        if any(word in command for word in ["будильник", "разбуди", "напомни"]):
            # Нормализуем фразу ("четырнадцать тридцать пять" -> "14 35", "шесть ноль ноль" -> "6 0 0")
            test_cmd = self.text_to_numbers_string(command)
            
            # Обработка "ноль ноль" или "ноль" в конце точного времени (заменяем "6 0 0" на "6 00")
            test_cmd = re.sub(r'(\d+)\s+0\s+0', r'\1 00', test_cmd)
            test_cmd = re.sub(r'(\d+)\s+0$', r'\1 00', test_cmd)

            # 1. Относительный таймер ("через Х часов", "через Х минут")
            if "через" in test_cmd:
                hours, minutes = 0, 0
                hour_match = re.search(r'через\s+(\d+)\s+(?:час|часа|часов)', test_cmd)
                if hour_match: hours = int(hour_match.group(1))
                
                min_match = re.search(r'(?:через|\d+\s+(?:час|часа|часов))\s+(\d+)\s+(?:минут|минуты|минуту)', test_cmd)
                if min_match:
                    minutes = int(min_match.group(1))
                elif "минут" in test_cmd and not hour_match:
                    simple_match = re.search(r'через\s+(\d+)', test_cmd)
                    if simple_match: minutes = int(simple_match.group(1))
                elif hour_match and not min_match:
                    tail_match = re.search(r'(?:час|часа|часов)\s+(\d+)$', test_cmd)
                    if tail_match: minutes = int(tail_match.group(1))

                if hours > 0 or minutes > 0:
                    status_text = "Действие: Будильник заведен через "
                    if hours > 0: status_text += f"{hours} ч. "
                    if minutes > 0: status_text += f"{minutes} мин."
                    self.voice_status.text = status_text.strip()
                    return

            # 2. Точное время ("на 14 35", "в 6 00")
            time_match = re.search(r'(?:на|в)\s+(\d{1,2})\s+(\d{1,2})', test_cmd)
            if time_match:
                h, m = time_match.group(1), time_match.group(2)
                m = m.zfill(2)
                self.voice_status.text = f"Действие: Будильник установлен на {h}:{m}"
                return
                
            self.voice_status.text = "Ошибка: Время будильника не распознано"
            return

        if "заметка" in command:
            note_text = command.replace("заметка", "").strip()
            if note_text: self.save_voice_note(note_text)
            return

        self.voice_status.text = f"Услышано: \"{command}\" (Команда не найдена)"

    def save_voice_note(self, text):
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        new_note = {"text": text, "date": current_time}
        notes = []
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f: notes = json.load(f)
            except: pass
        notes.append(new_note)
        with open(NOTES_FILE, "w", encoding="utf-8") as f: json.dump(notes, f, ensure_ascii=False, indent=4)
        self.load_notes_to_ui()
        self.voice_status.text = f"Добавлено: \"{text}\""

    def load_notes_to_ui(self, *args):
        self.notes_list.clear_widgets()
        if not os.path.exists(NOTES_FILE): return
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f: notes = json.load(f)
            for note in notes:
                display_date = note["date"][:16] if len(note["date"]) > 16 else note["date"]
                item = TwoLineAvatarIconListItem(text=note["text"], secondary_text=display_date)
                delete_btn = IconRightWidget(icon="delete-outline")
                delete_btn.bind(on_release=lambda x, t=note["text"], d=note["date"]: self.delete_note(t, d))
                item.add_widget(delete_btn)
                self.notes_list.add_widget(item)
        except Exception as e: print(f"Ошибка загрузки заметок: {e}")

    def delete_note(self, note_text, note_date):
        if not os.path.exists(NOTES_FILE): return
        try:
            with open(NOTES_FILE, "r", encoding="utf-8") as f: notes = json.load(f)
            notes = [n for n in notes if not (n["text"] == note_text and n["date"] == note_date)]
            with open(NOTES_FILE, "w", encoding="utf-8") as f: json.dump(notes, f, ensure_ascii=False, indent=4)
            self.load_notes_to_ui()
        except Exception as e: print(f"Ошибка удаления: {e}")

    def prepare_nfc_write(self, *args):
        fio = self.fio_input.text.strip()
        user_id = self.id_input.text.strip()
        if not fio or not user_id:
            self.nfc_status.text = "Статус: Ошибка! Заполните поля ФИО и ID"
            return
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
        log_string = json.dumps({"fio": fio, "id": user_id, "date": current_time}, ensure_ascii=False)
        self.nfc_status.text = f"Лог готов к записи на чип:\n{log_string}"

    def read_nfc_manual(self, *args):
        self.nfc_status.text = "Статус: Поиск метки... Прислоните чип цеха"

if __name__ == "__main__":
    OfflineAssistantApp().run()
