<!-- source: README.md blob 26dba1fed53b37c294f70349c23bb346496fea17 -->
[English](README.md) | [日本語](README.ja.md) | Español

> Este documento es una traducción de la [versión en inglés](README.md). Si hay diferencias, prevalece la versión en inglés.

# lyrics-video-app

Crea vídeos con la letra de tus propias canciones, sin conexión, en un Mac: una imagen de fondo fija, el título de la
canción, subtítulos con la letra que aparecen y desaparecen en la parte inferior, créditos y un espectro de audio
dibujado por [audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), con el audio de la canción.
Sustituye un proceso manual en el que se superponían imágenes de subtítulos en un editor de vídeo.

**Estado:** fase 1 (diseño) aceptada. `lyrics-video captions` crea a
partir de un archivo de letra las mismas imágenes de subtítulos que el antiguo script de imágenes de letra, para
usarlas en iMovie; `lyrics-video compare` muestra un texto en muchas fuentes; `lyrics-video still` dibuja fotogramas
del futuro vídeo (fondo, título, subtítulo, créditos y espectro) en tres diseños, `soft` por defecto. Los vídeos
completos llegarán en fases posteriores. Consulta el
[informe de aceptación de la fase 1](docs/working/PHASE1_ACCEPTANCE.md) (solo en inglés).

## Inicio rápido

audio-spectrum-app debe estar descargado junto a este repositorio (`../audio-spectrum-app`).

```bash
brew install uv ffmpeg
uv sync
mkdir -p work/my-song && cp examples/song.example.toml work/my-song/song.toml        # después elige la fuente, los colores y la letra
uv run lyrics-video captions work/my-song/song.toml         # un PNG por línea de subtítulo
uv run lyrics-video compare work/my-song/song.toml          # el texto de comparación en varias fuentes
uv run lyrics-video still work/my-song/song.toml --time 60  # fotogramas del vídeo en los instantes elegidos
```

Ejecuta `uv run pytest` para las pruebas.

## Documentación

- [Guía de uso](docs/es/USER_GUIDE.md): instalación, las órdenes, el archivo de la canción y el cambio desde el script antiguo
- [Desarrollo](docs/es/DEVELOPMENT.md): instalación, pruebas y convenciones
- [Índice de la documentación](docs/es/README.md): todos los documentos, incluidas las decisiones y los registros de cada fase

## Licencia

[MIT](LICENSE). Las canciones, letras, imágenes y fuentes nunca forman parte de este repositorio.
