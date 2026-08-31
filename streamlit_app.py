# -*- coding: utf-8 -*-
"""Versión Streamlit Cloud de CP fiscal SAT. Misma lógica que app.py (Flask)."""
from __future__ import annotations

import streamlit as st

import catalogo
import motor

st.set_page_config(page_title="CP fiscal SAT", page_icon="📍", layout="centered")

st.title("CP fiscal SAT")
st.caption(
    "El SAT no entrega el CP: se prueba por estado o municipio. "
    "No se guarda RFC ni nombres."
)

estados = catalogo.estados()
nombres_estado = [e["nombre"] for e in estados]
n_cps_map = {e["nombre"]: e["n_cps"] for e in estados}

estado = st.selectbox("Estado", [""] + nombres_estado, format_func=lambda x: "Coloca aquí el estado" if x == "" else f"{x} ({n_cps_map.get(x, 0)} CPs)")

munis = catalogo.municipios(estado) if estado else []
opciones_mun = [m["nombre"] for m in munis]
n_mun = {m["nombre"]: m["n_cps"] for m in munis}

seleccion = st.multiselect(
    "Municipio (opcional — vacío = todo el estado)",
    opciones_mun,
    format_func=lambda n: f"{n} ({n_mun.get(n, 0)})",
    disabled=not estado,
)

if estado and not seleccion:
    st.info(f"Sin municipio: se buscan los **{n_cps_map.get(estado, 0)} CPs** de todo {estado}.")
elif seleccion:
    st.info("CPs a probar: " + ", ".join(f"{n} ({n_mun.get(n, 0)})" for n in seleccion))

rfc = st.text_input("RFC", placeholder="Coloca aquí el RFC", max_chars=13)
nombre = st.text_input("Nombre SAT", placeholder="Coloca aquí el nombre SAT")

st.markdown(
    f"En el [validador del SAT]({motor.SAT_URL}): **Ejecutar en línea** → captcha → "
    "casilla **Validar RFC, nombre y CP** → validación masiva."
)

col1, col2 = st.columns(2)
with col1:
    generar = st.button("Generar TXT", type="primary", disabled=not estado)

if generar:
    try:
        cps, usados = catalogo.cps_de(estado, seleccion)
        etiqueta = usados[0] if len(usados) == 1 else (estado if not usados else f"{estado}_{len(usados)}mun")
        archivo, txt, n = motor.armar_txt(rfc, nombre, cps, etiqueta)
        st.session_state["txt"] = txt
        st.session_state["archivo"] = archivo
        st.session_state["lineas"] = n
        st.success(f"{n} líneas · {archivo}")
    except ValueError as exc:
        st.error(str(exc))

if st.session_state.get("txt"):
    st.download_button(
        "Descargar TXT",
        data=st.session_state["txt"].encode("utf-8"),
        file_name=st.session_state["archivo"],
        mime="text/plain",
    )

st.subheader("Respuesta del SAT")
archivo_sat = st.file_uploader("Suelte el TXT que bajó el SAT", type=["txt"])
if archivo_sat is not None:
    data = motor.leer_respuesta(archivo_sat.getvalue())
    if data.get("ok") and data.get("cp"):
        if data.get("estado") == "revisar_nombre":
            st.warning("Revise el nombre · CP encontrado")
        else:
            st.success("CP fiscal")
        st.markdown(f"# `{data['cp']}`")
        st.write(f"**{data.get('rfc', '')}** · {data.get('nombre', '')}")
        st.caption(data.get("detalle", ""))
    else:
        st.error(data.get("titulo") or "No se pudo leer")
        st.write(data.get("detalle") or data.get("error") or "")
        if data.get("estado") == "fuera":
            st.caption("Si acotó por municipio, búsque todo el estado o agregue uno cercano.")
