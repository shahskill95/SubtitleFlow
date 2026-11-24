# Сборка Android APK для SubtitleFlow

В этой папке находится исходный проект нативного Android-клиента. Готовый APK не включён: его нужно собрать локально в Android Studio.

## Требования

- Android Studio (актуальная стабильная версия).
- Android SDK Platform 35.
- JDK 17 (можно использовать JDK, встроенный в Android Studio).
- Android Gradle Plugin 8.7.3; совместимый Gradle 8.9.

## Сборка APK

1. Открой Android Studio.
2. Выбери **Open** и укажи папку `android` внутри SubtitleFlow.
3. Дождись синхронизации Gradle. При запросе установи Android SDK Platform 35.
4. В меню выбери **Build → Build Bundle(s) / APK(s) → Build APK(s)**.
5. После завершения нажми **Locate** в уведомлении Android Studio.
6. Debug APK будет создан по адресу `android/app/build/outputs/apk/debug/app-debug.apk`.

Debug APK предназначен для установки и тестирования. Для распространения через Google Play нужна отдельная release-сборка с подписанным ключом.

## Подключение к Windows

1. Запусти `pc/start_subtitleflow.bat` на компьютере.
2. Подключи телефон и ПК к одной доверенной частной Wi-Fi сети.
3. Скопируй полный адрес из окна Windows-приложения, включая `?key=...`.
4. Вставь адрес в Android-приложение.
5. Выбери видео, нажми «Создать русские субтитры». Готовый SRT появится в папке «Загрузки».

Android-клиент отправляет видео на Windows-компьютер; Whisper и переводчик работают на ПК. Не используй публичные Wi-Fi сети и не публикуй ссылку с временным ключом.
