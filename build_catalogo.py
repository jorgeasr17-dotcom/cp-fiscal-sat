# -*- coding: utf-8 -*-
"""Compacta CPdescarga.txt (SEPOMEX) a estado -> municipio -> CPs únicos."""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ORIGEN = Path(__file__).resolve().parent / "data" / "CPdescarga.txt"
DESTINO = Path(__file__).resolve().parent / "data" / "catalogo_cp.json"


def main() -> None:
    raw = ORIGEN.read_bytes()
    texto = raw.decode("cp1252")
    por: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    n_filas = 0
    for linea in texto.splitlines()[1:]:
        if not linea.strip() or linea.startswith("d_codigo|"):
            continue
        partes = linea.split("|")
        if len(partes) < 5:
            continue
        cp, _asenta, _tipo, mnpio, estado = (partes[0].strip(), partes[1], partes[2], partes[3].strip(), partes[4].strip())
        if len(cp) != 5 or not cp.isdigit() or not estado or not mnpio:
            continue
        por[estado][mnpio].add(cp)
        n_filas += 1

    catalogo = {
        "fuente": "Correos de México / SEPOMEX (Catálogo Nacional de Códigos Postales)",
        "estados": [],
    }
    for estado in sorted(por, key=lambda s: s.casefold()):
        municipios = []
        for mnpio in sorted(por[estado], key=lambda s: s.casefold()):
            cps = sorted(por[estado][mnpio])
            municipios.append({"nombre": mnpio, "cps": cps})
        catalogo["estados"].append({"nombre": estado, "municipios": municipios})

    DESTINO.parent.mkdir(exist_ok=True)
    DESTINO.write_text(json.dumps(catalogo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_est = len(catalogo["estados"])
    n_mun = sum(len(e["municipios"]) for e in catalogo["estados"])
    n_cp = len({cp for e in catalogo["estados"] for m in e["municipios"] for cp in m["cps"]})
    print(f"Filas {n_filas}  estados {n_est}  municipios {n_mun}  CPs únicos {n_cp}")
    print(f"Archivo {DESTINO}  {DESTINO.stat().st_size} bytes")


if __name__ == "__main__":
    main()
