#!/usr/bin/env python3
"""Run the GA configured to the user's specification.
Usage: python scripts/run_ga_spec.py --dat instances/sebas.dat

Defaults match the spec:
- popsize=100, gens=500
- tournament k=3, RBX prob 0.85
- mutation prob 0.10 (SWAP 70%, INSERT 20%, CUT-FILL 10%)
- elitism 2
- local search fraction 0.3 (option to apply only on final generation)
- diversity check every 50 gens, threshold 0.8, regen 30%
- early stop: 60 no-improve gens
"""
import argparse
import random
import json
import os
from copy import deepcopy
from src.data_loader import parse_ampl_dat, build_instance
from src.encoding import encode_routes, route_based_crossover, cut_and_fill, swap_mutation, insert_mutation, decode_vector
from src.simulator import evaluate_individual, schedule_muelles
from src.ga_utils import local_search_on_routes, population_diversity, build_greedy_single_truck, merge_routes_local_search


def is_feasible(vec, inst):
    """Check hard feasibility rules (returns True if feasible).
    Rules: no capacity violation, TT <= 12, no late return beyond tlim, muelles scheduling respects nmuelles (checked by schedule_muelles attempts).
    Note: window violations are allowed but penalized in FO (not treated as infeasible here by default).
    """
    res = evaluate_individual(vec, inst)
    for idx, det in res['details'].items():
        if det['violations'].get('cap_viol', 0.0) > 1e-6:
            return False
        if det['TT'] is not None and det['TT'] > 12 + 1e-6:
            return False
        if det['violations'].get('late_return', 0.0) > 1e-6:
            return False
    # check muelles: schedule_muelles will assign HS; if assigned HS leads to overlapping > nmuelles is handled in scheduling heuristic
    # we accept scheduling result as feasible here
    return True


def random_initial_population(inst, pop_size=100, seed=None):
    rng = random.Random(seed)
    client_ids = [nid for nid, c in inst.clients.items() if c.escliente == 1]
    R = len(inst.trucks)
    population = []
    for _ in range(pop_size):
        perm = client_ids[:]
        rng.shuffle(perm)
        # divide into R routes approximately evenly (allow empty)
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


def run_ga(dat_path, outdir, popsize=100, gens=500, seed=42, local_fraction=0.3, local_at_last_only=False):
    parsed = parse_ampl_dat(dat_path)
    inst = build_instance(parsed)
    os.makedirs(outdir, exist_ok=True)
    random.seed(seed)

    population = random_initial_population(inst, pop_size=popsize, seed=seed)
    # optionally insert greedy single-truck heuristic to seed
    greedy = build_greedy_single_truck(inst)
    if greedy is not None:
        # replace a few worst with variations of greedy
        fitness = [evaluate_individual(ind, inst)['Z'] for ind in population]
        sorted_worst = sorted(range(len(population)), key=lambda i: fitness[i], reverse=True)[:3]
        variants = [greedy, swap_mutation(greedy), insert_mutation(greedy)]
        for k, idx_replace in enumerate(sorted_worst):
            population[idx_replace] = variants[k % len(variants)]

    # GA core
    def evaluate_population(pop):
        return [evaluate_individual(ind, inst)['Z'] for ind in pop]

    fitness = evaluate_population(population)
    best_idx = min(range(len(population)), key=lambda i: fitness[i])
    best = deepcopy(population[best_idx])
    best_score = fitness[best_idx]
    print('Gen 0 best Z =', best_score)

    gens_since_improve = 0

    for g in range(1, gens+1):
        newpop = []
        # elitism
        sorted_idx = sorted(range(len(population)), key=lambda i: fitness[i])
        elites = [deepcopy(population[sorted_idx[0]]), deepcopy(population[sorted_idx[1]])]
        while len(newpop) < popsize - 2:
            # selection tournament K=3
            candidates = random.sample(range(len(population)), 3)
            p1 = min(candidates, key=lambda i: fitness[i])
            candidates = random.sample(range(len(population)), 3)
            p2 = min(candidates, key=lambda i: fitness[i])
            parent_a = population[p1]
            parent_b = population[p2]
            # crossover RBX 0.85
            if random.random() < 0.85:
                child = route_based_crossover(parent_a, parent_b)
            else:
                child = deepcopy(parent_a)
            # mutation 10%
            if random.random() < 0.10:
                m = random.random()
                if m < 0.70:
                    child = swap_mutation(child)
                elif m < 0.90:
                    child = insert_mutation(child)
                else:
                    child = cut_and_fill(child, parent_b)
            # local search
            if not local_at_last_only:
                child = local_search_on_routes(child, inst, fraction=local_fraction, rng=random)
                child = merge_routes_local_search(child, inst)
            newpop.append(child)
        newpop.extend(elites)
        population = newpop
        fitness = evaluate_population(population)
        cur_best_idx = min(range(len(population)), key=lambda i: fitness[i])
        cur_best_score = fitness[cur_best_idx]
        if cur_best_score < best_score:
            best_score = cur_best_score
            best = deepcopy(population[cur_best_idx])
            gens_since_improve = 0
        else:
            gens_since_improve += 1
        # diversity control
        if g % 50 == 0:
            diversity = population_diversity(population)
            print(f'Gen {g}: diversity={diversity:.3f}')
            if diversity < 0.8:
                regen_n = max(1, int(round(0.3 * popsize)))
                print(f'Low diversity -> regenerating {regen_n} individuals')
                new_inds = random_initial_population(inst, pop_size=regen_n, seed=random.randint(0,10**9))
                # replace worst
                sorted_worst = sorted(range(len(population)), key=lambda i: fitness[i], reverse=True)[:regen_n]
                for k, idx_replace in enumerate(sorted_worst):
                    population[idx_replace] = new_inds[k]
                fitness = evaluate_population(population)
        # local search on last generation if requested
        if g == gens and local_at_last_only:
            new_best = deepcopy(best)
            new_best = local_search_on_routes(new_best, inst, fraction=local_fraction, rng=random)
            new_best = merge_routes_local_search(new_best, inst)
            new_eval = evaluate_individual(new_best, inst)
            if new_eval['Z'] < best_score:
                best_score = new_eval['Z']
                best = new_best
        if gens_since_improve >= 60:
            print('Early stop: no improvement for 60 gens')
            break
        if g % 10 == 0 or g == 1 or g == gens:
            print(f'Gen {g}: best Z = {best_score} (noimprove {gens_since_improve})')

    res = evaluate_individual(best, inst)
    out = {
        'Z': res['Z'],
        'cost': res['cost'],
        'penalty': res['penalty'],
        'routes': res['routes'],
        'scheduled': res['scheduled']
    }
    with open(os.path.join(outdir, 'best_solution.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
    print('Done. Best Z =', res['Z'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dat', required=True, help='AMPL .dat file')
    parser.add_argument('--out', default='results_spec', help='Output directory')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--popsize', type=int, default=100)
    parser.add_argument('--gens', type=int, default=500)
    parser.add_argument('--local-fraction', type=float, default=0.3)
    parser.add_argument('--local-last-only', action='store_true', help='Apply local search only on last generation')
    args = parser.parse_args()
    run_ga(args.dat, args.out, popsize=args.popsize, gens=args.gens, seed=args.seed, local_fraction=args.local_fraction, local_at_last_only=args.local_last_only)
