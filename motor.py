# -*- coding: utf-8 -*-
"""Genera TXT SAT y lee la respuesta. No guarda RFC ni nombres."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
SALIDA = CARPETA / "salida"
SAT_URL = (
    "https://www.sat.gob.mx/aplicacion/79615/"
    "valida-en-linea-rfc%C2%B4s-uno-a-uno-o-de-manera-masiva-hasta-5-mil-registros"
)

RFC_RE = re.compile(r"^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$")


def _sin_acentos(texto: str) -> str:
    nk = unicodedata.normalize("NFD", texto or "")
    return "".join(c for c in nk if unicodedata.category(c) != "Mn")


def _norm(texto: str) -> str:
    t = _sin_acentos(texto).casefold()
    return re.sub(r"\s+", " ", t).strip()


def limpiar_rfc(valor: str) -> str:
    rfc = re.sub(r"\s+", "", valor or "").upper()
    if not RFC_RE.fullmatch(rfc):
        raise ValueError(f"RFC con estructura rara: {rfc}")
    return rfc


def limpiar_nombre(valor: str) -> str:
    nombre = re.sub(r"\s+", " ", valor or "").strip().upper()
    if len(nombre) < 5:
        raise ValueError("El nombre SAT debe ir completo: NOMBRE APELLIDO APELLIDO")
    if "|" in nombre:
        raise ValueError("El nombre no puede llevar |")
    return nombre


def armar_txt(rfc: str, nombre: str, cps: list[str], etiqueta: str = "cps") -> tuple[str, str, int]:
    rfc = limpiar_rfc(rfc)
    nombre = limpiar_nombre(nombre)
    if not cps:
        raise ValueError("No hay códigos postales para armar el TXT.")
    lineas = [f"{i}|{rfc}|{nombre}|{cp}" for i, cp in enumerate(cps, start=1)]
    contenido = "\r\n".join(lineas) + "\r\n"
    slug = re.sub(r"[^A-Z0-9]+", "_", _sin_acentos(etiqueta).upper()).strip("_")[:40]
    archivo = f"{rfc}_{slug or 'cps'}.txt"
    return archivo, contenido, len(lineas)


def generar_txt(rfc: str, nombre: str, cps: list[str], etiqueta: str = "cps") -> Path:
    archivo, contenido, _n = armar_txt(rfc, nombre, cps, etiqueta)
    SALIDA.mkdir(exist_ok=True)
    destino = SALIDA / archivo
    destino.write_bytes(contenido.encode("utf-8"))
    return destino


def _decodificar(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("cp1252", errors="replace")


def _tipo_mensaje(msg: str) -> str:
    """El SAT distingue nombre+CP mal vs solo nombre (el CP de esa línea sí pegó)."""
    m = _norm(msg)
    if "susceptible de recibir facturas" in m:
        return "ok"
    if "estructura del rfc" in m:
        return "estructura"
    if "no registrado" in m:
        return "no_padron"
    nombre_mal = "nombre" in m or "razon social" in m
    cp_en_msg = " y cp" in m or " y codigo postal" in m or "codigo postal" in m
    no_coinc = "no coinciden" in m or "no coincide" in m
    if nombre_mal and cp_en_msg and no_coinc:
        return "ambos"
    if nombre_mal and no_coinc:
        return "nombre_cp_ok"
    if "codigo postal" in m and no_coinc:
        return "cp"
    return "otra"


def leer_respuesta(raw: bytes) -> dict:
    texto = _decodificar(raw)
    lineas = []
    ok = []
    nombre_cp_ok = []
    n_cp = n_ambos = n_estructura = n_otras = 0

    for cruda in texto.splitlines():
        linea = cruda.strip()
        if not linea or linea.startswith("#"):
            continue
        partes = [p.strip() for p in linea.split("|")]
        if len(partes) < 3:
            continue
        rec = {
            "n": partes[0],
            "rfc": partes[1].upper() if len(partes) > 1 else "",
            "nombre": partes[2] if len(partes) >= 5 else "",
            "cp": partes[3] if len(partes) >= 5 else "",
            "mensaje": partes[-1],
        }
        if len(partes) == 4 and len(partes[3]) == 5 and partes[3].isdigit():
            rec["nombre"] = partes[2]
            rec["cp"] = partes[3]
            rec["mensaje"] = ""
        rec["tipo"] = _tipo_mensaje(rec["mensaje"])
        if rec["tipo"] == "ok":
            ok.append(rec)
        elif rec["tipo"] == "nombre_cp_ok":
            nombre_cp_ok.append(rec)
        elif rec["tipo"] == "estructura":
            n_estructura += 1
        elif rec["tipo"] == "ambos":
            n_ambos += 1
        elif rec["tipo"] == "cp":
            n_cp += 1
        else:
            n_otras += 1
        lineas.append(rec)

    total = len(lineas)
    if not total:
        return {
            "ok": False,
            "estado": "vacio",
            "titulo": "El archivo no tiene renglones del SAT.",
            "detalle": "Suba el TXT que descarga el validador masivo.",
            "hits": [],
            "total": 0,
        }

    if ok:
        hit = ok[0]
        extras = len(ok) - 1
        detalle = f"Nombre SAT correcto. De {total} CPs probados, coincidió {hit['cp']}."
        if extras:
            detalle += f" (otras {extras} líneas también salieron válidas; se toma la primera)"
        return {
            "ok": True,
            "estado": "encontrado",
            "titulo": f"CP fiscal: {hit['cp']}",
            "detalle": detalle,
            "rfc": hit["rfc"],
            "nombre": hit["nombre"],
            "cp": hit["cp"],
            "mensaje": hit["mensaje"],
            "hits": ok,
            "total": total,
            "conteo": {
                "ok": len(ok),
                "nombre_cp_ok": len(nombre_cp_ok),
                "ambos": n_ambos,
                "cp": n_cp,
                "estructura": n_estructura,
                "otras": n_otras,
            },
        }

    if nombre_cp_ok:
        hit = nombre_cp_ok[0]
        return {
            "ok": True,
            "estado": "revisar_nombre",
            "titulo": f"CP fiscal: {hit['cp']}",
            "detalle": (
                f"El SAT validó el código postal {hit['cp']}, pero el nombre no coincide "
                f"con el RFC. Revise el nombre (doble letra, acentos, José/Jose, orden) "
                f"antes de timbrar. El que se envió fue: {hit['nombre']}."
            ),
            "rfc": hit["rfc"],
            "nombre": hit["nombre"],
            "cp": hit["cp"],
            "mensaje": hit["mensaje"],
            "hits": nombre_cp_ok,
            "total": total,
            "conteo": {
                "ok": 0,
                "nombre_cp_ok": len(nombre_cp_ok),
                "ambos": n_ambos,
                "cp": n_cp,
                "estructura": n_estructura,
                "otras": n_otras,
            },
        }

    if n_estructura == total:
        return {
            "ok": False,
            "estado": "estructura",
            "titulo": "El SAT leyó solo el RFC (botón equivocado).",
            "detalle": (
                "Marque la casilla «Validar RFC, nombre, denominación o razón social y CP» "
                "y use Validación masiva de RFC, Nombre y Código Postal. El mismo TXT sirve."
            ),
            "rfc": lineas[0]["rfc"],
            "hits": [],
            "total": total,
            "conteo": {"estructura": n_estructura},
        }

    if n_ambos == total:
        return {
            "ok": False,
            "estado": "nombre",
            "titulo": "Ni el nombre ni el CP coincidieron.",
            "detalle": (
                "En ninguna línea pegó el código postal. Corrija el nombre "
                "(como en la constancia) y vuelva a generar el TXT; "
                "con el nombre mal el SAT casi no aísla el CP."
            ),
            "rfc": lineas[0]["rfc"],
            "nombre": lineas[0]["nombre"],
            "hits": [],
            "total": total,
            "conteo": {"ambos": n_ambos},
        }

    if n_cp == total:
        return {
            "ok": False,
            "estado": "fuera",
            "titulo": "El CP fiscal no está en esa búsqueda.",
            "detalle": (
                "El nombre sí coincidió con el SAT. El domicilio fiscal no está "
                "en los municipios (o el estado) que eligió. Amplíe la búsqueda."
            ),
            "rfc": lineas[0]["rfc"],
            "nombre": lineas[0]["nombre"],
            "hits": [],
            "total": total,
            "conteo": {"cp": n_cp},
        }

    return {
        "ok": False,
        "estado": "mixto",
        "titulo": "No salió un CP válido.",
        "detalle": (
            f"Renglones: {total}. Nombre y CP mal: {n_ambos}. "
            f"Solo CP mal: {n_cp}. Estructura: {n_estructura}. Otras: {n_otras}."
        ),
        "rfc": lineas[0]["rfc"],
        "hits": [],
        "total": total,
        "conteo": {
            "ok": 0,
            "nombre_cp_ok": len(nombre_cp_ok),
            "ambos": n_ambos,
            "cp": n_cp,
            "estructura": n_estructura,
            "otras": n_otras,
        },
    }
