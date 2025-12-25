#!/usr/bin/env python3
"""Evalúa una solución concreta (ruta por camión) usando el simulador.
Ejemplo:
  python scripts/eval_solution.py --dat inst.dat --truck 3 --route 1,5,3,2,8,6,10,9,4,7
"""
import argparse
from src.data_loader import parse_ampl_dat, build_instance
from src.encoding import encode_routes
from src.simulator import evaluate_individual


def main():
    parser = argparse.ArgumentParser(description='Evaluar solución (ruta específica)')
    parser.add_argument('--dat', required=True, help='Archivo .dat de la instancia')
    parser.add_argument('--truck', type=int, default=1, help='Índice del camión (1-based) donde insertar la ruta')
    parser.add_argument('--route', required=True, help='Lista de nodos separados por comas, e.g. "1,5,3"')
    parser.add_argument('--hs', type=float, default=None, help='Forzar HS (hora de salida) para el camión indicado')
    args = parser.parse_args()
    parsed = parse_ampl_dat(args.dat)
    inst = build_instance(parsed)

    # parse route
    if args.route.strip() == '':
        route_nodes = []
    else:
        route_nodes = [int(x) for x in args.route.split(',') if x.strip()!='']

    R = len(inst.trucks)
    # build routes list with empty for others
    routes = [[] for _ in range(R)]
    idx = max(0, min(R-1, args.truck - 1))
    routes[idx] = route_nodes

    vec = encode_routes(routes)

    # opcional: forzar HS para el camión objetivo (ya parseado en args)
    hs_value = args.hs

    # si se provee hs, simularemos ruta(s) usando ese HS para el camión y mantendremos schedule_muelles para los demás
    # llamaremos a evaluate_individual pero reemplazaremos el HS en `scheduled` antes de simular
    from src.encoding import decode_vector
    routes = decode_vector(vec)
    scheduled = None
    from src.simulator import schedule_muelles, simulate_route
    scheduled = schedule_muelles(routes, inst)
    if hs_value is not None:
        idx = max(0, min(len(routes)-1, args.truck-1))
        scheduled[idx] = hs_value

    # simular manualmente para obtener mismo formato de evaluate_individual
    total_penalty = 0.0
    total_cost = 0.0
    total_wait = 0.0
    details = {}
    truck_keys = sorted(inst.trucks.keys())

    for idx in range(len(routes)):
        route = routes[idx]
        HS = scheduled.get(idx, inst.params.get('tminsal', 0.0))
        sim = simulate_route(route, HS, idx+1, inst)
        details[idx] = sim
        truck_obj = inst.trucks[truck_keys[idx]] if idx < len(truck_keys) else list(inst.trucks.values())[0]
        TT = sim['TT']
        if truck_obj.esHora == 1:
            total_cost += truck_obj.CH * TT
        elif truck_obj.esF6 == 1:
            total_cost += truck_obj.CF6 * 1.0
        elif truck_obj.esF12 == 1:
            total_cost += truck_obj.CF12 * 1.0
        pcmin_c = float(inst.params.get('pcmin_c', 0))
        pcmax_c = float(inst.params.get('pcmax_c', 0))
        pcmin_nc = float(inst.params.get('pcmin_nc', 0))
        pcmax_nc = float(inst.params.get('pcmax_nc', 0))
        # penalizaciones por cliente (MinEx / MaxEx) — igual que en evaluate_individual
        for c in route:
            arr = sim['Arr'].get(c, 0.0)
            early = max(0.0, inst.clients[c].MinDC - arr)
            late = max(0.0, arr - inst.clients[c].MaxDC)
            if inst.clients[c].escritico == 1:
                total_penalty += pcmin_c * early + pcmax_c * late
            else:
                total_penalty += pcmin_nc * early + pcmax_nc * late
        total_penalty += float(inst.params.get('preg',0)) * sim['violations'].get('late_return', 0.0)
        total_wait += sum(sim['W'].values()) if sim['W'] else 0.0

    pw = float(inst.params.get('pw', 0.0))
    total_penalty += pw * total_wait
    Z = total_cost + total_penalty

    res = {'Z': Z, 'cost': total_cost, 'penalty': total_penalty, 'total_wait': total_wait, 'details': details, 'scheduled': scheduled, 'routes': routes}

    print('--- Evaluación de la solución proporcionada ---')
    print('Instancia:', args.dat)
    print('Camión colocado en posición:', args.truck)
    print('Rutas:', routes)
    print('Z =', res['Z'])
    print('Costo (contratos) =', res['cost'])
    print('Penalizaciones =', res['penalty'])
    print('Total espera (horas) =', res['total_wait'])
    print('\nDetalle por ruta:')
    for i,det in res['details'].items():
        print(f"Ruta idx {i}: HS={res['scheduled'].get(i,'?')}, HRegreso={det['HRegreso']}, TT={det['TT']}")
    print('\nViolaciones (ejemplo primera ruta no-vacía):')
    for i, det in res['details'].items():
        if det['route']:
            print('Idx', i, 'violations:', det['violations'])
            print('\nDetalle por cliente (Arr, MinDC, MaxDC, W):')
            for c in det['route']:
                arr = det['Arr'][c]
                minc = inst.clients[c].MinDC
                maxc = inst.clients[c].MaxDC
                w = det['W'].get(c, 0.0)
                early = max(0.0, minc - arr)
                late = max(0.0, arr - maxc)
                print(f"Cliente {c}: Arr={arr:.2f}, Min={minc:.2f}, Max={maxc:.2f}, W={w:.2f}, early={early:.2f}, late={late:.2f}, crit={inst.clients[c].escritico}")
            break


if __name__ == '__main__':
    main()
