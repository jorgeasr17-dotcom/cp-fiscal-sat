# -*- coding: utf-8 -*-
"""Catálogo SEPOMEX compacto: estado → municipio → CPs únicos."""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

ARCHIVO = Path(__file__).resolve().parent / "data" / "catalogo_cp.json"
SAT_MAX = 5000


def _sin_acentos(texto: str) -> str:
    nk = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nk if unicodedata.category(c) != "Mn")


def _norm(texto: str) -> str:
    t = _sin_acentos(texto).casefold()
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=1)
def _data() -> dict:
    if not ARCHIVO.exists():
        raise FileNotFoundError(
            f"Falta {ARCHIVO}. Ejecute: python build_catalogo.py"
        )
    return json.loads(ARCHIVO.read_text(encoding="utf-8"))


def estados() -> list[dict]:
    out = []
    for e in _data()["estados"]:
        cps: set[str] = set()
        for m in e["municipios"]:
            cps.update(m["cps"])
        out.append(
            {
                "nombre": e["nombre"],
                "n_cps": len(cps),
                "n_municipios": len(e["municipios"]),
            }
        )
    return out


def _estado(nombre: str) -> dict:
    n = _norm(nombre)
    for e in _data()["estados"]:
        if _norm(e["nombre"]) == n:
            return e
    raise ValueError(f"Estado no encontrado: {nombre}")


def n_cps_estado(estado: str) -> int:
    e = _estado(estado)
    cps: set[str] = set()
    for m in e["municipios"]:
        cps.update(m["cps"])
    return len(cps)


def municipios(estado: str) -> list[dict]:
    e = _estado(estado)
    return [{"nombre": m["nombre"], "n_cps": len(m["cps"])} for m in e["municipios"]]


def cps_de(estado: str, municipios_sel: list[str] | None) -> tuple[list[str], list[str]]:
    e = _estado(estado)
    sel = [m.strip() for m in (municipios_sel or []) if m and str(m).strip()]
    if not sel:
        union: set[str] = set()
        for m in e["municipios"]:
            union.update(m["cps"])
        cps = sorted(union)
        if len(cps) > SAT_MAX:
            raise ValueError(
                f"Todo {e['nombre']} son {len(cps)} CPs y el SAT acepta máximo {SAT_MAX}."
            )
        return cps, []
    por_nombre = {_norm(m["nombre"]): m for m in e["municipios"]}
    usados = []
    union: set[str] = set()
    faltan = []
    for raw in municipios_sel:
        nombre = (raw or "").strip()
        if not nombre:
            continue
        m = por_nombre.get(_norm(nombre))
        if not m:
            faltan.append(nombre)
            continue
        usados.append(m["nombre"])
        union.update(m["cps"])
    if faltan:
        raise ValueError("Municipio no encontrado: " + ", ".join(faltan))
    if not union:
        raise ValueError("No hay códigos postales para esa selección.")
    cps = sorted(union)
    if len(cps) > SAT_MAX:
        raise ValueError(
            f"Son {len(cps)} CPs y el SAT acepta máximo {SAT_MAX} por archivo. "
            "Quite algún municipio."
        )
    return cps, usados
