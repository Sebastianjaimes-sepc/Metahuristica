"""
OPERATORS_RBX: Operadores Genéticos Especializados

- Route-Based Crossover (RBX): Intercambiar rutas completas
- Mutation SWAP: Intercambiar clientes dentro/entre rutas
- Mutation INSERT: Mover cliente de una ruta a otra
"""

import numpy as np
import random
from typing import List, Tuple
from src.encoding_v2 import DEPOT, decode_vector_v2, encode_routes_v2

def crossover_rbx(parent1: List[int], parent2: List[int], prob: float = 0.85, seed: int = None) -> List[int]:
    """
    Route-Based Crossover (RBX).
    
    Intercambiar rutas completas entre dos padres.
    
    Algoritmo:
    1. Decodificar ambos padres en rutas
    2. Decidir qué rutas tomar de padre1 vs padre2 (aleatorio)
    3. Re-codificar en vector
    
    Args:
        parent1, parent2: vectores [0, 1, 3, 0, 2, 0, ...]
        prob: probabilidad de aplicar RBX (default 85%)
        seed: para reproducibilidad
        
    Returns:
        child: nuevo vector hijo
    """
    if seed is not None:
        np.random.seed(seed)
    
    if random.random() > prob:
        # No aplicar RBX, retornar copia del padre 1
        return parent1.copy()
    
    # Decodificar rutas
    routes1 = decode_vector_v2(parent1)
    routes2 = decode_vector_v2(parent2)
    
    # Determinar cuántas rutas tomar de cada padre
    num_routes = len(routes1)
    cutpoint = random.randint(0, num_routes)
    
    # Crear hijo: primeras rutas de padre1, resto de padre2
    child_routes = routes1[:cutpoint] + routes2[cutpoint:]
    
    # Re-codificar
    child = encode_routes_v2(child_routes)
    
    return child


def mutation_swap(individual: List[int], prob: float = 0.1, seed: int = None) -> List[int]:
    """
    Mutation SWAP: Intercambiar dos clientes.
    
    Selecciona dos posiciones aleatorias (que no sean 0) e intercambia sus valores.
    
    Args:
        individual: vector [0, 1, 3, 0, 2, 0, ...]
        prob: probabilidad de aplicar mutación
        seed: para reproducibilidad
        
    Returns:
        mutated: vector mutado
    """
    if seed is not None:
        np.random.seed(seed)
    
    if random.random() > prob:
        return individual.copy()
    
    mutated = individual.copy()
    
    # Encontrar posiciones de clientes (no 0)
    client_positions = [i for i, node in enumerate(mutated) if node != DEPOT]
    
    if len(client_positions) < 2:
        return mutated
    
    # Seleccionar dos posiciones aleatorias
    pos1, pos2 = random.sample(client_positions, 2)
    
    # Intercambiar
    mutated[pos1], mutated[pos2] = mutated[pos2], mutated[pos1]
    
    return mutated


def mutation_insert(individual: List[int], prob: float = 0.1, seed: int = None) -> List[int]:
    """
    Mutation INSERT: Mover un cliente a otra posición.
    
    Selecciona un cliente, lo saca de su posición y lo inserta en otra.
    Puede ser dentro de la misma ruta o cambiar a otra ruta.
    
    Args:
        individual: vector [0, 1, 3, 0, 2, 0, ...]
        prob: probabilidad de mutación
        seed: para reproducibilidad
        
    Returns:
        mutated: vector mutado
    """
    if seed is not None:
        np.random.seed(seed)
    
    if random.random() > prob:
        return individual.copy()
    
    mutated = individual.copy()
    
    # Encontrar posiciones de clientes
    client_positions = [i for i, node in enumerate(mutated) if node != DEPOT]
    
    if len(client_positions) < 2:
        return mutated
    
    # Seleccionar cliente a mover
    from_pos = random.choice(client_positions)
    client = mutated[from_pos]
    
    # Seleccionar posición destino (distinta)
    other_positions = [p for p in client_positions if p != from_pos]
    to_pos = random.choice(other_positions)
    
    # Hacer el movimiento
    mutated = mutated[:from_pos] + mutated[from_pos+1:]  # Remover
    mutated = mutated[:to_pos] + [client] + mutated[to_pos:]  # Insertar
    
    return mutated


def mutation_segment_fill(individual: List[int], prob: float = 0.1, seed: int = None) -> List[int]:
    """
    Mutation Segmento + Rellenar (como en especificación).
    
    Algoritmo:
    1. Seleccionar punto de corte random
    2. Copiar segmento de este individuo
    3. Rellenar con clientes faltantes en orden
    
    Esta es una versión simplificada de la especificación.
    
    Args:
        individual: vector
        prob: probabilidad
        seed: seed
        
    Returns:
        mutated: vector mutado
    """
    if seed is not None:
        np.random.seed(seed)
    
    if random.random() > prob:
        return individual.copy()
    
    # Encontrar todos los clientes en el vector
    all_clients = set([node for node in individual if node != DEPOT])
    
    if len(all_clients) < 3:
        return individual.copy()
    
    # Seleccionar punto de corte
    client_positions = [i for i, node in enumerate(individual) if node != DEPOT]
    if len(client_positions) < 2:
        return individual.copy()
    
    cut1 = random.choice(client_positions)
    cut2 = random.choice([p for p in client_positions if p != cut1])
    
    if cut1 > cut2:
        cut1, cut2 = cut2, cut1
    
    # Extraer segmento
    segment = individual[cut1:cut2+1]
    segment_clients = set([n for n in segment if n != DEPOT])
    
    # Clientes faltantes
    missing = sorted(all_clients - segment_clients)
    
    # Reconstruir vector: segmento + clientes faltantes
    mutated = individual[:cut1] + segment + missing + individual[cut2+1:]
    
    # Normalizar: asegurar que comienza y termina con 0
    if mutated[0] != DEPOT:
        mutated = [DEPOT] + mutated
    if mutated[-1] != DEPOT:
        mutated = mutated + [DEPOT]
    
    return mutated


def calculate_route_priority(route: List[int], inst, 
                            w1: float = 0.40,
                            w2: float = 0.30,
                            w3: float = 0.15,
                            w4: float = 0.10,
                            w5: float = 0.05) -> float:
    """
    Calcular prioridad de una ruta basado en pesos w1-w5.
    
    w1 = 0.40   Urgencia por ventanas de tiempo (strict windows)
    w2 = 0.30   Duración estimada de la ruta
    w3 = 0.15   Cantidad de clientes críticos
    w4 = 0.10   Riesgo de atraso (window tightness)
    w5 = 0.05   Sensibilidad al tráfico (impact on timing)
    
    Higher priority = debe salir primero
    
    Args:
        route: [1, 3, 5] (sin depósito)
        inst: Instance
        w1-w5: pesos
        
    Returns:
        priority: valor entre 0-1 (mayor = más urgente)
    """
    if not route:
        return 0.0
    
    from src.encoding_v2 import get_route_length, count_critical_clients, get_route_window_tightness
    
    # u1: Urgencia por ventanas (% clientes críticos con ventanas estrechas)
    critical_count = count_critical_clients(route, inst)
    u1 = critical_count / len(route) if route else 0.0
    
    # u2: Duración relativa de la ruta (normalizar por duración máxima ~8 horas)
    route_length = get_route_length(route, inst)
    # Asumir que distancia ~= tiempo (simplificación)
    u2 = min(route_length / 100.0, 1.0)  # Normalizar a 0-1
    
    # u3: Proporción de clientes críticos
    u3 = critical_count / len(route) if route else 0.0
    
    # u4: Riesgo de atraso (tightness de ventanas)
    u4 = get_route_window_tightness(route, inst)
    
    # u5: Sensibilidad al tráfico (dummy: asumir proporcional a clientes)
    u5 = len(route) / 20.0  # Normalizar por ~20 clientes máximo
    
    # Calcular prioridad ponderada
    priority = (w1 * u1 + w2 * u2 + w3 * u3 + w4 * u4 + w5 * u5) / (w1 + w2 + w3 + w4 + w5)
    
    return priority


def sort_routes_by_priority(routes: List[List[int]], inst,
                           w1: float = 0.40,
                           w2: float = 0.30,
                           w3: float = 0.15,
                           w4: float = 0.10,
                           w5: float = 0.05) -> List[Tuple[int, float]]:
    """
    Ordenar rutas por prioridad (mayor primero = salir antes).
    
    Returns:
        List of (route_index, priority_score)
    """
    priorities = []
    
    for idx, route in enumerate(routes):
        priority = calculate_route_priority(route, inst, w1, w2, w3, w4, w5)
        priorities.append((idx, priority))
    
    # Ordenar por prioridad descendente (mayor primero)
    priorities.sort(key=lambda x: x[1], reverse=True)
    
    return priorities
