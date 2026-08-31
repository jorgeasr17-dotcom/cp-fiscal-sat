# -*- coding: utf-8 -*-
"""CLI: python generar_txt.py RFC "NOMBRE SAT" "Nuevo León" "Monterrey" """
from __future__ import annotations

import sys

import catalogo
import motor


def main() -> int:
    if len(sys.argv) < 5:
        print('Uso: python generar_txt.py RFC "NOMBRE SAT" "Estado" "Municipio"')
        print('Ej.:  python generar_txt.py XAXX010101000 "NOMBRE APELLIDO APELLIDO" "Nuevo León" "Cadereyta Jiménez"')
        return 1
    rfc, nombre, estado = sys.argv[1], sys.argv[2], sys.argv[3]
    munis = sys.argv[4:]
    try:
        cps, usados = catalogo.cps_de(estado, munis)
        destino = motor.generar_txt(rfc, nombre, cps, usados[0] if len(usados) == 1 else estado)
    except Exception as exc:
        print(f"Error: {exc}")
        return 1
    print(f"Listo: {destino}  ({len(cps)} CPs · {', '.join(usados)})")
    print("Marque en el SAT: Validar RFC, nombre y CP → validación masiva.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
