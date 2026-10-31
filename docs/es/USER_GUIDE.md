<!-- source: docs/en/USER_GUIDE.md blob 01640a9b6aeb8404821a419ee846696023a98f3f -->
[English](../en/USER_GUIDE.md) | [日本語](../ja/USER_GUIDE.md) | Español · [Índice de la documentación](README.md)

> Este documento es una traducción de la [versión en inglés](../en/USER_GUIDE.md). Si hay diferencias, prevalece la versión en inglés.

# Guía de uso

Cómo instalar lyrics-video-app, crear las imágenes de subtítulos de una canción y ver fotogramas de su vídeo. Los
vídeos completos llegarán en fases posteriores.

## 1. Instalación

```bash
brew install uv ffmpeg
uv sync
```

audio-spectrum-app debe estar descargado junto a este repositorio (`../audio-spectrum-app`); consulta
[Desarrollo](DEVELOPMENT.md) §1. Todo funciona sin conexión.

## 2. Una carpeta por canción

Guarda cada canción en su propia carpeta dentro de `work/`, que Git ignora, o en cualquier lugar fuera del
repositorio:

```text
work/my-song/
  song.toml      el archivo de la canción: letra, colores, fuente, carpetas de salida
  lyrics.txt     un subtítulo por línea
  compare.txt    una o dos líneas para probar en varias fuentes (opcional)
```

Empieza por los ejemplos: copia `examples/song.example.toml` a `work/my-song/song.toml` y
`examples/lyrics.example.txt` a `work/my-song/lyrics.txt`, y edítalos.

### El archivo de letra

- Texto UTF-8, un subtítulo por línea.
- `;` divide un subtítulo en dos filas (`primera fila;segunda fila`). Una línea con más de un `;` es un error. Se
  puede elegir otro separador en el archivo de la canción.
- Las líneas vacías se omiten, pero siguen contando para los números de los nombres de archivo, como antes.

## 3. Imágenes de subtítulos: `captions`

```bash
uv run lyrics-video captions work/my-song/song.toml
```

Escribe un PNG por subtítulo en la carpeta de salida (por defecto `captions/`, junto al archivo de la canción), con
el nombre `lyrics_<índice de línea>.png`, donde el índice empieza en 0 e incluye las líneas vacías. Cada imagen es
una franja del color de fondo con el subtítulo en el color del texto, alineado a la izquierda:

- El tamaño de letra empieza en 80 y baja de 2 en 2 hasta que todas las filas caben con un margen de 50 px en cada
  dirección. Las dos filas de un subtítulo usan el mismo tamaño.
- Una fila se centra en vertical; dos filas ocupan la mitad superior y la inferior.

Son las reglas del antiguo script de imágenes de letra, así que las imágenes se pueden usar en iMovie como antes: la
imagen de fondo llena el encuadre y cada imagen de subtítulo va abajo del todo, a lo ancho, con fundidos.

Las imágenes existentes nunca se reemplazan sin avisar: si existe algún archivo de salida, no se escribe nada y se
muestra la lista. Añade `--overwrite` para reemplazarlos. Si la nueva letra tiene menos líneas, borra antes la
carpeta antigua para que no queden imágenes obsoletas.

## 4. Elegir una fuente: `compare`

```bash
uv run lyrics-video compare work/my-song/song.toml
uv run lyrics-video compare work/my-song/song.toml --font-dir ~/path/to/fonts --font /System/Library/Fonts/ヒラギノ明朝\ ProN.ttc
```

Dibuja cada línea del texto de comparación (`compare.txt`) en cada fuente, con el tamaño y los colores de la
canción, en la carpeta de comparación (por defecto `compare/`):

- `<nombre del archivo de fuente>_<índice de línea>.png` para cada fuente y línea;
- `contact_sheet.png`: la primera línea en todas las fuentes, una debajo de otra, cada una bajo el nombre de su
  fuente.

Las fuentes son `compare.fonts` y todos los archivos de fuente de `compare.font_dirs` (también en subcarpetas).
`--font` y `--font-dir` (se pueden repetir) reemplazan ambas listas en esa ejecución. Los archivos de fuente son
`.ttf`, `.otf`, `.ttc` y `.otc`; de una colección se usa la primera cara. `--overwrite` funciona igual que en
`captions`.

## 5. Fotogramas del vídeo y diseños: `still`

```bash
uv run lyrics-video still work/my-song/song.toml --time 3 62.5 --caption 4
```

Escribe los fotogramas que mostrará el vídeo en los instantes indicados (segundos de la canción) en `stills/`, junto
al archivo de la canción, con el nombre `<diseño>_<instante>s.png`: la imagen de fondo, el título, un subtítulo, los
créditos y el espectro de ese momento encima, exactamente como los tendrá el vídeo. Hasta que la letra tenga tiempos,
un fotograma muestra un solo subtítulo: la línea indicada con `--caption` (el índice de línea, contado como en los
nombres de las imágenes de subtítulos), el primer subtítulo por defecto, o ninguno con `--no-caption`. `--overwrite`
funciona igual que en `captions`.

Un fotograma se compone de estas partes, de abajo arriba:

| Parte | Contenido |
|---|---|
| Fondo | `background_image`, escalada para cubrir el encuadre y recortada, nunca estirada; negro sin imagen |
| Título | `title` y `subtitle`, dibujados por la aplicación |
| Subtítulo | El subtítulo del momento, con fundido de entrada y de salida |
| Créditos | Las líneas de `credits`, durante los primeros y los últimos segundos de la canción, sobre el encuadre oscurecido |
| Espectro | Dibujado por audio-spectrum-app con el preset y los ajustes de `[spectrum]` |

El aspecto de las partes es un **diseño**. El diseño incluido es `classic`: el título grande arriba en el centro, los
subtítulos en una franja opaca a lo largo del borde inferior dibujados con las reglas de las imágenes de subtítulos
antiguas y los créditos centrados. Elige un diseño con `design = "classic"`, o un archivo de diseño propio con
`design = "my-design.toml"`. Para cambiar valores sueltos, escribe una tabla `[design]` con el `name` del diseño y las
partes que cambian:

```toml
[design]
name = "classic"

[design.title]
font = "~/path/to/title-font.otf"   # el título con otra fuente que fonts.default
size = 96

[design.caption]
band_color = "#101820"
```

| Parte | Claves (tamaños en píxeles de un encuadre de 1080 píxeles de alto; se escalan con la altura del vídeo) |
|---|---|
| `background` | `focus` (`[x, y]` de 0 a 1, el punto que queda a la vista al recortar), `dim` (0 a 1), `blur` |
| `title` | `enabled`, `position` (`"top-center"`, `"top-left"`), `font`, `size`, `subtitle_size`, `color`, `margin`, `gap`, `shadow` |
| `caption` | `style` (`"band"`), `align` (`"left"`), `font`, `text_color`, `band_color`, `band_opacity`, `band_height`, `fade_seconds` |
| `credits` | `enabled`, `font`, `size`, `color`, `line_spacing`, `dim`, `show_seconds`, `fade_seconds`, `shadow` |
| `spectrum` | `set`: ajustes del preset aplicados antes de `[spectrum] set` del archivo de la canción |
| `shadow` (en `title`, `credits`) | `blur` (0 = sin sombra), `offset`, `color`, `opacity` |

Cada parte usa `fonts.default` salvo que indique su propia `font`. Los colores se escriben `"#RRGGBB"`.

## 6. El archivo de la canción

Un archivo TOML. Las rutas son relativas al archivo de la canción; `~` es la carpeta personal. Todas las claves son
opcionales excepto `captions.font` para `captions` y `audio` para `still`.

| Clave | Valor por defecto | Significado |
|---|---|---|
| `lyrics` | `"lyrics.txt"` | El archivo de letra |
| `audio` | ninguno | La canción, para el espectro (`still`) |
| `background_image` | ninguno | La imagen de fondo del vídeo |
| `title`, `subtitle` | `""` | El título y una línea debajo |
| `credits` | `[]` | Líneas de créditos |
| `design` | `"classic"` | Un nombre o archivo de diseño, o una tabla `[design]` con `name` y ajustes (sección 5) |
| `fonts.default` | ninguno | La fuente de cada parte del vídeo que no indique la suya |
| `spectrum.preset` | `"default"` | Un nombre o archivo de preset de audio-spectrum-app |
| `spectrum.set` | `[]` | Ajustes del preset, como `--set` de audio-spectrum-app |
| `video.width`, `video.height`, `video.fps` | `1920`, `1080`, `30` | Tamaño y frecuencia de los fotogramas |
| `captions.output_dir` | `"captions"` | Carpeta de las imágenes de subtítulos |
| `captions.size` | tamaño de la imagen de fondo; si no, `[1440, 232]` | Ancho y alto de cada imagen |
| `captions.background` | `"#000000"` | Color de fondo: `"#RRGGBB"`, o un archivo de imagen cuyo píxel central da el color |
| `captions.text_color` | `"#FFFFFF"` | Color del texto, de la misma forma |
| `captions.font` | ninguno | El archivo de fuente |
| `captions.font_index` | `0` | La cara dentro de una colección `.ttc` |
| `captions.separator` | `";"` | Divide un subtítulo en dos filas |
| `captions.file_prefix` | `"lyrics"` | Comienzo de los nombres de archivo |
| `compare.text` | `"compare.txt"` | El texto para comparar fuentes |
| `compare.output_dir` | `"compare"` | Carpeta de las imágenes de comparación |
| `compare.fonts` | `[]` | Archivos de fuente que se comparan |
| `compare.font_dirs` | `[]` | Carpetas cuyas fuentes se comparan todas |

Las fuentes no forman parte de este repositorio y nunca se copian en él; el archivo de la canción solo indica dónde
están. Los archivos reales de cada canción se quedan en `work/` o fuera del repositorio.

## 7. Cambiar desde el antiguo script de imágenes de letra

| `conf.toml` antiguo | Archivo de la canción |
|---|---|
| `input.background_color` (un PNG de muestra) | `captions.background = "back.png"` (el mismo PNG, o su color como `"#RRGGBB"`); el tamaño de la imagen pasa a ser el del subtítulo |
| `input.text_color` (un PNG de muestra) | `captions.text_color` |
| `input.lyrics_text_single` | `lyrics` |
| `input.lyrics_text_multi` | `compare.text` |
| `output.output_dir_single`, `output_dir_multi` | `captions.output_dir`, `compare.output_dir` |
| `font.font_path_single`, `font_path_multi` | `captions.font`, `compare.fonts` |
| `separator.separator` | `captions.separator` |
| `prefix.prefix_image_num` | `captions.file_prefix` |
| `margin.margin_text_x`, `margin_text_y` | Fijos en 50 |

En lugar de la antigua pregunta (0 o 1), elige la orden: `captions` o `compare`.

Diferencias con el script antiguo:

- Las mismas entradas dan los mismos tamaños, colores, tamaños de letra, disposición y nombres de archivo. En algunos
  sitios los caracteres pueden quedar a 1 px de distancia por cambios en las bibliotecas de fuentes; las imágenes se
  ven iguales.
- Una imagen de comparación lleva el nombre completo del archivo de fuente (`my-font-2.04_0.png`, donde el script
  antiguo cortaba el nombre en el primer punto), y la hoja de contactos es nueva.
- Las imágenes existentes no se sobrescriben sin `--overwrite`, y un error en el archivo de la canción, el de la
  letra o una fuente no escribe ninguna imagen.

## 8. Errores

| Código de salida | Significado |
|---|---|
| 0 | Hecho |
| 1 | Error; el mensaje en stderr explica el motivo (archivo de la canción, archivo de letra, fuente, imagen, canción, un subtítulo que no cabe, salida existente) |
| 2 | Uso incorrecto de la línea de órdenes |

Los errores indican el archivo y, en la letra, el número de línea. Todas las imágenes se dibujan antes de escribir
ninguna, así que estos errores no escriben nada; cada archivo se escribe completo o no se escribe.
