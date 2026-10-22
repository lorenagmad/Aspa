# Aspa · exámenes tipo test

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23571010.svg)](https://doi.org/10.5281/zenodo.23571010)

*[English version](README.md)*

Aplicación local (se abre en el navegador) para preparar, imprimir, leer y corregir
exámenes tipo test.
Funciona en Windows, macOS y Linux. No necesita Excel ni conexión a internet una vez instalada.

## Instalación y arranque

1. Instale **Python 3.9 o superior** desde <https://www.python.org/downloads/>.
   En Windows, marque «Add Python to PATH» durante la instalación.
2. Descomprima esta carpeta donde quiera, por ejemplo `C:\Examenes\corrector`.
3. Arranque la aplicación:
   - **Windows:** doble clic en `iniciar.bat`.
   - **macOS:** doble clic en `iniciar.command`. Si el sistema lo bloquea por venir de internet,
     clic derecho → Abrir, o en Terminal: `bash iniciar.command`.
   - **Linux:** `./iniciar.sh`.

La primera vez tarda un par de minutos porque instala las librerías. Después se abre el
navegador en `http://127.0.0.1:5077`.

Para terminar, pulse **«Cerrar Aspa»** (arriba a la derecha): el programa se detiene y la
ventana de la consola se cierra. Los navegadores no permiten que una página cierre su propia
pestaña, así que esa pestaña se cierra a mano. Si vuelve a abrir Aspa cuando ya estaba en
marcha, simplemente se abre otra pestaña con él.

Los exámenes se guardan en la carpeta `ExamenesTest` de su usuario. Para usar otra carpeta
(por ejemplo, una compartida con otros profesores):

```
iniciar.bat --carpeta "D:\Departamento\Examenes"
```

### Idiomas

Aspa está en **español e inglés**. Hay dos ajustes independientes:

- **Idioma de Aspa** (pantallas, avisos, ayudas, plantillas Excel y Excel de notas): se elige en
  el desplegable de la pantalla de inicio o en el de la barra superior, y se recuerda para la
  próxima vez.
- **Idioma del examen impreso** (hoja de respuestas, instrucciones, ficha del alumno, soluciones):
  se elige en cada examen, al crearlo o en el paso 2. Así se puede usar Aspa en español e imprimir
  un examen en inglés para un grupo internacional. Las preguntas se imprimen tal como están en el
  banco. Si las instrucciones para el alumno se dejan vacías, se usa el texto estándar en el idioma
  del examen.

Aspa lee las plantillas en cualquiera de los dos idiomas (cabeceras «pregunta/question»,
«correcta/correct»…), y reconoce «All of the above» y «None of the above» como opciones fijas.

**Añadir un idioma** (por ejemplo, francés):

```
python herramientas/revisar_traducciones.py fr --nuevo "Français"
```

Crea `idiomas/fr.json` con todos los textos del programa. Hay que rellenar cada valor con su
traducción, poner en `"_decimal"` el separador decimal del idioma (`,` en francés), copiar la
carpeta `templates/ayuda/en` como `templates/ayuda/fr` y traducir esas tres páginas. Al reiniciar
Aspa, el idioma aparece en el desplegable de idiomas. Mientras falte algo (un texto o una página de
ayuda), se muestra **en inglés**, así que se puede ir traduciendo poco a poco. Para ver qué falta (por ejemplo, tras
una actualización de Aspa):

```
python herramientas/revisar_traducciones.py fr                # lista lo que falta
python herramientas/revisar_traducciones.py fr --actualizar   # añade los textos nuevos al fichero
```

### Menú de cada examen

El menú de la izquierda muestra los seis pasos. El paso en el que está se resalta (también al
desplazarse por los pasos 1 a 3, que están en la misma página) y los completados llevan una ✓.
Arriba del menú, «← Todos los exámenes» vuelve a la pantalla de inicio. Al terminar el paso 3
se indica que el paso 4 se hace cuando el examen ya esté hecho y escaneado.

### Pantalla de inicio

- **Nuevo examen:** título corto (Evaluación global, Llamamiento especial, Parcial…),
  asignatura, convocatoria (Febrero, Junio, Septiembre, Diciembre u «Otra…» para escribir una
  distinta) y curso (AAAA-AAAA; se propone el curso académico actual y se comprueba el formato,
  aceptando también 2026/27 o 2026-27). Se puede partir de un examen anterior para reutilizar sus
  preguntas, alumnos y configuración.
- **Cabecera impresa:** el examen lleva «Asignatura · Título» y debajo «Convocatoria Curso ·
  Subtítulo». Si el nombre es muy largo se reduce la letra y, si hace falta, se abrevia la
  asignatura; el título del examen se ve siempre entero.
- **Plantillas y ayuda:** para el banco de preguntas y para la lista de alumnos hay una página
  que explica cómo rellenarlos (respuestas múltiples, grupos y modelos, opciones fijas…), una
  plantilla limpia y otra con ejemplos. También están en la carpeta `ejemplos/`.
- **Lista de exámenes:** filtros por estado (en preparación, generado, en corrección, corregido),
  asignatura, convocatoria y curso, y búsqueda por título.
- **Borrar:** marque los exámenes y pulse «Mover a la papelera». No se borran del todo: se
  guardan en la carpeta `.papelera` dentro de la carpeta de exámenes y se pueden recuperar
  moviéndolos de vuelta.

## Flujo de trabajo

1. **Crear el examen** (se puede partir de uno anterior: se copian preguntas, alumnos y configuración).
2. **Paso 1:** subir el banco de preguntas y la lista de clase (y, si hace falta, las imágenes).
3. **Paso 2:** configuración: tipo de examen, idioma del examen impreso, puntuación y modelos. Cada
   modelo indica cuántas preguntas tiene disponibles.
4. **Paso 3:** generar el PDF para imprimir y el PDF de soluciones por modelo.
5. **Paso 4:** arrastrar los escaneos al navegador; se leen y corrigen solos. En la pantalla de
   revisión se pulsa una casilla para cambiar una respuesta, y el «modo revisión con el alumno»
   sirve para enseñarle su examen. Para reutilizar un examen: «Borrar corrección» en opciones
   avanzadas, o crear uno nuevo a partir del anterior.
6. **Paso 5:** estadística por pregunta; anular preguntas o corregir claves.
7. **Paso 6:** exportar las notas a Excel.

### Tipos de examen

Al crear el examen (o en el paso 2) se elige el tipo:

- **Por modelos:** varios modelos (A, B, C…) y copias iguales de cada uno. El alumno marca su
  documento en la hoja.
- **Personalizado:** un examen por alumno de la lista, con su nombre y documento impresos en la
  hoja (no marca nada para identificarse) y sin las preguntas que ya tiene superadas en clase.
  - Las superadas se indican en la lista de alumnos, columna `superadas`, con los números de las
    preguntas que se quitan del examen (por ejemplo `2, 5, 7, 12`).
  - Lo más cómodo es un único Excel con las hojas `preguntas` y `alumnos`, subido en «Banco de
    preguntas»: la lista se toma de ahí. En la pantalla de inicio está la explicación y la
    plantilla («Exámenes personalizados»), también en `ejemplos/plantilla_personalizado.xlsx`.
  - Cada alumno va a un modelo que contenga todas sus superadas; si caben en varios, se reparten.
    Si ninguno las contiene todas, Aspa avisa en el paso 1 antes de generar.
  - Cada superada cuenta como un acierto completo y la nota se calcula sobre el examen completo
    (por ejemplo, 30 preguntas) y se pasa a 10.
  - Los alumnos sin superadas reciben el examen completo con su nombre impreso.
  - **Exámenes de reserva:** exámenes completos sin personalizar, con casillas para el documento,
    para quien no esté en la lista.
  - El PDF sale ordenado alfabéticamente; los de reserva, al final.

### Explicación de la respuesta correcta

La columna opcional `explicacion` del banco (en inglés, `explanation`) permite escribir por qué la
respuesta correcta lo es. En la pantalla de revisión aparece bajo la pregunta y sus opciones
**solo cuando el alumno no la ha acertado** (fallada, parcial, en blanco o pendiente de revisar);
la tabla de respuestas marca esas preguntas con ⓘ. Es útil en el modo revisión con el alumno.
No se imprime en el examen, y se puede añadir después de generarlo: basta con volver a subir el
banco.

### Imágenes

En el paso 1, «Imágenes del examen», se suben las imágenes que se imprimirán al final de cada
examen (en los dos tipos), en el orden de la lista y con su pie («Imagen 1»…). Las preguntas
hacen referencia a ellas por ese pie. Se puede subir una composición ya rotulada y dejar el pie
vacío.

### Banco de preguntas

Descargue la plantilla desde la pantalla de inicio (limpia o con ejemplos) o use
`ejemplos/plantilla_preguntas.xlsx`. Las dos llevan una hoja de instrucciones. Las columnas son:

`id | tema | pregunta | A | B | C | D | correcta | grupo | fija | explicacion`

- **correcta:** letras (`B`, `AC`). También se puede escribir con números (`2` = B, `13` = A y C).
- **grupo:** código para formar los modelos. Cada modelo toma las preguntas de los
  grupos que se le indiquen (por ejemplo, el modelo A usa los grupos `1,2`).
  - Si no llegan al número de preguntas del examen, el resto se completa **al azar entre las
    preguntas sin grupo**, de forma independiente en cada modelo. Por ejemplo, con 8 preguntas
    del grupo 1 en un examen de 20, la tabla de modelos indica «8 del modelo + 12 al azar».
  - Si hay más de las necesarias, se eligen al azar entre ellas.
  - Un modelo sin grupos toma todas sus preguntas al azar de todo el banco.
- **fija:** opciones que no se deben mover al desordenar. Las que empiezan por «Todas…» o
  «Ninguna…» ya se quedan fijas automáticamente.
- Si una pregunta tiene menos de cuatro opciones, deje vacías las últimas.

La lista de alumnos puede ser la que exporta el sistema de gestión académica de la universidad, sin tocar: la aplicación busca las columnas
del documento y del nombre (por ejemplo «Doc.» y «Apellidos y nombre»). También vale una hoja con las columnas `documento | nombre`.

### Imprimir y escanear

- Imprima a **doble cara**. Cada copia empieza en una hoja nueva (se añade una página en blanco
  si hace falta).
- Solo hace falta escanear la **primera página** de cada examen. Si se escanea todo, las páginas
  de preguntas y las páginas en blanco se ignoran solas.
- Sirven JPG, PNG, TIFF o PDF (una imagen por examen o un PDF con todos). Bastan 200 ppp en
  escala de grises.
- No recorte la hoja: los **cuatro cuadrados negros de las esquinas** deben verse enteros.
  Pueden estar torcidos o del revés; eso no es problema.

## La hoja de respuestas

Se ha rediseñado para eliminar los problemas de la anterior:

- **QR en lugar de la tira de cuadrados.** Contiene el código del examen, el modelo y el número
  de copia, con corrección de errores incluida. El modelo también va impreso en letra grande
  por si hiciera falta indicarlo a mano.
- **Cuatro marcadores en las esquinas.** Corrigen giro, inclinación, escala y perspectiva.
  Después, el lector localiza las casillas impresas reales y ajusta cada bloque a ellas, lo que
  absorbe la curvatura del papel y la distorsión de la lente cuando se fotografía con el móvil.
  También iguala la iluminación (sombras) antes de medir.
- **Documento de 10 dígitos.** Las casillas no llevan números dentro (los números estaban
  dentro de la zona que se mide y ensuciaban la lectura). Admite DNI, NIE y pasaportes, porque
  se comparan solo los dígitos con la lista de clase. Si falla un dígito, se propone el alumno
  más parecido y se marca para revisar. Si no aparece, se elige de una lista con buscador.
- **Casilla «Anular» separada** de A–D. Si está marcada, la pregunta queda «por revisar»
  hasta que el profesor indique la respuesta según lo escrito en el recuadro de aclaraciones.
  Las casillas rellenas del todo cuentan como marcadas.

Toda la geometría de la hoja está en `examtool/layout.py`. El generador de PDF y el lector la
comparten, así que un cambio de diseño se hace en un solo sitio.

## Puntuación

Se configura en el paso 2. Por defecto:

- **Acierto:** +1. **Fallo:** −0,1. **En blanco:** 0.
- **Varias correctas (modo parcial):** (aciertos − errores) / nº de correctas, sin bajar de 0.
  Si no acierta ninguna, cuenta como fallo. Por ejemplo, si la correcta es AB:
  marcar AB da 1; A da 0,5; AC da 0; C da −0,1. También existe el modo «solo exacta».
- **Nota:** sobre 10 (configurable), calculada sobre las preguntas no anuladas.
  Si se anula una pregunta, se reescala a las restantes.

Todas las notas se **recalculan al momento** cuando cambia algo: la penalización, una pregunta
anulada, una clave corregida o una revisión manual. Las revisiones manuales se guardan aparte
(`revision.json`) y nunca se pierden al volver a leer los escaneos.

## Qué hay en la carpeta de cada examen

```
proyecto.json   configuración
preguntas.xlsx  banco de preguntas    alumnos.xlsx  lista de clase
generado.json   orden de preguntas y opciones de cada modelo (se fija al generar)
examenes.pdf    para imprimir         soluciones.pdf  claves por modelo
escaneos/       lo que se sube        procesadas/     páginas enderezadas
lecturas.json   lo leído              revision.json   cambios manuales
notas.xlsx      exportación
```

Son ficheros de texto (JSON) y Excel normales, así que se pueden copiar, archivar o abrir.

**Importante:** no vuelva a generar un examen que ya está impreso. Cambiaría el orden de las
preguntas y las hojas impresas dejarían de corregirse bien. La aplicación pide confirmación.

## Herramientas para desarrollo

```
python herramientas/simular_escaneos.py <carpeta_examen> 40   # crea 40 hojas rellenadas simuladas
python herramientas/evaluar_simulacion.py <carpeta_examen>    # compara lo leído con lo simulado
python herramientas/revisar_traducciones.py en                # comprueba las traducciones
```

Resultado en la prueba con 40 hojas simuladas (aspas, rellenos, «vistos», bolígrafo flojo,
giros de ±4°, perspectiva, curvatura del papel, sombras, una hoja del revés, JPEG de baja calidad): 40/40 QR,
40/40 documentos y 800/800 respuestas leídas correctamente.

Los umbrales de lectura están en `proyecto.json` (`umbral_marca`, por defecto 0,11, y
`umbral_duda`, 0,04). Son la fracción de tinta en el centro de la casilla. Entre los dos valores,
la casilla se marca como «dudosa» para revisarla. Si en una hoja las casillas vacías ya dan algo
de tinta, los umbrales de esa hoja se suben automáticamente.

Prueba con 12 hojas reales rellenadas a mano y fotografiadas con el móvil (bolígrafo rojo,
negro y azul; aspas, «vistos», casillas rayadas; anulaciones): todas las respuestas y QR leídos
correctamente; las marcas que se salen de la casilla quedan como dudosas.

## Estructura del código

```
app.py                 aplicación web (Flask)
examtool/layout.py     geometría de la hoja
examtool/banco.py      lectura de preguntas y alumnos, emparejado de documentos
examtool/proyecto.py   proyectos, configuración y generación de modelos
examtool/pdf.py        PDF de exámenes y de soluciones
examtool/lector.py     lectura óptica (OpenCV: ArUco, QR, medida de tinta)
examtool/calificar.py  puntuación y estadística
examtool/exportar.py   Excel de notas
examtool/plantillas.py plantillas Excel y ejemplos de las páginas de ayuda
examtool/i18n.py       idiomas (los textos traducidos están en idiomas/*.json)
examtool/simulacion.py hojas simuladas para pruebas
```

## Pendiente

- Probar con más hojas reales impresas y escaneadas con distintos escáneres y móviles.

## Licencia

Aspa es software libre: puede redistribuirlo y modificarlo bajo los términos de la **GNU Affero
General Public License**, versión 3 o (a su elección) cualquier versión posterior, publicada por la
Free Software Foundation. Véase el fichero [`LICENSE`](LICENSE).

En la práctica, cualquier persona o institución puede usar, estudiar y modificar Aspa, pero si
distribuye una versión modificada, o la ofrece como servicio a través de una red, debe publicar
su código fuente con la misma licencia.

Aspa usa estas librerías, todas con licencias compatibles: Flask (BSD-3-Clause), OpenCV
(Apache-2.0), NumPy (BSD-3-Clause), ReportLab (BSD), openpyxl (MIT) y PyMuPDF (AGPL-3.0).

## Autores

- Lorena Gutiérrez Madroñal
- Rubén Baena Pérez
- José Miguel Mota Macías

## Cómo citar

Si usa Aspa en su docencia o investigación, cítelo con los datos de [`CITATION.cff`](CITATION.cff)
(GitHub los muestra en «Cite this repository»).

