#!/usr/bin/env python3
"""
Publica un plan de trabajo ya generado en docs/<cliente>/index.html para que
GitHub Pages lo sirva (Settings > Pages > Deploy from a branch > main > /docs).

También regenera docs/index.html con la lista de todos los planes publicados.

Uso:
    python publish_docs.py output/general-motors-plan-de-trabajo.html "General Motors"
"""
import html
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from generate import slugify

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"


def extraer_titulo(path: Path) -> str | None:
    texto = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", texto, re.S)
    return html.unescape(m.group(1)).strip() if m else None


def publicar(html_path: Path, contribuyente: str) -> Path:
    slug = slugify(contribuyente)
    destino_dir = DOCS_DIR / slug
    destino_dir.mkdir(parents=True, exist_ok=True)
    destino = destino_dir / "index.html"
    shutil.copyfile(html_path, destino)
    return destino


def reconstruir_indice():
    entradas = []
    if DOCS_DIR.exists():
        for sub in sorted(DOCS_DIR.iterdir()):
            if sub.is_dir() and (sub / "index.html").exists():
                titulo = extraer_titulo(sub / "index.html") or sub.name
                entradas.append((titulo, sub.name))

    filas = "\n".join(
        f'      <li><a href="{slug}/">{html.escape(titulo)}</a></li>'
        for titulo, slug in entradas
    ) or '      <li style="color:#888">Aún no hay planes publicados.</li>'

    actualizado = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    pagina = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Planes de trabajo — Volumetrics by AIVARA</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", Arial, sans-serif; max-width: 640px; margin: 60px auto; padding: 0 24px; color: #4D4D4D; }}
  h1 {{ font-size: 20px; }}
  ul {{ list-style: none; padding: 0; }}
  li {{ padding: 12px 0; border-bottom: 1px solid #E5E5E5; }}
  a {{ color: #C94A1C; text-decoration: none; font-weight: 600; }}
  a:hover {{ text-decoration: underline; }}
  .nota {{ font-size: 12px; color: #888; margin-top: 32px; }}
</style>
</head>
<body>
  <h1>Planes de trabajo — Volumetrics by AIVARA</h1>
  <ul>
{filas}
  </ul>
  <p class="nota">Actualizado {actualizado} · generado automáticamente, no editar a mano.</p>
</body>
</html>
"""
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(pagina, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").touch()


def main():
    if len(sys.argv) != 3:
        print("Uso: python publish_docs.py <ruta-al-html-generado> <contribuyente>", file=sys.stderr)
        sys.exit(1)
    html_path = Path(sys.argv[1])
    if not html_path.exists():
        print(f"Error: no existe {html_path}", file=sys.stderr)
        sys.exit(1)
    destino = publicar(html_path, sys.argv[2])
    reconstruir_indice()
    print(f"Publicado: {destino}")


if __name__ == "__main__":
    main()
