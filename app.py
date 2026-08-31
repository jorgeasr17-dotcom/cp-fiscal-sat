# -*- coding: utf-8 -*-
"""
Validar CP fiscal con el validador masivo del SAT.

    python app.py
    http://127.0.0.1:5099
"""
from __future__ import annotations

from flask import Flask, jsonify, render_template, request

import catalogo
import motor

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
app.config["TEMPLATES_AUTO_RELOAD"] = True
PUERTO = 5099


@app.after_request
def _no_cache(resp):
    ct = resp.content_type or ""
    if "text/html" in ct or "stylesheet" in ct or "javascript" in ct:
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.get("/")
def index():
    return render_template(
        "index.html",
        sat_url=motor.SAT_URL,
        sat_max=catalogo.SAT_MAX,
        n_estados=len(catalogo.estados()),
        puerto=PUERTO,
    )


@app.get("/api/estados")
def api_estados():
    return jsonify({"ok": True, "estados": catalogo.estados()})


@app.get("/api/municipios")
def api_municipios():
    estado = (request.args.get("estado") or "").strip()
    try:
        items = catalogo.municipios(estado)
        n_cps_estado = catalogo.n_cps_estado(estado)
        nombre_estado = catalogo._estado(estado)["nombre"]
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(
        {
            "ok": True,
            "municipios": items,
            "estado": nombre_estado,
            "n_cps_estado": n_cps_estado,
        }
    )


@app.post("/api/generar")
def api_generar():
    rfc = (request.form.get("rfc") or "").strip()
    nombre = (request.form.get("nombre") or "").strip()
    estado = (request.form.get("estado") or "").strip()
    munis = [m for m in request.form.getlist("municipios") if m.strip()]
    try:
        if not estado:
            raise ValueError("Elija un estado.")
        cps, usados = catalogo.cps_de(estado, munis)
        if usados:
            etiqueta = usados[0] if len(usados) == 1 else f"{estado}_{len(usados)}mun"
        else:
            etiqueta = estado
        archivo, txt, n = motor.armar_txt(rfc, nombre, cps, etiqueta)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    return jsonify(
        {
            "ok": True,
            "archivo": archivo,
            "lineas": n,
            "rfc": motor.limpiar_rfc(rfc),
            "nombre": motor.limpiar_nombre(nombre),
            "estado": estado,
            "municipios": usados,
            "txt": txt,
        }
    )


@app.post("/api/leer")
def api_leer():
    fh = request.files.get("file")
    if not fh:
        return jsonify({"ok": False, "error": "No llegó el archivo del SAT."}), 400
    raw = fh.read()
    if not raw:
        return jsonify({"ok": False, "error": "El archivo está vacío."}), 400
    return jsonify(motor.leer_respuesta(raw))


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PUERTO, debug=False)
