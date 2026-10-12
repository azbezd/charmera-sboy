# Визуальные материалы

## Обложка

`assets/banner.webp` — иллюстрация бренда, созданная встроенным Image Gen. Это не снимок с камеры и не демонстрация конкретного алгоритма. Изображение сохранено в WebP; фон, крупная кириллическая типографика и один жёлтый акцент сохраняют читаемость при уменьшении.

Промпт: wide editorial GitHub banner, exact Cyrillic title «СБОЙ» and subtitle «ПРОШИВКА СО СДВИГОМ»; near-black background, ivory condensed grotesk lettering, two horizontal scanline displacements, restrained warm-yellow accent, abstract optical signal on the right; no device rendering, emoji, fake UI, rainbow neon or decorative cards.

## Примеры эффектов

`assets/effects.webp` получен скриптом `tools/render_effects_preview.py`. Исходная геометрическая сцена построена программно, без личных фотографий или чужого тестового изображения. После преобразования в YUV420 она обрабатывается реальными OR1K-инструкциями ядра 0.8, сохранённого в 0.9, в нашем ограниченном эмуляторе.

Показаны режимы I, фиксированная фаза tick=384, размер входа 160×80. Большие сохранённые фото могут выглядеть иначе: сортировка использует другие размеры окон. Эта иллюстрация не является аппаратным тестом или измерением FPS.

Для повторения нужны локально собранные образы, Pillow, NumPy и установленный Arial либо DejaVuSans с кириллицей:

```sh
python3 -m pip install -r requirements-dev.txt numpy
python3 tools/render_effects_preview.py
```

Предыдущий [ASCII-знак](ascii-wordmark.md) сохранён для терминалов и текстовых представлений.
