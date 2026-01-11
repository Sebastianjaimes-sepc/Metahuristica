"""
OBJECTIVE_FUNCTION: Función objetivo Z según especificación AMPL.

Z = Costo_camiones 
  + Penalizacion_ventanas_criticas
  + Penalizacion_ventanas_normales  
  + Penalizacion_regreso_tarde (>18:00)
  + Penalizacion_espera
"""

from typing import List, Dict, Tuple
import numpy as np

def calculate_cost_trucks(routes: List[List[int]], inst, truck_assignment: Dict = None) -> float:
    """
    Calcular costo total de camiones.
    
    Cada camión tiene:
    - CH: costo por hora
    - CF6: costo fijo 6 horas
    - CF12: costo fijo 12 horas
    
    Args:
        routes: [[1,3,5], [2,4]]
        inst: Instance
        truck_assignment: dict {ruta_idx: truck_id}
        
    Returns:
        costo_total
    """
    total_cost = 0.0
    
    # Simplificación: asumir camión 0 para todas las rutas
    # En realidad se debería asignar óptimamente
    
    for route_idx, route in enumerate(routes):
        if not route:
            continue
        
        truck = list(inst.trucks.values())[route_idx % len(inst.trucks)]
        
        # Estimar duración de ruta (simplificación)
        route_duration = len(route) * 0.5  # ~30 min por cliente
        
        # Calcular costo según tipo
        if truck.esHora == 1:
            cost = truck.CH * route_duration
        elif truck.esF6 == 1:
            cost = truck.CF6  # Fijo por 6 horas
        else:  # esF12 == 1
            cost = truck.CF12  # Fijo por 12 horas
        
        total_cost += cost
    
    return total_cost


def calculate_window_penalties(routes: List[List[int]], inst,
                              pcmin_c: float = 100.0,
                              pcmax_c: float = 500.0,
                              pcmin_nc: float = 50.0,
                              pcmax_nc: float = 200.0) -> float:
    """
    Calcular penalizaciones por violación de ventanas de tiempo.
    
    Args:
        pcmin_c: penalización por llegar antes EN cliente crítico
        pcmax_c: penalización por llegar después EN cliente crítico
        pcmin_nc: idem cliente no-crítico
        pcmax_nc: idem cliente no-crítico
        
    Returns:
        penalizacion_total
    """
    penalty = 0.0
    
    for route in routes:
        current_time = 0.0
        
        for client_id in route:
            client = inst.clients[client_id]
            
            # Simular llegada (simplificado)
            travel_time = 0.5  # 30 min por defecto
            arrival_time = current_time + travel_time
            
            # Verificar ventana
            if arrival_time < client.MinDC:
                # Llegó antes
                is_critical = client.escritico == 1
                pc = pcmax_c if is_critical else pcmax_nc
                penalty += pc * (client.MinDC - arrival_time)
            
            elif arrival_time > client.MaxDC:
                # Llegó después
                is_critical = client.escritico == 1
                pc = pcmin_c if is_critical else pcmin_nc
                penalty += pc * (arrival_time - client.MaxDC)
            
            # Actualizar tiempo actual
            current_time = arrival_time + client.TS
    
    return penalty


def calculate_return_penalty(routes: List[List[int]], inst,
                            tlim: float = 18.0,
                            preg: float = 1000.0) -> float:
    """
    Penalización por regresar después de tlim (18:00).
    
    Args:
        tlim: hora máxima deseada (default 18:00)
        preg: penalización por cada hora de exceso
        
    Returns:
        penalizacion_total
    """
    penalty = 0.0
    
    for route in routes:
        if not route:
            continue
        
        current_time = 0.0
        
        for client_id in route:
            client = inst.clients[client_id]
            travel_time = 0.5
            current_time += travel_time + client.TS
        
        # Tiempo de retorno al depósito
        travel_return = 0.5
        arrival_depot = current_time + travel_return
        
        if arrival_depot > tlim:
            penalty += preg * (arrival_depot - tlim)
    
    return penalty


def calculate_wait_penalty(routes: List[List[int]], inst,
                          pw: float = 50.0) -> float:
    """
    Penalización por horas de espera.
    
    Espera ocurre cuando se llega antes de MinDC.
    
    Args:
        pw: penalización por hora de espera
        
    Returns:
        penalizacion_total
    """
    penalty = 0.0
    
    for route in routes:
        current_time = 0.0
        
        for client_id in route:
            client = inst.clients[client_id]
            travel_time = 0.5
            arrival_time = current_time + travel_time
            
            # Si llegó antes, hay espera
            if arrival_time < client.MinDC:
                wait_time = client.MinDC - arrival_time
                penalty += pw * wait_time
                current_time = client.MinDC + client.TS
            else:
                current_time = arrival_time + client.TS
    
    return penalty


def calculate_z(routes: List[List[int]], inst,
               pcmin_c: float = 100.0,
               pcmax_c: float = 500.0,
               pcmin_nc: float = 50.0,
               pcmax_nc: float = 200.0,
               tlim: float = 18.0,
               preg: float = 1000.0,
               pw: float = 50.0) -> Tuple[float, Dict]:
    """
    Calcular función objetivo Z completa.
    
    Z = Costo_camiones 
      + Penalizacion_ventanas_criticas
      + Penalizacion_ventanas_normales
      + Penalizacion_regreso_tarde
      + Penalizacion_espera
    
    Returns:
        (Z_value, detalles_componentes)
    """
    
    cost = calculate_cost_trucks(routes, inst)
    window_penalty = calculate_window_penalties(routes, inst, pcmin_c, pcmax_c, pcmin_nc, pcmax_nc)
    return_penalty = calculate_return_penalty(routes, inst, tlim, preg)
    wait_penalty = calculate_wait_penalty(routes, inst, pw)
    
    Z = cost + window_penalty + return_penalty + wait_penalty
    
    details = {
        'Z': Z,
        'cost_trucks': cost,
        'window_penalty': window_penalty,
        'return_penalty': return_penalty,
        'wait_penalty': wait_penalty
    }
    
    return Z, details


def get_default_weights() -> Dict[str, float]:
    """
    Retornar pesos por defecto según especificación.
    """
    return {
        'pcmin_c': 100.0,    # Penalización llegar antes cliente crítico
        'pcmax_c': 500.0,    # Penalización llegar después cliente crítico
        'pcmin_nc': 50.0,    # Penalización llegar antes cliente normal
        'pcmax_nc': 200.0,   # Penalización llegar después cliente normal
        'tlim': 18.0,        # Límite de regreso
        'preg': 1000.0,      # Penalización regreso tarde
        'pw': 50.0           # Penalización espera
    }
