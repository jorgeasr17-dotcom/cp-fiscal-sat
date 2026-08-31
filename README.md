# CP fiscal SAT

App local para encontrar el **código postal fiscal** de un RFC con el [validador masivo del SAT](https://www.sat.gob.mx/aplicacion/79615/valida-en-linea-rfc%C2%B4s-uno-a-uno-o-de-manera-masiva-hasta-5-mil-registros).

El SAT no entrega el CP: hay que probar candidatos. Esta herramienta arma un TXT con los CPs de un **estado** (o de uno o más **municipios**) y lee la respuesta.

No guarda RFC ni nombres. El SAT se consulta a mano (lleva captcha).

## Uso

```
python -m pip install -r requirements.txt
python app.py
```

Abre [http://127.0.0.1:5099](http://127.0.0.1:5099). En Windows también: `Abrir_ValidarCP.bat`.

1. Estado (obligatorio). Municipio opcional: si lo dejas vacío, busca todo el estado.
2. RFC y nombre SAT → **Generar TXT**.
3. En el SAT: casilla *Validar RFC, nombre y CP* → validación masiva → sube el TXT.
4. Suelta aquí el archivo que baja el SAT.

El SAT acepta **hasta 5,000 renglones** por archivo. Ningún estado de México llega a ese tope.

Si el nombre no coincide pero el CP sí, la app muestra el CP y pide revisar el nombre (p. ej. Villareal vs Villarreal).

## Catálogo

`data/catalogo_cp.json` sale del Catálogo Nacional de Códigos Postales de **Correos de México / SEPOMEX**. Para regenerarlo:

1. Baja `CPdescarga.txt` desde [datos abiertos de Correos](https://www.correosdemexico.gob.mx/datosabiertos/cp/cpdescarga.txt).
2. Ponlo en `data/CPdescarga.txt`.
3. `python build_catalogo.py`

Ese TXT grande no va en el repositorio.

## Licencia de datos

El catálogo de CPs es de Correos de México, de uso particular y **no comercializable**. Cite la fuente. El código de esta app queda a cargo de quien lo publique.
