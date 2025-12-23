"""Simulador de rutas y evaluador de factibilidad.
Funciones principales:
- franja_of_time
- schedule_muelles (heurístico sencillo con pesos w1..w5)
- simulate_individual / evaluate_individual

Comentarios y mensajes están en español.
"""
from typing import List, Dict, Any, Tuple
from src.data_loader import Instance
from src.encoding import decode_vector
import math
import os
import logging

logger = logging.getLogger(__name__)

# Pesos por defecto para prioridad de muelles
DEFAULT_WEIGHTS = {'w1':0.40, 'w2':0.30, 'w3':0.15, 'w4':0.10, 'w5':0.05}

# Valores por defecto de parámetros no provistos
DEFAULTS = {'tlim':18.0, 'alm':14.0, 'talm':1.0, 'tminsal':0.0}


def franja_of_time(time: float, tinic: Dict[int,float], tfin: Dict[int,float]) -> int:
    """Devuelve índice de franja donde cae `time`. Si no encuentra, devuelve el más cercano."""
    for f, start in tinic.items():
        end = tfin.get(f, start+4)
        if start <= time < end:
            return f
    # si no encontrado, devolver la última franja
    return max(tinic.keys()) if tinic else 1


def estimate_route_duration(route: List[int], truck_id:int, inst: Instance) -> float:
    """Estimación simple: suma de tiempos de servicio + tiempo de viaje entre nodos + vuelta a depot usando franja 1 por defecto"""
    if len(route)==0:
        return 0.0
    total = 0.0
    # from depot to first
    f = franja_of_time(0.0, inst.tinic, inst.tfin)
    total += inst.tvia.get(f, next(iter(inst.tvia.values())))[0, route[0]]
    for i in range(len(route)):
        c = route[i]
        total += inst.clients[c].TS
        if i+1 < len(route):
            j = route[i+1]
            total += inst.tvia.get(f, next(iter(inst.tvia.values())))[c,j]
    # last to depot
    last = route[-1]
    total += inst.tvia.get(f, next(iter(inst.tvia.values())))[last, 0]
    return total


def compute_priority(route: List[int], truck_id:int, inst: Instance, weights:Dict[str,float]=None) -> float:
    """Calcula el score de prioridad una ruta para asignación de muelles.
    w1 urgencia por ventanas (número de clientes cerca del limite),
    w2 duración estimada,
    w3 cantidad de clientes críticos,
    w4 riesgo de atraso (ventanas estrechas),
    w5 sensibilidad al tráfico (duración relativa en franjas pico)
    """
    w = weights or DEFAULT_WEIGHTS
    # w1: urgencia: contar % clientes con ventana alta urgencia (MaxDC - MinDC pequeña)
    urg = 0.0
    risk=0.0
    ncrit=0
    for c in route:
        span = inst.clients[c].MaxDC - inst.clients[c].MinDC
        if span < 3:  # ventana estrecha
            urg += 1
            risk += 1/(span+0.1)
        if inst.clients[c].escritico==1:
            ncrit += 1
    urg_score = urg / (len(route)+1)
    dur_est = estimate_route_duration(route, truck_id, inst)
    duration_score = dur_est
    crit_score = ncrit
    risk_score = risk
    # sensitivity: fraction of route edges that would be in slow franjas (approx by comparing tvia across franjas)
    sens = 0.0
    if len(route)>0 and len(inst.tvia)>1:
        # compute average of franja 1 vs franja 3 for speedup
        fkeys = sorted(inst.tvia.keys())
        fslow = fkeys[0]
        ffast = fkeys[-1]
        tot=0.0
        for i0 in [0]+route[:-1]:
            j = route[0] if i0==0 else route[route.index(i0)+1] if route.index(i0)+1 < len(route) else 0
            a = inst.tvia[fslow][i0,j]
            b = inst.tvia[ffast][i0,j]
            if b>0:
                tot += max(0, (a-b)/b)
        sens = tot
    score = w['w1']*urg_score + w['w2']*(duration_score) + w['w3']*(crit_score) + w['w4']*risk_score + w['w5']*sens
    return score


def schedule_muelles(routes: List[List[int]], inst: Instance, weights:Dict[str,float]=None) -> Dict[int, float]:
    """Asignación heurística de HS (hora de salida) a cada ruta (índices 0..R-1) respetando nmuelles y tcarga/discrete Lc.
    Devuelve dict index->HS
    """
    w = weights or DEFAULT_WEIGHTS
    nmuelles = inst.params.get('nmuelles', 1)
    durH = float(inst.params.get('durH', 0.166))
    Lc = int(inst.params.get('Lc', 3))
    tcarga = float(inst.params.get('tcarga', 0.5))
    tminsal = float(inst.params.get('tminsal', DEFAULTS['tminsal']))

    # calcular prioridad de cada ruta
    scores = [(i, compute_priority(routes[i], i+1, inst, weights=w)) for i in range(len(routes))]
    # ordenar por prioridad descendente (mayor score primero)
    scores.sort(key=lambda x: -x[1])

    # ocupación de muelles por franjas temporales discretas (lista de intervales)
    scheduled = {}
    occupancy = []  # list of tuples (start, end)

    def can_schedule_at(start: float):
        # check how many overlapping cargues con [start, start + Lc*durH)
        s = start
        e = start + Lc*durH
        overlap = sum(1 for (a,b) in occupancy if not (b <= s or a >= e))
        return overlap < nmuelles

    # try to assign earliest feasible HS >= tminsal in steps of durH
    for idx, sc in scores:
        dur_est = estimate_route_duration(routes[idx], idx+1, inst)
        # start from tminsal
        t = tminsal
        # try up to 24 hours in steps
        assigned = None
        while t < 24:
            if can_schedule_at(t):
                occupancy.append((t, t + Lc*durH))
                assigned = t
                break
            t += durH
        if assigned is None:
            # fallback: assign at tminsal ignoring muelles (will incur infeasibility)
            assigned = tminsal
        scheduled[idx] = assigned
    return scheduled


def simulate_route(route: List[int], HS: float, truck_id:int, inst: Instance) -> Dict[str, Any]:
    """Simula una ruta individual a partir de la hora de salida HS y devuelve datos y violaciones.
    Asume que la franja para cada viaje se determina por la hora de salida del tramo.
    """
    res = {
        'route': route,
        'HS': HS,
        'HI': {},  # inicio servicio por cliente
        'Arr': {},
        'W': {},
        'q': {},
        'HRegreso': None,
        'TT': None,
        'violations': {
            'cap_viol': 0.0,
            'window_early': 0.0,
            'window_late': 0.0,
        },
        'costs': {}
    }
    # load init
    truck_keys = sorted(inst.trucks.keys())
    if truck_id-1 < len(truck_keys):
        truck_obj = inst.trucks[truck_keys[truck_id-1]]
    else:
        truck_obj = list(inst.trucks.values())[0]
    Cap = truck_obj.Cap

    tcur = HS
    q = 0.0
    prev = 0
    for i, c in enumerate(route):
        # travel prev -> c
        f = franja_of_time(tcur, inst.tinic, inst.tfin)
        ttravel = inst.tvia.get(f, next(iter(inst.tvia.values())))[prev, c]
        arr = tcur + ttravel
        # wait if before MinDC
        minc = inst.clients[c].MinDC
        maxc = inst.clients[c].MaxDC
        W = 0.0
        if arr < minc:
            W = minc - arr
            start = minc
        else:
            start = arr
        # service
        HI = start
        tfinish = HI + inst.clients[c].TS
        # update q
        q = q - inst.clients[c].DemE + inst.clients[c].DemR
        if q < 0:
            q = 0.0
        # check capacity
        if q > Cap:
            res['violations']['cap_viol'] += q - Cap
        # check windows
        if arr < minc:
            res['violations']['window_early'] += (minc - arr)
        if arr > maxc:
            res['violations']['window_late'] += (arr - maxc)
        # store
        res['Arr'][c] = arr
        res['HI'][c] = HI
        res['W'][c] = W
        res['q'][c] = q
        tcur = tfinish
        prev = c
    # return to depot
    f = franja_of_time(tcur, inst.tinic, inst.tfin)
    ttravel_back = inst.tvia.get(f, next(iter(inst.tvia.values())))[prev, 0]
    HRegreso = tcur + ttravel_back
    TT = HRegreso - HS
    res['HRegreso'] = HRegreso
    res['TT'] = TT

    # penalties
    tlim = float(inst.params.get('tlim', DEFAULTS['tlim']))
    preg = float(inst.params.get('preg', 0.0))
    if HRegreso > tlim:
        res['violations']['late_return'] = HRegreso - tlim
    else:
        res['violations']['late_return'] = 0.0

    return res


def evaluate_individual(vec: List[int], inst: Instance, weights:Dict[str,float]=None) -> Dict[str, Any]:
    """Evalúa un vector completo: decodifica rutas, programa muelles, simula cada ruta y devuelve métricas y costo Z aproximado."""
    routes = decode_vector(vec)
    R = len(routes)
    truck_keys = sorted(inst.trucks.keys())

    scheduled = schedule_muelles(routes, inst, weights=weights)

    total_penalty = 0.0
    total_cost = 0.0
    total_wait = 0.0
    details = {}

    for idx in range(R):
        route = routes[idx]
        HS = scheduled.get(idx, inst.params.get('tminsal', DEFAULTS['tminsal']))
        sim = simulate_route(route, HS, idx+1, inst)
        details[idx] = sim
        # compute cost: contract
        truck_obj = inst.trucks[truck_keys[idx]] if idx < len(truck_keys) else list(inst.trucks.values())[0]
        TT = sim['TT']
        if truck_obj.esHora == 1:
            total_cost += truck_obj.CH * TT
        elif truck_obj.esF6 == 1:
            total_cost += truck_obj.CF6 * 1.0
        elif truck_obj.esF12 == 1:
            total_cost += truck_obj.CF12 * 1.0
        # penalties windows
        # distinguish clientes críticos (we'll weight with pcmin_c/pcmax_c)
        pcmin_c = float(inst.params.get('pcmin_c', 0))
        pcmax_c = float(inst.params.get('pcmax_c', 0))
        pcmin_nc = float(inst.params.get('pcmin_nc', 0))
        pcmax_nc = float(inst.params.get('pcmax_nc', 0))
        w_viol = 0.0
        for c in route:
            if inst.clients[c].escritico==1:
                w_viol += pcmin_c * sim['violations']['window_early'] + pcmax_c * sim['violations']['window_late']
            else:
                w_viol += pcmin_nc * sim['violations']['window_early'] + pcmax_nc * sim['violations']['window_late']
        total_penalty += w_viol
        total_penalty += float(inst.params.get('preg',0)) * sim['violations'].get('late_return', 0.0)
        total_wait += sum(sim['W'].values()) if sim['W'] else 0.0

    # waiting penalty
    pw = float(inst.params.get('pw', 0.0))
    total_penalty += pw * total_wait

    Z = total_cost + total_penalty

    return {
        'Z': Z,
        'cost': total_cost,
        'penalty': total_penalty,
        'total_wait': total_wait,
        'details': details,
        'scheduled': scheduled,
        'routes': routes
    }


if __name__ == '__main__':
    import argparse
    from src.data_loader import parse_ampl_dat, build_instance
    parser = argparse.ArgumentParser(description='Herramientas de simulación y evaluación')
    parser.add_argument('--dat', required=True)
    args = parser.parse_args()
    parsed = parse_ampl_dat(args.dat)
    inst = build_instance(parsed)
    print('Instancia cargada para simulación: nodos=', inst.n_nodes(), 'camiones=', len(inst.trucks))
    # demo small
    vec = [0,7,9,10,8,0,6,4,1,0,5,2,3,0]
    res = evaluate_individual(vec, inst)
    print('Z=', res['Z'], 'cost=', res['cost'], 'penalty=', res['penalty'])
    print('Scheduled HS:', res['scheduled'])
