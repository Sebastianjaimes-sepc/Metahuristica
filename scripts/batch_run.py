"""Script de ayuda para ejecutar por lotes varias instancias .dat.
Acepta rutas individuales, un directorio, o un archivo con lista de rutas.
Llama a `scripts/run_ga.py` para cada instancia y guarda los resultados en `results/<basename>/`.
"""
import argparse
import subprocess
import os
import glob


def gather_paths(paths, dir_path, list_file):
    out = []
    if dir_path:
        p = os.path.abspath(dir_path)
        out.extend(glob.glob(os.path.join(p, '*.dat')))
    if paths:
        for p in paths:
            out.append(p)
    if list_file:
        with open(list_file, 'r', encoding='utf-8') as f:
            for line in f:
                line=line.strip()
                if line:
                    out.append(line)
    # deduplicate and keep absolute
    out = [os.path.abspath(p) for p in dict.fromkeys(out)]
    return out


def main():
    parser = argparse.ArgumentParser(description='Ejecutar múltiples instancias .dat en lote')
    parser.add_argument('--paths', nargs='*', help='Rutas a archivos .dat (uno o varios)')
    parser.add_argument('--dir', help='Directorio con archivos .dat a ejecutar')
    parser.add_argument('--list', help='Archivo de texto con rutas a .dat (una por línea)')
    parser.add_argument('--popsize', type=int, default=50)
    parser.add_argument('--gens', type=int, default=100)
    parser.add_argument('--seed', type=int, default=1)
    parser.add_argument('--out', type=str, default='results')
    args = parser.parse_args()

    files = gather_paths(args.paths, args.dir, args.list)
    if not files:
        print('No se encontraron archivos .dat. Proporciona --paths, --dir o --list')
        return

    for f in files:
        base = os.path.splitext(os.path.basename(f))[0]
        outdir = os.path.join(args.out, base)
        os.makedirs(outdir, exist_ok=True)
        cmd = ['python', 'scripts/run_ga.py', '--dat', f, '--run', '--popsize', str(args.popsize), '--gens', str(args.gens), '--seed', str(args.seed), '--out', outdir]
        print('Ejecutando:', ' '.join(cmd))
        subprocess.run(cmd)

if __name__ == '__main__':
    main()
