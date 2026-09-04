# Generador de planes de trabajo — Volumetrics by AIVARA

Genera un HTML autocontenido y "vivo" (avance clicable, guardado local, exportable a
PDF) por cada cliente, a partir de 6 datos. No depende de ningún runtime privado:
es HTML + CSS + JS vanilla, listo para GitHub Pages, Vercel, Netlify o para enviarse
por correo y abrirse con doble clic.

## Arquitectura

```
generator/
  generate.py              # script de generación (CLI interactivo o por flags)
  templates/
    plan_template.html     # plantilla única: CSS + lógica de negocio en JS vanilla
  data/
    partidas.json           # estructura fija de partidas/subtareas (de la plantilla Excel)
  requirements.txt          # solo openpyxl, solo si usas --matriz-excel
output/
  <cliente>-plan-de-trabajo.html   # un archivo por cliente, lo que se entrega
```

- **Datos** (`data/partidas.json`) y **plantilla/lógica** (`templates/plan_template.html`)
  están separados del **script de generación** (`generate.py`), para que cambiar las
  partidas o el diseño no toque el generador.
- La plantilla no usa frameworks: un solo archivo con `<style>` y `<script>` inline.
  El script de Python solo reemplaza dos placeholders (`{{ client_json }}`,
  `{{ partidas_json }}`) con los datos del cliente — no hay build step.
- Las partidas (A–E), sus subtareas y duraciones son fijas para todos los clientes
  (vienen del Excel "Template - Plan de trabajo y Matriz Responsabilidad"); lo único
  que cambia por cliente son los 6 datos de entrada.

## Uso

Interactivo:

```bash
python generate.py
```

Por línea de comandos:

```bash
python generate.py \
  --contribuyente "General Motors" \
  --instalaciones 4 \
  --molecula "Gas Natural" \
  --excluir Certificación \
  --unidad-verificadora MG3 \
  --kickoff 2026-09-07
```

Esto crea `output/general-motors-plan-de-trabajo.html`, listo para enviar al cliente.

### Los 6 datos

| Campo | Ejemplo | Notas |
|---|---|---|
| `--contribuyente` | `GM` | Nombre de la empresa |
| `--instalaciones` | `4` | Un número → genera "Instalación 1..N"; o nombres separados por comas: `"Planta Silao, Planta Ramos Arizpe"` |
| `--molecula` | `Gas Natural` | Molécula/producto general del cliente |
| `--excluir` | `Certificación` | Partidas a excluir (por nombre o id: A–E); se reconoce sin acentos/mayúsculas |
| `--unidad-verificadora` | `MG3` | Reemplaza "VICER" en toda la partida E y el renglón de equipo |
| `--kickoff` | `2026-09-07` | Fecha general. Para excepciones por instalación: `"2026-09-07, Planta Ramos Arizpe: 2026-10-01"` |

Si el nombre de una excepción de kickoff coincide con más de una instalación, el
plan generado muestra una banda de advertencia ("Fecha de kickoff ambigua") y
todas conservan la fecha general — la misma regla que ya usaba la plantilla original.

### Matriz de responsabilidad (RACI) — opcional

Si el cliente tiene un Excel con la hoja "Matriz de Responsabilidades" (mismo
formato que "Template - Plan de trabajo y Matriz Responsabilidad - Controles
Volumetricos.xlsx": columna A = tarea, columna B = asignado a, columnas C en
adelante = roles con letras R/A/C/I, y al final una leyenda), se puede importar
con `--matriz-excel`:

```bash
python generate.py --contribuyente "General Motors" --instalaciones 4 \
  --molecula "Gas Natural" --excluir Certificación \
  --unidad-verificadora MG3 --kickoff 2026-09-07 \
  --matriz-excel "GM - Matriz Responsabilidad.xlsx"
```

Esto requiere `pip install -r requirements.txt` (openpyxl) — es la única
dependencia externa de todo el generador, y solo hace falta si usas esta
opción. Sin `--matriz-excel`, el plan se genera igual que siempre, sin la
pestaña extra.

Las letras se toman literalmente de donde estén capturadas en el Excel (no se
asume que siempre estén en la fila de la partida "padre" — si en el Excel del
cliente el RACI de una partida quedó capturado en una subtarea en particular,
así se refleja).

## El archivo entregado (deliverable)

Cada `output/<cliente>-plan-de-trabajo.html` es 100% autónomo:

- Pestaña **General** con anillo de avance ponderado, semanas de atraso y bloques de
  partidas completadas/pendientes.
- Pestaña **Matriz de responsabilidad** (solo si se generó con `--matriz-excel`):
  tabla RACI por tarea con una columna por rol y su leyenda. Al exportar a PDF,
  esta pestaña se incluye siempre como página adicional, sin importar cuál esté
  activa en pantalla en ese momento.
- Una pestaña por instalación, con su propio anillo, kickoff, molécula y tabla de
  partidas con subtareas expandibles.
- El estado se captura por subtarea con clic (pendiente → en proceso → completada);
  la partida y los anillos se recalculan solos.
- Botón **"+ Instalación"** junto a las pestañas para agregar una instalación nueva
  en cualquier momento (hereda la molécula general y la misma exclusión de partidas
  que las demás). Botón **"Eliminar instalación"** dentro de cada pestaña de
  instalación, que pide confirmación explícita antes de borrar (el avance de esa
  instalación se pierde permanentemente al confirmar). Debe quedar siempre al menos
  una instalación.
- Guardado automático en `localStorage` del navegador, con clave por contribuyente
  (dos clientes abiertos en el mismo navegador no se pisan).
- Botón **Descargar PDF** (usa la impresión nativa del navegador con una hoja de
  estilos `@media print` que oculta las pestañas) — no depende de ninguna librería
  externa ni de conexión a internet.
- Única dependencia externa: la tipografía Inter vía Google Fonts (con fallback a
  la fuente del sistema si no hay internet).

## Generar desde GitHub Actions

El repositorio incluye [`.github/workflows/generar-plan.yml`](.github/workflows/generar-plan.yml),
un workflow manual (`workflow_dispatch`) que corre `generate.py` en la nube sin
necesidad de tener Python instalado localmente.

Para usarlo:

1. En GitHub, entra a la pestaña **Actions** del repositorio.
2. Selecciona el workflow **"Generar plan de trabajo"**.
3. Clic en **Run workflow** y llena los 6 campos (contribuyente, instalaciones,
   molécula, partidas a excluir, unidad verificadora, fecha de kickoff).
4. Al terminar la ejecución, el archivo HTML queda disponible como **artefacto
   descargable** en la página de esa ejecución (sección "Artifacts"), listo para
   enviar al cliente.

El workflow no hace commit del HTML generado al repositorio (los planes contienen
datos reales de clientes); solo lo publica como artefacto de esa ejecución, que
solo pueden descargar quienes tengan acceso al repositorio.

## Publicar y compartir como página web (GitHub Pages)

⚠️ **Antes de activar esto:** en una cuenta personal de GitHub (no Enterprise),
el sitio de GitHub Pages es **público** aunque el repositorio sea privado —
cualquiera con el link puede verlo, no hay control de acceso real. Hacer el
repo privado solo oculta el código fuente, no el sitio publicado. Si los planes
contienen datos sensibles de clientes, evalúa si esto es aceptable antes de
publicar; la alternativa sin este riesgo es usar solo el artefacto descargable
del workflow (requiere login de GitHub con acceso al repo).

### Configuración (una sola vez)

1. En GitHub → **Settings → Pages** → en "Build and deployment", **Source:
   Deploy from a branch** → **Branch: `main`, folder: `/docs`** → **Save**.
2. (Opcional) **Settings → General → Danger Zone → Change visibility** para
   hacer el repo privado — recuerda que esto no oculta el sitio de Pages, ver
   el aviso arriba.

### Publicar un plan

El workflow **"Generar plan de trabajo"** ya incluye un input
`publicar_en_pages` (activado por default): al correrlo, además de generar el
HTML y subirlo como artefacto, lo copia a `docs/<cliente>/index.html`, regenera
`docs/index.html` (un índice con links a todos los planes publicados) y hace
commit + push automático de esos cambios. GitHub Pages redeploya solo.

El plan queda visible en:

```
https://heber-peniche.github.io/plan-generator-/<cliente>/
```

Para generarlo y publicarlo desde tu máquina en vez de Actions:

```bash
python generate.py --contribuyente "General Motors" --instalaciones 4 \
  --molecula "Gas Natural" --excluir Certificación \
  --unidad-verificadora MG3 --kickoff 2026-09-07 --out-dir output

python publish_docs.py output/general-motors-plan-de-trabajo.html "General Motors"

git add docs/ && git commit -m "Publicar plan: General Motors" && git push
```

Si en un run no quieres publicar (ej. cliente muy sensible), pon
`publicar_en_pages` en `false` al correr el workflow — el HTML seguirá
disponible como artefacto descargable, sin tocar `docs/`.
