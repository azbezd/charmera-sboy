# От USB до своего образа

Сначала проверьте [совместимость](compatibility.md). Команды выполняются из корня клонированного репозитория; нужен macOS, Python 3.9+ и libusb.

## Короткий маршрут

```text
USB + microSD
     |
     v
USB inventory --> unknown hardware? --> STOP / collect evidence
     |
     v
verify descriptors + resident-code fingerprints
     |
     v
SPI read A == SPI read B --> save private factory backup
     |
     v
exact factory SHA-256 + supported replacement LCD
     |
     v
apply bounded patches --> verify complete output SHA-256
     |
     v
DestBin.bin on microSD --> native camera updater at startup
     |
     v
two new SPI reads == intended image --> remove update file
```

Чтение выполняется **по USB через уже работающую прошивку**. Запись выполняет **штатный обновлятор с microSD**. Программатор для этого рабочего сценария не нужен; универсального восстановления мёртвой камеры по USB здесь нет.

### 1. Проверить USB без захвата камеры

Инструменты доступа к устройству сейчас поддерживают **macOS**. Python 3.9+; для чтения понадобится `libusb` (например, `brew install libusb`).

```sh
python3 tools/identify.py --usb
diskutil list external physical
```

Камера A с картой сама входит в накопитель, без меню MEMORY. Без карты наблюдался режим веб-камеры `1908:3282`. Закройте приложения, работающие с картой, перед резервным чтением.

### 2. Сделать резервную копию

Найдите **целый диск именно Buildwin Media-Player** и его размер в байтах через `diskutil info`. Подставьте реальные значения в команду ниже; `diskN` — обозначение, не готовый номер.

```sh
sudo python3 tools/backup.py --disk diskN --card-bytes SIZE_IN_BYTES
```

Ридер дополнительно проверяет единственный Buildwin-накопитель, внешний USB-диск, точный выбранный номер/размер, USB-дескрипторы и код камеры. Он сохраняет два полных чтения по 1 MiB и принимает результат только при совпадении. Пароль вводится в Terminal; скрипт не сохраняет пароль.

После завершения на macOS может потребоваться физически переподключить USB: возврат драйвера накопителя иногда завершается тайм-аутом. Это не команда стирания прошивки. [Протокол и ограничения](protocol.md).

### 3. Определить точную версию и собрать образ

```sh
python3 tools/identify.py camera-dumps/YOUR_CAPTURE/spi-flash-1MiB.bin
python3 tools/build.py camera-dumps/YOUR_CAPTURE/spi-flash-1MiB.bin --lcd replacement-st7735
```

Сборка требует **точного заводского SHA-256 образца A**, а не просто похожих строк. Не снимайте проверку хеша для другого экземпляра. Сохраните оба исходных дампа отдельно от карты камеры. Модифицированный дамп не заменяет заводской backup.

Готовый файл: `custom-firmware/builds/sboy-0.9/DestBin.bin`.

```text
SHA256 3c67c73acb5d34c85da6bd28c6edfef9179c0884505eabe53e99089624cea010
```

Дальше следуйте [порядку установки и проверки](install.md). Сборщик сам не подключается к USB и ничего не устанавливает.

