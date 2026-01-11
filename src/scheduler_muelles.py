"""
SCHEDULER_MUELLES: Asignar horarios de salida con sistema de muelles.

Sistema:
- Múltiples camiones quieren salir
- Pero solo max_muelles pueden estar cargando simultáneamente
- Ordenar por prioridad y espaciar por tiempo de cargue
"""

from typing import List, Dict, Tuple
from src.operators_rbx import sort_routes_by_priority

def calculate_priorities(routes: List[List[int]], inst,
                        w1: float = 0.40,
                        w2: float = 0.30,
                        w3: float = 0.15,
                        w4: float = 0.10,
                        w5: float = 0.05) -> List[Tuple[int, float]]:
    """
    Calcular prioridad de cada ruta.
    
    Returns:
        [(route_index, priority_score), ...]
        Ordenado por prioridad descendente
    """
    return sort_routes_by_priority(routes, inst, w1, w2, w3, w4, w5)


def assign_departure_times(routes: List[List[int]], inst,
                          priorities: List[Tuple[int, float]],
                          tcarga: float = 1.0,
                          max_muelles: int = 2,
                          min_salida: float = 0.0) -> Dict[int, float]:
    """
    Asignar hora de salida a cada ruta respetando muelles.
    
    Algoritmo:
    1. Ordenar rutas por prioridad
    2. Asignar salida de forma escalonada
    3. Máximo max_muelles cargando simultáneamente
    
    Args:
        routes: [[1,3], [2,4], [5]]
        inst: Instance
        priorities: [(ruta_idx, score), ...] ordenado por score DESC
        tcarga: tiempo que ocupa en muelle (default 1.0 hora)
        max_muelles: número máximo simultáneos
        min_salida: hora mínima de salida
        
    Returns:
        {ruta_idx: hora_salida, ...}
    """
    departure_times = {}
    muelle_queue = []  # [(time_available, route_idx)]
    
    # Inicializar: primer grupo de max_muelles
    for i in range(min(max_muelles, len(priorities))):
        route_idx, priority = priorities[i]
        departure_times[route_idx] = min_salida
        muelle_queue.append((min_salida + tcarga, route_idx))
    
    # Procesar resto de rutas
    for i in range(max_muelles, len(priorities)):
        route_idx, priority = priorities[i]
        
        # Encontrar muelle disponible más pronto
        earliest_time, _ = min(muelle_queue)
        
        # Asignar salida
        departure_times[route_idx] = earliest_time
        
        # Actualizar cola de muelles
        muelle_queue.remove((earliest_time, _))
        muelle_queue.append((earliest_time + tcarga, route_idx))
    
    return departure_times


def schedule_muelles(routes: List[List[int]], inst,
                    w1: float = 0.40,
                    w2: float = 0.30,
                    w3: float = 0.15,
                    w4: float = 0.10,
                    w5: float = 0.05,
                    tcarga: float = 1.0,
                    max_muelles: int = 2,
                    min_salida: float = 0.0) -> Dict[int, float]:
    """
    Scheduler completo: calcular prioridades y asignar horarios.
    
    Args:
        routes: [[1,3,5], [2,4], [6]]
        inst: Instance
        w1-w5: pesos para prioridad
        tcarga: tiempo de carga en muelle
        max_muelles: máximo simultáneo
        min_salida: hora mínima de salida
        
    Returns:
        {ruta_idx: hora_salida_recomendada, ...}
    """
    # Paso 1: Calcular prioridades
    priorities = calculate_priorities(routes, inst, w1, w2, w3, w4, w5)
    
    # Paso 2: Asignar horarios respetando muelles
    departure_times = assign_departure_times(
        routes, inst, priorities, tcarga, max_muelles, min_salida
    )
    
    return departure_times


def simulate_route_with_departure(route: List[int], inst,
                                 departure_time: float = 0.0) -> Dict:
    """
    Simular una ruta con hora de salida específica.
    
    Retorna: tiempos de llegada, ventanas, esperas, etc.
    """
    if not route:
        return {'feasible': True, 'violations': 0}
    
    current_time = departure_time
    violations = 0
    violations_list = []
    
    for client_id in route:
        client = inst.clients[client_id]
        
        # Simular viaje
        travel_time = 0.5  # Simplificación
        arrival_time = current_time + travel_time
        
        # Chequear ventana
        if arrival_time < client.MinDC:
            wait_time = client.MinDC - arrival_time
            current_time = client.MinDC + client.TS
        elif arrival_time > client.MaxDC:
            violations += 1
            violations_list.append({
                'client': client_id,
                'arrival': arrival_time,
                'max_allowed': client.MaxDC,
                'violation': arrival_time - client.MaxDC
            })
            current_time = arrival_time + client.TS
        else:
            current_time = arrival_time + client.TS
    
    return {
        'feasible': violations == 0,
        'violations': violations,
        'violation_list': violations_list,
        'return_time': current_time
    }
