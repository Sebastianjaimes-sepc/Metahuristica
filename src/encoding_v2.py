"""
ENCODING V2: Vector solución con delimitadores de depósito (0)

Formato: [0, c1, c2, c3, 0, c4, c5, 0, c6, 0, ...]
         - 0 = depósito (inicio/fin de ruta)
         - Cada número entre 0s es un cliente
         - Cantidad de 0s = número de camiones
"""

import numpy as np
from typing import List, Tuple

DEPOT = 0

def encode_routes_v2(routes: List[List[int]]) -> List[int]:
    """
    Convierte lista de rutas en vector con delimitadores.
    
    Args:
        routes: [[1,3,5], [2,4], [6]] -> 3 rutas
        
    Returns:
        [0, 1, 3, 5, 0, 2, 4, 0, 6, 0] vector codificado
    """
    vector = []
    for route in routes:
        vector.append(DEPOT)
        vector.extend(route)
    vector.append(DEPOT)  # Depósito final
    return vector


def decode_vector_v2(vector: List[int]) -> List[List[int]]:
    """
    Convierte vector con delimitadores en lista de rutas.
    
    Args:
        vector: [0, 1, 3, 5, 0, 2, 4, 0, 6, 0]
        
    Returns:
        routes: [[1,3,5], [2,4], [6]]
    """
    routes = []
    current_route = []
    
    for node in vector:
        if node == DEPOT:
            if current_route:  # Si hay clientes en la ruta actual
                routes.append(current_route)
                current_route = []
        else:
            current_route.append(node)
    
    return routes


def vector_length(routes: int) -> int:
    """
    Calcula longitud del vector para R camiones y N clientes.
    
    Args:
        routes: número de camiones
        
    Returns:
        R + N + 1 (R depósitos de inicio + N clientes + 1 depósito final)
    """
    # En realidad depende de cómo distribuya clientes
    # Pero mínimo es R+1 (depósitos) + 1 (final)
    return None  # Se calcula dinámicamente


def count_depots(vector: List[int]) -> int:
    """Cuántos 0s (depósitos) hay en el vector = número de camiones."""
    return vector.count(DEPOT) - 1  # Restar 1 por el depósito final


def get_client_count(vector: List[int]) -> int:
    """Cuántos clientes hay en el vector (elementos != 0)."""
    return sum(1 for node in vector if node != DEPOT)


def get_route_for_client(vector: List[int], client: int) -> Tuple[int, int]:
    """
    Encontrar en qué ruta (depósito) está un cliente.
    
    Returns:
        (numero_ruta, posicion_en_ruta)
    """
    route_num = 0
    pos_in_route = 0
    in_route = False
    
    for node in vector:
        if node == DEPOT:
            if in_route:
                route_num += 1
                pos_in_route = 0
            in_route = True
        else:
            if node == client:
                return (route_num, pos_in_route)
            pos_in_route += 1
    
    return None


def validate_vector(vector: List[int], num_clients: int, num_trucks: int) -> bool:
    """
    Validar que el vector sea válido.
    
    Verificaciones:
    - Empieza y termina con 0 (depósito)
    - Tiene exactamente num_trucks depósitos de inicio
    - Contiene todos los clientes 1 a num_clients
    - Sin duplicados
    """
    if vector[0] != DEPOT or vector[-1] != DEPOT:
        return False
    
    depots = vector.count(DEPOT)
    if depots != num_trucks + 1:  # +1 por depósito final
        return False
    
    clients = [n for n in vector if n != DEPOT]
    if sorted(clients) != list(range(1, num_clients + 1)):
        return False
    
    if len(clients) != len(set(clients)):  # Hay duplicados
        return False
    
    return True


def get_route_length(route: List[int], inst) -> float:
    """
    Calcular distancia total de una ruta.
    
    Args:
        route: [1, 3, 5] (sin depósito)
        inst: Instance object con matriz de distancias
        
    Returns:
        distancia total
    """
    if not route:
        return 0.0
    
    dist = 0.0
    # Inicio desde depósito (nodo 0)
    prev = 0
    
    for client in route:
        dist += inst.distances[prev][client]
        prev = client
    
    # Regreso al depósito
    dist += inst.distances[prev][0]
    
    return dist


def count_critical_clients(route: List[int], inst) -> int:
    """Cuántos clientes críticos hay en una ruta."""
    count = 0
    for client in route:
        if inst.clients[client].escritico == 1:
            count += 1
    return count


def get_route_window_tightness(route: List[int], inst) -> float:
    """
    Medir qué tan ajustadas son las ventanas de tiempo en una ruta.
    
    Valores altos = ventanas estrechas = riesgo alto
    """
    if not route:
        return 0.0
    
    tightness = 0.0
    for client in route:
        c = inst.clients[client]
        window = c.MaxDC - c.MinDC
        if window > 0:
            tightness += 1.0 / window  # Inverso: ventana estrecha = tightness alta
    
    return tightness / len(route) if route else 0.0


def get_total_demand(route: List[int], inst) -> Tuple[float, float]:
    """
    Calcular demanda total (entrega + recogida) de una ruta.
    
    Returns:
        (demanda_entrega, demanda_recogida)
    """
    dem_e = 0.0
    dem_r = 0.0
    
    for client in route:
        c = inst.clients[client]
        dem_e += c.DemE
        dem_r += c.DemR
    
    return (dem_e, dem_r)
