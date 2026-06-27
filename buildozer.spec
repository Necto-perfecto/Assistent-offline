[app]
title = Offline Assistant
package.name = offlineassistant
package.domain = org.blackview.assistant
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json

# Версия приложения
version = 1.0

# Требования к библиотекам (KivyMD, Vosk и PyAudio для Android собираются через зависимости)
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pyaudio,vosk,pyjnius

# Ориентация экрана (хоть он и будет заблокирован)
orientation = portrait

# Важнейший пункт: запрашиваем у Android 15 доступ к микрофону, контактам, звонкам, Bluetooth и NFC
android.permissions = RECORD_AUDIO, READ_CONTACTS, CALL_PHONE, BLUETOOTH, BLUETOOTH_ADMIN, BLUETOOTH_CONNECT, NFC, FOREGROUND_SERVICE, FOREGROUND_SERVICE_MICROPHONE

# Настройки целевой архитектуры Android (Blackview работает на ARM64)
android.archs = arm64-v8a

# Минимальная и целевая версии Android SDK (для Android 15)
android.minapi = 26
android.api = 34

# Включаем поддержку фоновых служб (Services), чтобы ассистент не засыпал при выключенном экране
android.services = OfflineVoiceService:service.py

# Запуск приложения в режиме Foreground (приоритет перед системой)
android.foreground_service = true
