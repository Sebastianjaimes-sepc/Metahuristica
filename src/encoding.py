"""Encoding and GA operators for single-vector representation.
Vector encoding: [0, route1..., 0, route2..., 0, ..., 0]
(0 represents depot). There must be R+1 zeros if we maintain exactly R trucks.
"""
import random
from typing import List, Tuple

DEPOT = 0

# Utilities

def clients_from_vector(vec: List[int]) -> List[int]:
    return [x for x in vec if x != DEPOT]


def count_trucks_from_vector(vec: List[int]) -> int:
    # number of segments = number of zeros - 1
    zeros = sum(1 for x in vec if x == DEPOT)
    return max(0, zeros - 1)


def encode_routes(routes: List[List[int]]) -> List[int]:
    v = []
    for r in routes:
        v.append(DEPOT)
        v.extend(r)
    v.append(DEPOT)
    return v


def decode_vector(vec: List[int]) -> List[List[int]]:
    routes = []
    current = []
    first = True
    for x in vec:
        if x == DEPOT:
            if first:
                first = False
            else:
                routes.append(current)
                current = []
        else:
            current.append(int(x))
    # Note: last depot closes last route; if not, append
    return routes

# Genetic operators

def cut_and_fill(parent_a: List[int], parent_b: List[int], rng=random) -> List[int]:
    """Cut-and-fill using flattened client lists. Preserves number of trucks (zeros) from parent_a."""
    A_clients = clients_from_vector(parent_a)
    B_clients = clients_from_vector(parent_b)
    n = len(A_clients)
    if n == 0:
        return parent_a[:]

    # choose cut positions on flattened list
    cut = rng.randint(0, n-1)
    # copy prefix from A up to cut
    segment = A_clients[0:cut+1]
    offspring_clients = segment[:]
    for c in B_clients:
        if c not in offspring_clients:
            offspring_clients.append(c)

    # reinsert zeros keeping same number of trucks as parent_a
    R = count_trucks_from_vector(parent_a)
    # partition offspring_clients into R parts as evenly as possible
    if R <= 0:
        return [DEPOT] + offspring_clients + [DEPOT]
    base = len(offspring_clients) // R
    rem = len(offspring_clients) % R
    routes = []
    idx = 0
    for r in range(R):
        size = base + (1 if r < rem else 0)
        routes.append(offspring_clients[idx:idx+size])
        idx += size
    return encode_routes(routes)


def swap_mutation(vec: List[int], rng=random) -> List[int]:
    clients = clients_from_vector(vec)
    if len(clients) < 2:
        return vec[:]
    i, j = rng.sample(range(len(clients)), 2)
    clients[i], clients[j] = clients[j], clients[i]
    # reconstruct preserving original truck splits
    R = count_trucks_from_vector(vec)
    if R <= 0:
        return [DEPOT] + clients + [DEPOT]
    base = len(clients)//R
    rem = len(clients)%R
    routes = []
    idx = 0
    for r in range(R):
        size = base + (1 if r < rem else 0)
        routes.append(clients[idx:idx+size])
        idx += size
    return encode_routes(routes)


def insert_mutation(vec: List[int], rng=random) -> List[int]:
    clients = clients_from_vector(vec)
    if len(clients) < 2:
        return vec[:]
    i = rng.randrange(len(clients))
    val = clients.pop(i)
    j = rng.randrange(len(clients)+1)
    clients.insert(j, val)
    # reconstruct
    R = count_trucks_from_vector(vec)
    if R <= 0:
        return [DEPOT] + clients + [DEPOT]
    base = len(clients)//R
    rem = len(clients)%R
    routes = []
    idx = 0
    for r in range(R):
        size = base + (1 if r < rem else 0)
        routes.append(clients[idx:idx+size])
        idx += size
    return encode_routes(routes)


def route_based_crossover(parent_a: List[int], parent_b: List[int], rng=random) -> List[int]:
    """Take a random subset of routes (whole routes between depots) from A and fill remaining with B order"""
    routes_a = decode_vector(parent_a)
    routes_b = decode_vector(parent_b)
    R = len(routes_a)
    if R == 0:
        return parent_a[:]
    # pick random subset of route indices to copy
    k = rng.randint(1, max(1, R//2))
    chosen = set(rng.sample(range(R), k))
    taken_clients = []
    child_routes = [None]*R
    for idx in range(R):
        if idx in chosen:
            child_routes[idx] = routes_a[idx][:]
            taken_clients.extend(routes_a[idx])
    # Fill remaining routes with remaining clients in order of parent_b
    remaining_clients = [c for route in routes_b for c in route if c not in taken_clients]
    # partition remaining_clients into the remaining slots
    rem_slot_idxs = [i for i in range(R) if child_routes[i] is None]
    if len(rem_slot_idxs) == 0:
        return encode_routes(child_routes)
    base = len(remaining_clients)//len(rem_slot_idxs)
    rrem = len(remaining_clients)%len(rem_slot_idxs)
    idx = 0
    for j,slot in enumerate(rem_slot_idxs):
        size = base + (1 if j < rrem else 0)
        child_routes[slot] = remaining_clients[idx:idx+size]
        idx += size
    return encode_routes(child_routes)


def tournament_selection(population: List[List[int]], fitnesses: List[float], k:int=3, rng=random) -> int:
    indices = rng.sample(range(len(population)), k)
    best = min(indices, key=lambda i: fitnesses[i])
    return best

if __name__ == '__main__':
    # quick demo
    pA = [0,1,2,3,0,4,5,0]
    pB = [0,4,2,1,0,3,5,0]
    print('A', pA)
    print('B', pB)
    child = route_based_crossover(pA,pB)
    print('RBX child', child)
    child2 = cut_and_fill(pA,pB)
    print('Cut-and-fill child', child2)
    print('Swap mut', swap_mutation(child))
    print('Insert mut', insert_mutation(child))
