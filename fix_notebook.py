#!/usr/bin/env python3

# Script para arreglar las rutas del notebook

notebook_path = r'C:\Users\sjaim\Metahuristica\notebooks\02_GA_Tutorial_Paso_a_Paso.ipynb'

with open(notebook_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar la ruta antigua por la nueva
content = content.replace(
    "sys.path.insert(0, '/root/Metahuristica')",
    "sys.path.insert(0, r'C:\\Users\\sjaim\\Metahuristica')"
)

with open(notebook_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Notebook actualizado correctamente")
