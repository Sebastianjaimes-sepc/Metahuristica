"""Simple CLI runner to test data loader and GA operators.
This script demonstrates loading the .dat file, building an Instance, creating a random initial population and performing some genetic operators.
"""
import argparse
import random
import json
from src.data_loader import parse_ampl_dat, build_instance
from src.encoding import encode_routes, route_based_crossover, cut_and_fill, swap_mutation, insert_mutation, decode_vector


def random_initial_population(inst, pop_size=10, seed=None):
    rng = random.Random(seed)
    client_ids = [nid for nid, c in inst.clients.items() if c.escliente == 1]
    R = len(inst.trucks)
    population = []
    for _ in range(pop_size):
        perm = client_ids[:]
        rng.shuffle(perm)
        # split into R routes roughly evenly
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
    parser.add_argument('--dat', required=True, help='Path to AMPL .dat instance')
    parser.add_argument('--pop', type=int, default=20)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--demo', action='store_true', help='Run demo of operators and exit')
    args = parser.parse_args()

    parsed = parse_ampl_dat(args.dat)
    inst = build_instance(parsed)
    print('Loaded instance: nodes=', inst.n_nodes(), 'trucks=', len(inst.trucks))

    pop = random_initial_population(inst, pop_size=args.pop, seed=args.seed)
    print('\nSample individuals (first 3):')
    for i in range(min(3,len(pop))):
        print(i, pop[i])

    if args.demo:
        a,b = pop[0], pop[1]
        print('\nRBX demo:')
        print('Parent A:',a)
        print('Parent B:',b)
        child = route_based_crossover(a,b)
        print('Child:',child)
        print('\nCut-and-fill demo:')
        print('Child CF:', cut_and_fill(a,b))
        print('\nSwap/Insert demos on child:')
        c1 = swap_mutation(child)
        c2 = insert_mutation(child)
        print('Swap:', c1)
        print('Insert:', c2)

if __name__ == '__main__':
    main()
