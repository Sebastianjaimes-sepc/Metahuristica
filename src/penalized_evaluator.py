"""
Evaluador con penalización por rutas largas.
Wrapper sobre evaluate_individual que añade penalización extra por rutas >max_hours.
"""

from src.simulator import evaluate_individual


def evaluate_with_route_penalty(individual, inst, max_hours=12.0, penalty_per_hour=50):
    """
    Evalúa un individuo y añade penalización por rutas que exceden max_hours.
    
    Args:
        individual: Vector de solución
        inst: Instancia del problema
        max_hours: Máximo de horas permitidas por ruta
        penalty_per_hour: Penalización por cada hora que excede max_hours
        
    Returns:
        dict con 'Z', 'cost', 'penalties', 'route_penalty'
    """
    result = evaluate_individual(individual, inst)
    
    # Calcular penalización por rutas largas
    route_penalty = 0
    for tid, details in result['details'].items():
        TT = details.get('TT', 0)
        if TT > max_hours:
            excess_hours = TT - max_hours
            route_penalty += excess_hours * penalty_per_hour
    
    # Objetivo total con penalización de rutas
    Z_penalized = result['Z'] + route_penalty
    
    return {
        'Z': Z_penalized,
        'Z_original': result['Z'],
        'cost': result['cost'],
        'penalty': result['penalty'],
        'route_penalty': route_penalty,
        'details': result['details']
    }
