#!/usr/bin/env python3
"""
Publica un plan de trabajo ya generado en docs/<cliente>/index.html para que
GitHub Pages lo sirva (Settings > Pages > Deploy from a branch > main > /docs).

También regenera docs/index.html: un formulario que genera planes 100% en el
navegador (sin backend, reutilizando templates/plan_template.html y los datos
fijos de data/) más la lista de todos los planes ya publicados. Para que ese
formulario funcione, este script sincroniza esos mismos archivos como assets
estáticos en docs/_generador/.

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
ASSETS_DIR = DOCS_DIR / "_generador"
INDEX_TEMPLATE_PATH = BASE_DIR / "templates" / "index_template.html"
PLAN_TEMPLATE_PATH = BASE_DIR / "templates" / "plan_template.html"
PARTIDAS_PATH = BASE_DIR / "data" / "partidas.json"
MATRIZ_PATH = BASE_DIR / "data" / "matriz_responsabilidad.json"


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


def sync_assets():
    """Copia la plantilla y los datos fijos a docs/_generador/ para que el
    formulario de docs/index.html los pueda leer con fetch() en el navegador
    (mismo origen, sin CORS) y generar el plan sin backend."""
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(PLAN_TEMPLATE_PATH, ASSETS_DIR / "plan_template.html")
    shutil.copyfile(PARTIDAS_PATH, ASSETS_DIR / "partidas.json")
    if MATRIZ_PATH.exists():
        shutil.copyfile(MATRIZ_PATH, ASSETS_DIR / "matriz_responsabilidad.json")


def reconstruir_indice():
    entradas = []
    if DOCS_DIR.exists():
        for sub in sorted(DOCS_DIR.iterdir()):
            if sub.is_dir() and sub.name != "_generador" and (sub / "index.html").exists():
                titulo = extraer_titulo(sub / "index.html") or sub.name
                entradas.append((titulo, sub.name))

    filas = "\n".join(
        f'      <li><a href="{slug}/">{html.escape(titulo)}</a></li>'
        for titulo, slug in entradas
    ) or '      <li style="color:#888">Aún no hay planes publicados.</li>'

    actualizado = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    plantilla = INDEX_TEMPLATE_PATH.read_text(encoding="utf-8")
    pagina = plantilla.replace("{{ LISTA_PLANES }}", filas).replace("{{ ACTUALIZADO }}", actualizado)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "index.html").write_text(pagina, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").touch()
    sync_assets()


def main():
    if len(sys.argv) == 1:
        # Sin argumentos: solo refresca docs/index.html y docs/_generador/
        # (útil la primera vez, o después de editar la plantilla/los datos
        # fijos, sin necesidad de publicar el plan de ningún cliente).
        reconstruir_indice()
        print(f"Índice actualizado: {DOCS_DIR / 'index.html'}")
        return
    if len(sys.argv) != 3:
        print("Uso: python publish_docs.py [<ruta-al-html-generado> <contribuyente>]", file=sys.stderr)
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
