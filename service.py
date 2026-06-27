import os
import json
import time
import re
from datetime import datetime

# На мобильном Android этот скрипт работает как фоновая служба (без графики)
print("Фоновая служба голосового ассистента успешно запущена!")

NOTES_FILE = "notes.json"

def text_to_numbers_string(text):
    units = {"ноль": 0, "один": 1, "два": 2, "три": 3, "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8, "девять": 9}
    teens = {"десять": 10, "одиннадцать": 11, "двенадцать": 12, "тринадцать": 13, "четырнадцать": 14, "пятнадцать": 15, "шестнадцать": 16, "семнадцать": 17, "восемнадцать": 18, "девятнадцать": 19}
    tens = {"двадцать": 20, "тридцать": 30, "сорок": 40, "пятьдесят": 50}
    
    words = text.split()
    res_tokens = []
    current_number = None
    
    for w in words:
        if w in tens:
            if current_number is not None: res_tokens.append(str(current_number))
            current_number = tens[w]
        elif w in units:
            if current_number is not None and current_number in tens.values(): current_number += units[w]
            else:
                if current_number is not None: res_tokens.append(str(current_number))
                current_number = units[w]
        elif w in teens:
            if current_number is not None: res_tokens.append(str(current_number))
            current_number = teens[w]
        else:
            if current_number is not None:
                res_tokens.append(str(current_number))
                current_number = None
            res_tokens.append(w)
            
    if current_number is not None: res_tokens.append(str(current_number))
    return " ".join(res_tokens)

def handle_voice_command(command):
    # Логика команд в фоне для Android
    if "позвони" in command or "набери" in command:
        name = command.replace("позвони", "").replace("набери", "").strip()
        print(f"[СЛУЖБА ANDROID] Инициируем вызов контакта: {name}")
        return

    if any(word in command for word in ["будильник", "разбуди", "напомни"]):
        test_cmd = text_to_numbers_string(command)
        test_cmd = re.sub(r'(\d+)\s+0\s+0', r'\1 00', test_cmd)
        test_cmd = re.sub(r'(\d+)\s+0$', r'\1 00', test_cmd)

        if "через" in test_cmd:
            hours, minutes = 0, 0
            hour_match = re.search(r'через\s+(\d+)\s+(?:час|часа|часов)', test_cmd)
            if hour_match: hours = int(hour_match.group(1))
            min_match = re.search(r'(?:через|\d+\s+(?:час|часа|часов))\s+(\d+)\s+(?:минут|минуты|минуту)', test_cmd)
            if min_match: minutes = int(min_match.group(1))
            elif "минут" in test_cmd and not hour_match:
                simple_match = re.search(r'через\s+(\d+)', test_cmd)
                if simple_match: minutes = int(simple_match.group(1))

            print(f"[СЛУЖБА ANDROID] Заводим будильник через {hours} ч. {minutes} мин.")
            return

        time_match = re.search(r'(?:на|в)\s+(\d{1,2})\s+(\d{1,2})', test_cmd)
        if time_match:
            print(f"[СЛУЖБА ANDROID] Ставим точный будильник на {time_match.group(1)}:{time_match.group(2)}")
            return
        return

    if "заметка" in command:
        note_text = command.replace("заметка", "").strip()
        if note_text:
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            new_note = {"text": note_text, "date": current_time}
            notes = []
            if os.path.exists(NOTES_FILE):
                try:
                    with open(NOTES_FILE, "r", encoding="utf-8") as f: notes = json.load(f)
                except: pass
            notes.append(new_note)
            with open(NOTES_FILE, "w", encoding="utf-8") as f: json.dump(notes, f, ensure_ascii=False, indent=4)
            print(f"[СЛУЖБА ANDROID] Заметка сохранена в json: {note_text}")
        return

# Имитация бессмертного фонового цикла службы
if __name__ == "__main__":
    while True:
        # Здесь в .apk будет стоять Java-слушатель BroadcastReceiver для Bluetooth-кнопки
        time.sleep(1)
