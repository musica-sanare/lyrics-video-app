<!-- source: README.md blob 08b24fae74baa6c53c8b1bb7c2a44429c7dda7b7 -->
[English](README.md) | [日本語](README.ja.md) | Español

> Este documento es una traducción de la [versión en inglés](README.md). Si hay diferencias, prevalece la versión en inglés.

# lyrics-video-app

Crea vídeos con la letra de tus propias canciones, sin conexión, en un Mac: una imagen de fondo fija, el título de la
canción, subtítulos con la letra que aparecen y desaparecen en la parte inferior, créditos y un espectro de audio
dibujado por [audio-spectrum-app](https://github.com/musica-sanare/audio-spectrum-app), con el audio de la canción.
Sustituye un proceso manual en el que se superponían imágenes de subtítulos en un editor de vídeo.

**Estado:** Fase 0 (base). La orden ya está preparada; lo siguiente es crear las imágenes de subtítulos a partir de
un archivo de letra. Consulta el [plan de la fase 0](docs/working/PHASE0_PLAN.md) (solo en inglés).

## Inicio rápido

audio-spectrum-app debe estar descargado junto a este repositorio (`../audio-spectrum-app`).

```bash
brew install uv ffmpeg
uv sync
uv run lyrics-video --version
uv run pytest
```

## Documentación

- [Desarrollo](docs/es/DEVELOPMENT.md): instalación, pruebas y convenciones
- [Índice de la documentación](docs/es/README.md): todos los documentos, incluidas las decisiones y los registros de cada fase

## Licencia

[MIT](LICENSE). Las canciones, letras, imágenes y fuentes nunca forman parte de este repositorio.
