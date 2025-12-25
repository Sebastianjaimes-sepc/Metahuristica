"""Utilities for GA: local search per-route and diversity measures."""
import random
from typing import List, Tuple
from src.encoding import decode_vector, encode_routes
from src.simulator import evaluate_individual


def local_search_on_routes(individual: List[int], inst, fraction: float=0.3, max_evals_per_route:int=50, rng=None) -> List[int]:
    """Apply intra-route local search to `fraction` of the routes in `individual`.
    We try pairwise swaps and relocations inside a route and accept the first improving move (first-improvement) until no improvement found or eval limit reached.
    Returns a possibly improved individual.
    """
    rng = rng or random
    routes = decode_vector(individual)
    if len(routes) == 0:
        return individual
    R = len(routes)
    k = max(1, int(max(1, round(fraction * R))))
    chosen = rng.sample(range(R), k)
    best_vec = individual[:]
    best_eval = evaluate_individual(best_vec, inst)['Z']

    for idx in chosen:
        route = routes[idx]
        if len(route) < 2:
            continue
        improved = True
        evals = 0
        while improved and evals < max_evals_per_route:
            improved = False
            # try swaps
            n = len(route)
            for i in range(n):
                for j in range(i+1, n):
                    newr = route[:]
                    newr[i], newr[j] = newr[j], newr[i]
                    # build candidate individual
                    cand_routes = routes[:]
                    cand_routes[idx] = newr
                    cand_vec = encode_routes(cand_routes)
                    evals += 1
                    if evals > max_evals_per_route:
                        break
                    z = evaluate_individual(cand_vec, inst)['Z']
                    if z < best_eval:
                        best_eval = z
                        best_vec = cand_vec
                        routes = decode_vector(best_vec)
                        route = routes[idx]
                        improved = True
                        break
                if improved or evals >= max_evals_per_route:
                    break
            if improved:
                continue
            # try relocations (take element i and insert at j)
            for i in range(n):
                for j in range(n):
                    if i == j:
                        continue
                    newr = route[:]
                    val = newr.pop(i)
                    newr.insert(j, val)
                    cand_routes = routes[:]
                    cand_routes[idx] = newr
                    cand_vec = encode_routes(cand_routes)
                    evals += 1
                    if evals > max_evals_per_route:
                        break
                    z = evaluate_individual(cand_vec, inst)['Z']
                    if z < best_eval:
                        best_eval = z
                        best_vec = cand_vec
                        routes = decode_vector(best_vec)
                        route = routes[idx]
                        improved = True
                        break
                if improved or evals >= max_evals_per_route:
                    break
    return best_vec


def population_similarity(pop: List[List[int]]) -> float:
    """Compute average pairwise similarity (fraction of equal positions in flattened client list).
    Returns average similarity in [0,1]."""
    if len(pop) < 2:
        return 1.0
    # flatten clients (remove DEPOT=0)
    flats = [[x for x in ind if x != 0] for ind in pop]
    n = len(flats[0]) if flats[0] else 0
    if n == 0:
        return 1.0
    total_sim = 0.0
    pairs = 0
    for i in range(len(flats)):
        for j in range(i+1, len(flats)):
            a = flats[i]
            b = flats[j]
            matches = sum(1 for k in range(n) if a[k] == b[k])
            total_sim += matches / n
            pairs += 1
    if pairs == 0:
        return 1.0
    return total_sim / pairs


def population_diversity(pop: List[List[int]]) -> float:
    """Return diversity = 1 - average_similarity"""
    sim = population_similarity(pop)
    return 1.0 - sim


def build_greedy_single_truck(inst, hs_candidates=None, truck_index: int = None):
    """Construye una solución con un solo camión (los demás vacíos) usando inserción voraz.
    Devuelve un vector codificado.
    """
    from src.encoding import encode_routes
    if hs_candidates is None:
        hs_candidates = [6.0, 7.0, 8.0, 9.0]
    client_ids = [nid for nid, c in inst.clients.items() if c.escliente == 1]
    best_vec = None
    best_z = float('inf')
    R = len(inst.trucks)
    for hs in hs_candidates:
        route = []
        remaining = client_ids[:]
        while remaining:
            best_choice = None
            best_choice_z = float('inf')
            for c in remaining:
                cand_route = route + [c]
                # build vector with cand_route in truck 0 (or last truck_index if provided)
                routes = [[] for _ in range(R)]
                idx = 0 if truck_index is None else truck_index
                routes[idx] = cand_route
                vec = encode_routes(routes)
                # force HS by scheduling and overriding HS if needed (we rely on schedule_muelles default)
                z = evaluate_individual(vec, inst)['Z']
                if z < best_choice_z:
                    best_choice_z = z
                    best_choice = c
            # append best and remove
            route.append(best_choice)
            remaining.remove(best_choice)
        # evaluate final
        routes = [[] for _ in range(R)]
        idx = 0 if truck_index is None else truck_index
        routes[idx] = route
        vec = encode_routes(routes)
        z = evaluate_individual(vec, inst)['Z']
        if z < best_z:
            best_z = z
            best_vec = vec
    return best_vec


def merge_routes_local_search(individual: List[int], inst, max_evals:int=200) -> List[int]:
    """Try merging whole routes or prefixes to other routes to find improvements (useful to reduce number of used trucks).
    Returns improved individual if found, otherwise original.
    """
    from src.encoding import decode_vector, encode_routes
    best_vec = individual[:]
    best_z = evaluate_individual(best_vec, inst)['Z']
    routes = decode_vector(individual)
    R = len(routes)
    evals = 0
    # try moving prefixes of route i into route j
    for i in range(R):
        for j in range(R):
            if i == j:
                continue
            ri = routes[i]
            rj = routes[j]
            if not ri:
                continue
            # try k from 1 to len(ri) (prefix sizes)
            for k in range(1, len(ri)+1):
                prefix = ri[:k]
                new_ri = ri[k:]
                new_rj = rj + prefix
                cand_routes = [r for r in routes]
                cand_routes[i] = new_ri
                cand_routes[j] = new_rj
                cand_vec = encode_routes(cand_routes)
                evals += 1
                if evals > max_evals:
                    return best_vec
                z = evaluate_individual(cand_vec, inst)['Z']
                if z < best_z:
                    best_z = z
                    best_vec = cand_vec
                    routes = decode_vector(best_vec)
                    # restart scanning with new configuration
                    evals = 0
                    break
            # if improved, break outer loops to re-evaluate
    return best_vec

