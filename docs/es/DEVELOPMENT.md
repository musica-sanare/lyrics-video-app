<!-- source: docs/en/DEVELOPMENT.md blob 2852382f0dd281c6b0607f5e07f07d041ccad412 -->
[English](../en/DEVELOPMENT.md) | [日本語](../ja/DEVELOPMENT.md) | Español · [Índice de la documentación](README.md)

> Este documento es una traducción de la [versión en inglés](../en/DEVELOPMENT.md). Si hay diferencias, prevalece la versión en inglés.

# Desarrollo

Instalación, comprobaciones y convenciones para trabajar en el código.

## 1. Instalación

```bash
brew install uv ffmpeg
git clone <repositorio de audio-spectrum-app> ../audio-spectrum-app   # una vez, junto a este repositorio
uv sync
```

Python 3.13 y todas las dependencias se gestionan con `uv` (`pyproject.toml`, `uv.lock`). audio-spectrum-app es una
dependencia por ruta (`../audio-spectrum-app`, editable, versión 0.5.0 o posterior), así que sus cambios se aplican
sin reinstalar
([ADR-001](../working/DECISIONS.md#adr-001-a-separate-repository-that-draws-under-audio-spectrum-apps-spectrum),
solo en inglés). Solo se puede usar su API pública, los nombres que exporta `audio_spectrum`. Las dependencias se
añaden con `uv add <package>`; deben ser pocas y de uso extendido.

## 2. Pruebas

```bash
uv run pytest
```

- Las pruebas usan solo texto, imágenes y señales generados (`tests/signals.py`), nunca canciones, letras reales ni
  fuentes de terceros. Las pruebas que necesitan una fuente usan las fuentes del sistema de macOS y se omiten donde
  no existen.

| Archivo | Cubre |
|---|---|
| `test_lyrics.py` | Archivos de letra: índices de línea, filas, separadores, errores |
| `test_config.py` | El archivo de la canción: valores por defecto, rutas, colores de imágenes de muestra, validación, los ejemplos |
| `test_fonts.py` | Reunir archivos de fuente y sus etiquetas |
| `test_caption_image.py` | Imágenes de subtítulos: los mismos píxeles que una transcripción del script antiguo, tamaños, disposición |
| `test_cli.py` | `captions` y `compare`: nombres de archivo, sobrescritura, ningún archivo tras un error, fuentes desde la línea de órdenes |
| `test_spectrum_dependency.py` | audio-spectrum-app está instalado; se dibuja un fotograma sobre un fondo (backdrop) suministrado |

## 3. Archivos locales

Las canciones, letras, imágenes de fondo, fuentes, los archivos reales de cada canción y todo lo que se exporta se
quedan en `work/` (ignorado por Git) o fuera del repositorio. `.gitignore` también ignora, en cualquier lugar del
árbol, los archivos de audio, vídeo, imagen y fuentes, y todos los `*.toml` excepto `pyproject.toml` y
`*.example.toml`. Antes de cada commit, revisa que la lista de archivos no contenga nada de esto ni rutas absolutas
con un nombre de usuario (escribe `~/...`).

## 4. Convenciones

- El código, los comentarios, los mensajes de commit y la documentación se escriben en inglés. El japonés y el
  español aparecen solo en las traducciones (`docs/ja/`, `docs/es/`, `README.ja.md`, `README.es.md`).
- El fotograma `n` muestra el audio del instante `n / fps`; los subtítulos y los créditos se colocan por tiempo.
- El uso normal es totalmente sin conexión.
- Los documentos estables están en `docs/en/`, con su traducción al japonés en `docs/ja/` y al español en `docs/es/`;
  cada traducción guarda en su primera línea el hash de blob del archivo en inglés
  (`git hash-object docs/en/<FILE>.md`) y se actualiza en el mismo commit que el archivo en inglés. Los documentos de
  trabajo (planes, decisiones, informes de aceptación) están en `docs/working/`, solo en inglés.
- El trabajo avanza por fases: un plan en `docs/working/PHASE<N>_PLAN.md` aprobado por el propietario, después la
  implementación con un commit por hito y, al final, un informe de aceptación.
- Antes de publicar el repositorio, se analiza todo su historial con un escáner de secretos (por ejemplo,
  `gitleaks`).
