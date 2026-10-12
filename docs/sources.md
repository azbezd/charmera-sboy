# Источники и авторство

СБОЙ — независимое исследование экземпляров владельца и собственные хостовые инструменты, патчи, графика и обработка изображений. Проект не связан с Kodak, RETO или Buildwin и не устанавливает подлинность торговой марки конкретного экземпляра.

Полезные предшествующие исследования и документация:

- [Project-Sirius, Khimira](https://github.com/Khimira/Project-Sirius): публичное исследование Charmera и другой исходный образ. Его бинарник не использован как совместимая прошивка нашей камеры.
- [G6ThumbCameraFirmware, CompTlg](https://github.com/CompTlg/G6ThumbCameraFirmware): отдельные варианты мини-камер и прошивок; материалы для сравнения, не замена нашего дампа.
- [Dwl_ISP, Cool2Feel](https://github.com/Cool2Feel/Dwl_ISP): исходники семейства AX32xx и протокола USB/ISP; использовались для понимания vendor-команд. Исполняемые loaders и чужой SDK в этом репозитории не распространяются.
- [USB-communication-test, QingChunm](https://github.com/QingChunm/USB-communication-test): дополнительный источник по AX327X transport.
- [Тема Elektroda о чтении похожей камеры](https://www.elektroda.com/rtvforum/topic4074083.html#21981174): исходная зацепка для чтения через USB. Адреса другой камеры не переносились без проверки.
- [Официальные инструкции Kodak/RETO Charmera](https://www.kodak.retopro.co/pages/kodak-charmera-keychain-digital-camera-quick-start-guide): поведение официального продукта; не доказательство идентичности аппаратуры образца A.
- [ST7735S datasheet v1.1, зеркало SparkFun](https://cdn.sparkfun.com/assets/9/0/2/5/8/ST7735S_v1.1.pdf): команды LCD, включая отдельные MADCTL RGB/BGR и INVON/INVOFF.
- [libusb](https://libusb.info/): внешний USB runtime, устанавливается отдельно, не включён в проект.

MIT-лицензия репозитория относится к собственному коду, документации и графике проекта. Она не предоставляет прав на закрытую заводскую прошивку, товарные знаки или сторонние материалы по ссылкам. Патч-пакет требует локальный оригинал владельца устройства; полные заводские дампы не включены.
