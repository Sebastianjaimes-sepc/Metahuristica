"""Script CLI simple para probar el cargador de datos y los operadores GA.
Este script carga el .dat, construye la instancia, genera una población inicial y muestra operadores genéticos de ejemplo.
"""
import argparse
import random
import json
from src.data_loader import parse_ampl_dat, build_instance
from src.encoding import encode_routes, route_based_crossover, cut_and_fill, swap_mutation, insert_mutation, decode_vector
from src.simulator import evaluate_individual
from copy import deepcopy
import os


def random_initial_population(inst, pop_size=10, seed=None):
    rng = random.Random(seed)
    client_ids = [nid for nid, c in inst.clients.items() if c.escliente == 1]
    R = len(inst.trucks)
    population = []
    for _ in range(pop_size):
        perm = client_ids[:]
        rng.shuffle(perm)
        # dividir en R rutas de forma aproximadamente uniforme
        routes = []
        base = len(perm)//R
        rem = len(perm)%R
        idx = 0
        for r in range(R):
            size = base + (1 if r < rem else 0)
            routes.append(perm[idx:idx+size])
            idx += size
        population.append(encode_routes(routes))
    return population


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dat', required=True, nargs='+', help='Rutas a uno o más archivos AMPL .dat (se pueden pasar varias, o un patrón de archivos)')
    parser.add_argument('--pop', type=int, default=20)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--demo', action='store_true', help='Ejecutar demostración de operadores y salir')
    parser.add_argument('--run', action='store_true', help='Ejecutar GA simple (guardará resultados en results/)')
    parser.add_argument('--gens', type=int, default=50, help='Número de generaciones (cuando se usa --run)')
    parser.add_argument('--popsize', type=int, default=50, help='Tamaño de población (cuando se usa --run)')
    parser.add_argument('--out', type=str, default='results', help='Directorio donde guardar resultados')
    args = parser.parse_args()

    # support multiple .dat files: procesar uno a uno
    for dat_path in args.dat:
        print('\nProcesando instancia:', dat_path)
        parsed = parse_ampl_dat(dat_path)
        inst = build_instance(parsed)
        print('Instancia cargada: nodos=', inst.n_nodes(), 'camiones=', len(inst.trucks))

        pop = random_initial_population(inst, pop_size=args.pop, seed=args.seed)
        print('\nIndividuos ejemplo (3 primeros):')
        for i in range(min(3,len(pop))):
            print(i, pop[i])

        if args.demo:
            a,b = pop[0], pop[1]
            print('\nDemostración RBX:')
            print('Padre A:',a)
            print('Padre B:',b)
            child = route_based_crossover(a,b)
            print('Hijo (RBX):',child)
            print('\nDemostración Cut-and-fill:')
            print('Hijo (Cut-and-fill):', cut_and_fill(a,b))
            print('\nDemostración Swap/Insert sobre el hijo:')
            c1 = swap_mutation(child)
            c2 = insert_mutation(child)
            print('Mutación Swap:', c1)
            print('Mutación Insert:', c2)

        if args.run:
            # modo GA simple
            popsize = args.popsize
            gens = args.gens
            # crear subdirectorio por instancia
            base = os.path.splitext(os.path.basename(dat_path))[0]
            outdir = os.path.join(args.out, base)
            os.makedirs(outdir, exist_ok=True)
            # init population
            population = random_initial_population(inst, pop_size=popsize, seed=args.seed)
            # evaluate
            def evaluate_population(pop):
                fitness = []
                for ind in pop:
                    r = evaluate_individual(ind, inst)
                    fitness.append(r['Z'])
                return fitness

            fitness = evaluate_population(population)
            best_idx = min(range(len(population)), key=lambda i: fitness[i])
            best = deepcopy(population[best_idx])
            best_score = fitness[best_idx]
            print(f'Generación 0: mejor Z = {best_score}')
        for g in range(1, gens+1):
            newpop = []
            # elitismo (2)
            sorted_idx = sorted(range(len(population)), key=lambda i: fitness[i])
            elites = [deepcopy(population[sorted_idx[0]]), deepcopy(population[sorted_idx[1]])]
            while len(newpop) < popsize - 2:
                # selección torneo k=3
                i1 = random.sample(range(len(population)), 3)
                p1 = min(i1, key=lambda i: fitness[i])
                i2 = random.sample(range(len(population)), 3)
                p2 = min(i2, key=lambda i: fitness[i])
                parent_a = population[p1]
                parent_b = population[p2]
                # cruce RBX con prob 0.85
                if random.random() < 0.85:
                    child = route_based_crossover(parent_a, parent_b)
                else:
                    child = deepcopy(parent_a)
                # mutación 10%
                if random.random() < 0.10:
                    mtype = random.random()
                    if mtype < 0.70:
                        child = swap_mutation(child)
                    elif mtype < 0.90:
                        child = insert_mutation(child)
                    else:
                        child = cut_and_fill(child, parent_b)
                newpop.append(child)
            newpop.extend(elites)
            population = newpop
            fitness = evaluate_population(population)
            cur_best_idx = min(range(len(population)), key=lambda i: fitness[i])
            cur_best_score = fitness[cur_best_idx]
            if cur_best_score < best_score:
                best_score = cur_best_score
                best = deepcopy(population[cur_best_idx])
            # si es la última generación, aplicar búsqueda local simple (ordenar rutas internamente por ventana mínima)
            if g == gens:
                new_best = deepcopy(best)
                # aplicar búsqueda local: para cada ruta, ordenar por MinDC
                routes = [r for r in decode_vector(new_best)]
                new_routes = []
                for r in routes:
                    new_routes.append(sorted(r, key=lambda c: inst.clients[c].MinDC))
                new_best = encode_routes(new_routes)
                new_eval = evaluate_individual(new_best, inst)
                if new_eval['Z'] < best_score:
                    best = new_best
                    best_score = new_eval['Z']
            if g % 10 == 0 or g==1 or g==gens:
                print(f'Generación {g}: mejor Z = {best_score}')

        # guardar resultado
        res = evaluate_individual(best, inst)
        outpath = os.path.join(outdir, 'best_solution.json')
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump({'Z': res['Z'], 'cost': res['cost'], 'penalty': res['penalty'], 'routes': res['routes'], 'scheduled': res['scheduled']}, f, indent=2)
        print('Mejor solución guardada en', outpath)

if __name__ == '__main__':
    main()
