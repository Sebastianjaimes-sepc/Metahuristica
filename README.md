# Metahuristica

📦 **Resumen**

Proyecto de heurística (Algoritmo Genético) para el problema de ruteo con ventanas horarias y asignación de muelles. El código carga instancias en formato AMPL `.dat`, valida parámetros, genera soluciones iniciales y ejecuta operadores genéticos (RBX, cut-and-fill, swap, insert). Los parámetros del problema son inmutables y se toman del archivo `.dat`.

---

## ⚙️ Requisitos

- Python 3.10+ (o 3.8+ recomendado)
- Dependencias: listadas en `requirements.txt` (instalar con pip)

Instalación rápida:

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

---

## 📁 Estructura principal

- `notebooks/` — notebooks de análisis y carga de datos
- `src/data_loader.py` — parser de archivos AMPL `.dat` y construcción de la instancia
- `src/encoding.py` — representación (vector único con `0`=depósito) y operadores GA (RBX, cut-and-fill, swap, insert)
- `scripts/run_ga.py` — script CLI demo para cargar la instancia y probar operadores
- `tests/` — pruebas unitarias básicas (usar `pytest`)
- `requirements.txt` — dependencias del proyecto

---

## 🗂️ Datos / Formato

Coloca tu archivo AMPL `.dat` (la instancia) en una ruta accesible y úsala con el script CLI. El parser soporta:
- vectores tipo `param DemE := 0 0 1 6 ... ;`
- matrices tipo `param Dist : 0 1 2 := ... ;`
- bloques 3D para `tvia` como en la instancia de ejemplo `[*,*,f]: ... :=`.

> Nota: los parámetros dentro del `.dat` (capacidad, costos, penalizaciones, franjas, etc.) **no se modifican por el script** — deben editarse en el `.dat` si se requiere otro escenario.

---

## ▶️ Uso (CLI)

Ejemplo básico para ejecutar el demo de operadores y validar la carga de la instancia:

```powershell
$env:PYTHONPATH = 'c:\Users\sjaim\Metahuristica'
python scripts/run_ga.py --dat "C:\ruta\a\instancia_generada.dat" --pop 20 --seed 1 --demo
```

Parámetros útiles:
- `--dat` (obligatorio): ruta(s) al/los `.dat` de la instancia. Puedes pasar varios caminos separados o un patrón.
- `--pop`: tamaño de la población inicial (por defecto 20)
- `--seed`: semilla aleatoria
- `--demo`: ejecuta demostración de operadores y sale
- `--run`: ejecutar GA (guardará resultados)
- `--popsize` / `--gens`: tamaño de población y generaciones cuando se usa `--run`

### Ejecutar varias instancias (batch)

Coloca tus `.dat` en una carpeta, o pásalos directamente, y usa el script de lotes:

```powershell
# Ejecutar todas las instancias en un directorio
python scripts/batch_run.py --dir "C:\ruta\a\mis_dat" --popsize 50 --gens 100 --seed 1

# Ejecutar archivos concretos (ruta absoluta o relativa)
python scripts/batch_run.py --paths "C:\inst1.dat" "D:\otros\inst2.dat" --popsize 50 --gens 100

# Ejecutar usando un archivo con líneas que contienen rutas
python scripts/batch_run.py --list dat_paths.txt --popsize 50 --gens 100
```

> El script crea subdirectorios en `results/<nombre_instancia>/` y ejecuta `scripts/run_ga.py` por cada archivo encontrado.

### Cómo interpretar la salida del demo

- Los individuos se muestran como **vectores** donde `0` es el depósito y separa las rutas. Ejemplo:

  - Vector: `[0, 7, 9, 10, 8, 0, 6, 4, 1, 0, 5, 2, 3, 0]` → Rutas: `[7,9,10,8]`, `[6,4,1]`, `[5,2,3]`.

- Bloques que verás en el demo:
  - **Demostración RBX**: muestra Padre A, Padre B y el Hijo resultante del crossover basado en rutas.
  - **Demostración Cut-and-fill**: muestra el Hijo generado por el operador cut-and-fill (corte + rellenado con orden del otro padre).
  - **Mutación Swap/Insert**: ejemplos de mutaciones aplicadas a un individuo (intercambio o inserción de clientes).

- Interés práctico: estos prints permiten verificar que los operadores preservan la estructura (cada cliente aparece una vez y se mantiene el número de rutas).

- Para decodificar programáticamente un vector a rutas usa:

```python
from src.encoding import decode_vector
print(decode_vector([0,7,9,10,8,0,6,4,1,0,5,2,3,0]))
```

---

## 📈 Resultados y dónde buscarlos

- El demo imprime en consola los individuos de la población y ejemplos de cruces/mutaciones.
- Próximamente se agregará: generación de ficheros `results/*.json` y `results/*.csv` con la mejor solución, desglose de costos, asignación de muelles y métricas de factibilidad.

---

## ✅ Probar y depurar

- Ejecutar tests:

```bash
python -m pytest -q
```

- Para desarrollos iterativos usar el notebook `notebooks/01_data_loader_and_validation.ipynb` para comprobar la lectura de parámetros y visualización rápida de nodos.

---

## 🛠️ Siguientes pasos implementados / planeados

He implementado:
- Parser `.dat` y validación básica
- Dataclasses (`Client`, `Truck`, `Instance`)
- Encodings y operadores GA (RBX, cut-and-fill, swap, insert)

En curso / por implementar:
- Simulador de rutas y chequeo de factibilidad (capacidad temporal, ventanas, almuerzo, muelles)
- Scheduler de muelles usando pesos w1..w5
- Función objetivo Z y evaluación completa
- Bucle GA, control de diversidad y búsqueda local
- Exportar resultados a CSV/JSON y notebooks de análisis

---

## 💬 Contacto / Ayuda

Si quieres que avance con el simulador y la evaluación completa, dime:
1) ¿Aplicamos búsqueda local en cada generación o sólo en la última (menos costoso)?
2) ¿Generamos archivos `results/` automáticamente o prefieres ver todo primero por consola?


---

© Proyecto Metahuristica
