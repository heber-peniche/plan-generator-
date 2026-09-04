#!/usr/bin/env python3
"""
Generador de planes de trabajo — Volumetrics by AIVARA.

Toma los 6 datos por cliente (contribuyente, instalaciones, molécula,
partidas a excluir, unidad verificadora, fecha de kickoff) e inyecta un
plan de trabajo HTML autocontenido (sin dependencias externas de terceros,
salvo la fuente Inter vía Google Fonts, con fallback a system-ui offline).

Uso interactivo:
    python generate.py

Uso no interactivo:
    python generate.py --contribuyente "General Motors" --instalaciones 4 \
        --molecula "Gas Natural" --excluir Certificación \
        --unidad-verificadora MG3 --kickoff 2026-09-07

Las partidas fijas (A-E, con sus subtareas y duraciones) y la matriz de
responsabilidad (RACI) viven en data/partidas.json y
data/matriz_responsabilidad.json, y no cambian entre clientes — están
tomadas del Excel "Template - Plan de trabajo y Matriz Responsabilidad -
Controles Volumetricos" / "GENERAL MOTORS - Agenda de Implementación y
Matriz Responsabilidad".
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "templates" / "plan_template.html"
PARTIDAS_PATH = BASE_DIR / "data" / "partidas.json"
MATRIZ_PATH = BASE_DIR / "data" / "matriz_responsabilidad.json"
OUTPUT_DIR = BASE_DIR.parent / "output"

# id de partida -> nombres/alias reconocidos para "partidas a excluir"
PARTIDA_ALIAS = {
    "A": ["a", "pre-auditoria", "pre auditoria", "preauditoria", "diagnostico"],
    "B": ["b", "reportes historicos", "historicos", "sat 2022-2025", "reportes sat"],
    "C": ["c", "programa informatico", "software", "nube", "covol"],
    "D": ["d", "sgm", "sgm 10012", "balance volumetrico"],
    "E": ["e", "certificacion", "certificado", "certificado anual"],
}


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def resolver_partidas_excluir(valores):
    """Acepta ids ('E'), nombres ('Certificación') o listas mixtas; case/accent-insensitive."""
    ids = set()
    desconocidos = []
    for v in valores:
        v = v.strip()
        if not v:
            continue
        nv = _norm(v)
        encontrado = None
        for pid, alias in PARTIDA_ALIAS.items():
            # Solo se hace matching por substring en alias de 3+ caracteres,
            # para que letras sueltas ("a", "e") no den falsos positivos por
            # ser substring de un nombre largo (ej. "certificación" contiene "a").
            if nv == pid.lower() or any(
                nv == a or (len(a) >= 3 and (nv in a or a in nv)) for a in alias
            ):
                encontrado = pid
                break
        if encontrado:
            ids.add(encontrado)
        else:
            desconocidos.append(v)
    if desconocidos:
        print(f"Aviso: no reconozco estas partidas a excluir, se ignoran: {', '.join(desconocidos)}", file=sys.stderr)
    return sorted(ids)


def resolver_instalaciones(valor: str):
    """Si es un número puro -> 'Instalación 1..N'; si no, se toma como lista separada por comas."""
    valor = (valor or "").strip()
    if valor.isdigit():
        n = int(valor)
        return [f"Instalación {i}" for i in range(1, n + 1)]
    nombres = [s.strip() for s in valor.split(",") if s.strip()]
    return nombres or ["Instalación 1"]


def slugify(s: str) -> str:
    s = _norm(s)
    return re.sub(r"\s+", "-", s).strip("-") or "cliente"


def construir_client_data(contribuyente, instalaciones_raw, molecula, excluir_raw,
                           unidad_verificadora, kickoff):
    instalaciones = resolver_instalaciones(instalaciones_raw)
    excluir_ids = resolver_partidas_excluir(
        excluir_raw if isinstance(excluir_raw, list) else re.split(r"[,;]", excluir_raw or "")
    )
    overrides = {}
    if excluir_ids:
        for i in range(len(instalaciones)):
            overrides[str(i)] = {"excluir": excluir_ids}

    return {
        "contribuyente": contribuyente.strip(),
        "unidadVerificadora": unidad_verificadora.strip(),
        "moleculaGeneral": molecula.strip(),
        "fechaKickoff": kickoff.strip(),
        "instalaciones": ", ".join(instalaciones),
        "overrides": overrides,
        # Aplica también a instalaciones agregadas en vivo desde el HTML (botón
        # "+ Instalación"), para que hereden la misma exclusión que las demás.
        "excluirGeneral": excluir_ids,
    }


def render(client_data: dict) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    partidas_data = json.loads(PARTIDAS_PATH.read_text(encoding="utf-8"))
    matriz_data = json.loads(MATRIZ_PATH.read_text(encoding="utf-8")) if MATRIZ_PATH.exists() else {}
    html = template.replace(
        "{{ client_json }}", json.dumps(client_data, ensure_ascii=False, indent=2)
    ).replace(
        "{{ partidas_json }}", json.dumps(partidas_data, ensure_ascii=False)
    ).replace(
        "{{ matriz_json }}", json.dumps(matriz_data, ensure_ascii=False)
    ).replace(
        "{{ contribuyente }}", client_data["contribuyente"]
    )
    return html


def generar(contribuyente, instalaciones, molecula, excluir, unidad_verificadora, kickoff,
            out_dir: Path = OUTPUT_DIR) -> Path:
    client_data = construir_client_data(
        contribuyente, instalaciones, molecula, excluir, unidad_verificadora, kickoff
    )
    html = render(client_data)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slugify(contribuyente)}-plan-de-trabajo.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def parse_args():
    p = argparse.ArgumentParser(description="Genera un plan de trabajo HTML por cliente.")
    p.add_argument("--contribuyente", help="Nombre de la empresa, ej. 'General Motors'")
    p.add_argument("--instalaciones", help="Número de instalaciones (ej. 4) o nombres separados por comas")
    p.add_argument("--molecula", help="Molécula / producto, ej. 'Gas Natural'")
    p.add_argument("--excluir", default="", help="Partidas a excluir (ids o nombres), separadas por comas, ej. 'Certificación'")
    p.add_argument("--unidad-verificadora", dest="unidad_verificadora", help="Ej. MG3")
    p.add_argument("--kickoff", help="Fecha de kickoff, ej. '2026-09-07' o '2026-09-07, Planta 2: 2026-10-01'")
    p.add_argument("--out-dir", default=str(OUTPUT_DIR), help="Carpeta de salida")
    return p.parse_args()


def prompt(msg, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val or (default or "")


def main():
    args = parse_args()
    if not args.contribuyente:
        print("=== Generador de planes de trabajo — Volumetrics by AIVARA ===\n")
        contribuyente = prompt("Contribuyente (nombre de la empresa)")
        instalaciones = prompt("Número de instalaciones (o nombres separados por comas)", "1")
        molecula = prompt("Molécula / producto", "Gas L.P.")
        excluir = prompt("Partidas a excluir (separadas por comas, Enter si ninguna)", "")
        unidad_verificadora = prompt("Unidad verificadora del proyecto", "VICER")
        kickoff = prompt("Fecha de kickoff (YYYY-MM-DD)")
        excluir_list = [s.strip() for s in excluir.split(",") if s.strip()]
    else:
        contribuyente = args.contribuyente
        instalaciones = args.instalaciones or "1"
        molecula = args.molecula or "Gas L.P."
        unidad_verificadora = args.unidad_verificadora or "VICER"
        kickoff = args.kickoff or ""
        excluir_list = args.excluir

    if not contribuyente:
        print("Error: el contribuyente es obligatorio.", file=sys.stderr)
        sys.exit(1)
    if not kickoff:
        print("Error: la fecha de kickoff es obligatoria (YYYY-MM-DD).", file=sys.stderr)
        sys.exit(1)

    out_path = generar(
        contribuyente, instalaciones, molecula, excluir_list, unidad_verificadora, kickoff,
        out_dir=Path(args.out_dir) if hasattr(args, "out_dir") and args.out_dir else OUTPUT_DIR,
    )
    print(f"\nListo: {out_path}")


if __name__ == "__main__":
    main()
