# rtwlm.kext — itlwm-режим для Realtek RTW89 (RTL8852BE и др.)

`rtwlm.kext` — это тот же RTW89-бэкенд, что и в AirportRTW, но с ethernet-фронтендом
в стиле itlwm: карта появляется в системе как сетевой интерфейс `enX`, а сканирование
и подключение выполняются через приложение HeliPort.

**Зачем это нужно:** нативный фронтенд (AirportRTW) на Sequoia 15.2+/Tahoe 26 требует
восстановления легаси-стека Wi-Fi — AMFIPass, `SecureBootModel=Disabled`, а по данным
kext.me ещё и OCLP root-патчей, слетающих с каждым обновлением macOS. rtwlm не
использует IO80211Family вообще, поэтому:

- **не нужен AMFIPass**, не нужно отключать SecureBootModel, не нужны root-патчи;
- установка — один кекст (+ HeliPort как приложение);
- переживает обновления macOS.

Поддерживаемые карты (PCI IDs в personality): RTL8851BE, RTL8852AE, RTL8852BE/BTE,
RTL8852CE, RTL8922AE.

## Сборка

Локально (Xcode 15/16, macOS):

```bash
xcodebuild -project AirportRTW.xcodeproj -target rtwlm -configuration Release build
# результат: build/Release/rtwlm/rtwlm.kext
```

Или автоматически через GitHub Actions (workflow `.github/workflows/build-rtwlm.yml`) —
артефакт `rtwlm-kext` собирается на macos-раннере при каждом пуше.

## Установка (OpenCore)

1. Скопируйте `rtwlm.kext` в `EFI/OC/Kexts/`.
2. В config.plist: Kernel → Add → добавьте `rtwlm.kext` (Enabled). **Lilu не требуется.**
3. Убедитесь, что AMFIPass не загружается и `Misc → Security → SecureBootModel`
   остаётся дефолтным — для rtwlm ничего отключать не нужно.
4. Если ранее стоял AirportRTW — уберите его из Kernel → Add (оба кекста вместе
   не должны матчить одну карту).
5. Установите HeliPort: https://github.com/OpenIntelWireless/HeliPort/releases
   (стоковый, без модификаций — он находит кекст по IOClass=`itlwm`).

### Автоподключение при загрузке (опционально)

В `rtwlm.kext/Contents/Info.plist` personality `rtwlm` поддерживает словарь
`WiFiConfig` (как в itlwm):

```xml
<key>WiFiConfig</key>
<dict>
    <key>WiFi_1</key>
    <dict>
        <key>ssid</key>
        <string>МояСеть</string>
        <key>password</key>
        <string>пароль</string>
    </dict>
</dict>
```

Без `WiFiConfig` кекст уходит в auto-join по известным сетям.

## Чек-лист тестирования на ноутбуке

1. **Загрузка кекста**: `kextstat | grep rtwlm`; в «Системной информации» →
   PCI карта должна быть занята драйвером (не `display`/none).
2. **Интерфейс**: `ifconfig` — появился `enX` с MAC-адресом карты.
3. **HeliPort**: сканирование видит сети, подключение WPA2-PSK держится,
   переподключение после выхода из диапазона.
4. **Скорость**: `iperf3` до машины в локальной сети — сравнить с Linux/Windows
   на той же точке (ожидаемо сопоставимо; tx-путь — mbuf DMA, без копий).
5. **Энергопотребление**: в HAL портированы LPS/IPS из Linux (`ps.c`), но их
   фактическую активность нужно проверить на железе:
   - `pmset -g assertions` — нет лишних assertions от enX;
   - сон/пробуждение (крышка) — Wi-Fi поднимается сам после wake;
   - скорость разряда в простое с Wi-Fi vs без.
6. **Перезагрузки и обновления**: перезагрузка; эмуляция обновления — кекст
   не должен требовать переустановки чего-либо.
7. **Паники**: если ядро падает при загрузке кекста — убрать кекст из config
   (загрузиться без него) и сохранить panic-лог из
   `/Library/Logs/DiagnosticReports/` для разбора.

## Известные ограничения

- Bluetooth-часть RTL8852BE (USB) этим кекстом не покрывается — нужен отдельный
  драйвер (как IntelBluetoothFirmware для Intel).
- WPA2-PSK подтверждён автором AirportRTW; WPA3 — проверить по чек-листу.
- Нативное меню Wi-Fi, AirDrop/Handoff — недоступны в этом режиме (это цена
  отсутствия IO80211Family).

## Авторы

- Бэкенд RTW89 и ethernet-скелет: проект AirportRTW (souissiak1-maker), форк
  архитектуры itlwm (钟先耀 / OpenIntelWireless), порт Linux-драйвера rtw89.
- rtwlm-таргет, itlwm-класс и CI: добавлены в этом репозитории
  (`tools/add_rtwlm_target.py`). Лицензия GPL-2.0.
