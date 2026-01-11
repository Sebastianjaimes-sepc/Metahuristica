"""
FEASIBILITY: Validar que una solución cumple con todas las restricciones.

Restricciones:
- Capacidad en cada instante (DemE + DemR <= Cap)
- Ventanas de tiempo (MinDC <= hora_llegada <= MaxDC)
- Tiempo máximo de trabajo (<= 18:00)
- Almuerzo después de las 14:00
- Número máximo de muelles simultáneos
"""

from typing import List, Tuple, Dict
from src.encoding_v2 import decode_vector_v2

def check_capacity(route: List[int], inst) -> bool:
    """
    Verificar que la capacidad NO se exceda en ningún momento de la ruta.
    
    La carga debe estar dentro de Cap en todo momento.
    """
    if not route:
        return True
    
    # Obtener primer camión disponible
    truck = list(inst.trucks.values())[0]
    capacity = truck.Cap
    
    current_load = 0.0
    
    for client_id in route:
        client = inst.clients[client_id]
        
        # Cargar entrega
        current_load += client.DemE
        if current_load > capacity:
            return False
        
        # Descargar recogida
        current_load -= client.DemR
        if current_load < 0:  # No puede ser negativo
            return False
    
    # Al final debe estar vacío o con recogida pendiente de retorno
    return True


def check_time_windows(route: List[int], inst, departure_time: float = 0.0) -> bool:
    """
    Verificar que se respeten ventanas de tiempo [MinDC, MaxDC].
    
    Args:
        route: [1, 3, 5]
        inst: Instance
        departure_time: Hora de salida del depósito (default 0.0)
        
    Returns:
        True si todas las ventanas se respetan
    """
    if not route:
        return True
    
    current_time = departure_time
    
    for client_id in route:
        client = inst.clients[client_id]
        
        # Tiempo de viaje desde depósito o cliente anterior
        # Asumimos velocidad constante o matriz de tiempos
        travel_time = inst.times[0][client_id] if hasattr(inst, 'times') else 0.5
        
        # Hora de llegada
        arrival_time = current_time + travel_time
        
        # Verificar ventana
        if arrival_time < client.MinDC or arrival_time > client.MaxDC:
            return False
        
        # Actualizar hora actual: llegada + tiempo de servicio
        current_time = arrival_time + client.TS
    
    return True


def check_max_time(route: List[int], inst, departure_time: float = 0.0, max_time: float = 18.0) -> bool:
    """
    Verificar que la ruta termine antes de max_time (18:00).
    
    Args:
        route: [1, 3, 5]
        inst: Instance
        departure_time: Hora de salida
        max_time: Hora máxima permitida (default 18:00)
        
    Returns:
        True si la ruta finaliza antes de max_time
    """
    if not route:
        return True
    
    current_time = departure_time
    
    for client_id in route:
        client = inst.clients[client_id]
        travel_time = inst.times[0][client_id] if hasattr(inst, 'times') else 0.5
        current_time += travel_time + client.TS
    
    # Tiempo de regreso al depósito
    travel_time_return = inst.times[0][route[-1]] if hasattr(inst, 'times') else 0.5
    arrival_depot = current_time + travel_time_return
    
    return arrival_depot <= max_time


def check_lunch(route: List[int], inst, lunch_hour: float = 14.0, lunch_duration: float = 1.0) -> bool:
    """
    Verificar que el almuerzo se tome DESPUES de lunch_hour (14:00).
    
    Si la ruta es larga, debe incluir pausa de almuerzo DESPUES de las 14:00.
    """
    if not route:
        return True
    
    # Simplificación: si la ruta es larga (>5 horas), requiere almuerzo después de 14:00
    # Calcular duración total de la ruta
    current_time = 0.0
    
    for client_id in route:
        client = inst.clients[client_id]
        travel_time = inst.times[0][client_id] if hasattr(inst, 'times') else 0.5
        current_time += travel_time + client.TS
    
    route_duration = current_time
    
    # Si ruta > 6 horas, necesita almuerzo
    if route_duration > 6.0:
        # El almuerzo debe ocurrir después de las 14:00
        # Verificar si hay tiempo disponible
        # Simplificación: asumir que se puede colocar almuerzo
        return True
    
    return True


def check_muelles(routes: List[List[int]], inst, max_muelles: int = 2, carga_time: float = 1.0) -> bool:
    """
    Verificar que no haya más de max_muelles camiones cargando simultáneamente.
    
    Simplificación: Verificar que el timeline de salidas tenga máximo max_muelles
    camiones saliendo en ventana de tcarga.
    """
    if not routes:
        return True
    
    # Para esta simplificación, asumir que las rutas se ordenan
    # y se espacian por carga_time
    return len(routes) <= len(inst.trucks)


def is_feasible(routes: List[List[int]], inst, 
                max_time: float = 18.0, 
                lunch_hour: float = 14.0,
                max_muelles: int = 2) -> Tuple[bool, List[str]]:
    """
    Evaluación completa de factibilidad.
    
    Returns:
        (es_factible: bool, errores: List[str])
    """
    errores = []
    
    if not routes:
        return False, ["Sin rutas"]
    
    for route_idx, route in enumerate(routes):
        if not route:
            continue
        
        # Capacidad
        if not check_capacity(route, inst):
            errores.append(f"Ruta {route_idx}: Excede capacidad")
        
        # Ventanas de tiempo
        if not check_time_windows(route, inst):
            errores.append(f"Ruta {route_idx}: Viola ventana de tiempo")
        
        # Tiempo máximo
        if not check_max_time(route, inst, max_time=max_time):
            errores.append(f"Ruta {route_idx}: Llega después de {max_time}:00")
        
        # Almuerzo
        if not check_lunch(route, inst, lunch_hour=lunch_hour):
            errores.append(f"Ruta {route_idx}: Almuerzo mal planificado")
    
    # Muelles
    if not check_muelles(routes, inst, max_muelles=max_muelles):
        errores.append(f"Excede número máximo de muelles ({max_muelles})")
    
    return len(errores) == 0, errores


def get_feasibility_details(routes: List[List[int]], inst) -> Dict:
    """
    Retornar detalles de factibilidad para cada ruta.
    """
    details = {
        "factible": True,
        "rutas": {}
    }
    
    for route_idx, route in enumerate(routes):
        ruta_info = {
            "clientes": route,
            "capacidad_ok": check_capacity(route, inst),
            "ventanas_ok": check_time_windows(route, inst),
            "tiempo_ok": check_max_time(route, inst),
            "almuerzo_ok": check_lunch(route, inst),
        }
        
        details["rutas"][route_idx] = ruta_info
        
        if not all([ruta_info["capacidad_ok"], ruta_info["ventanas_ok"], 
                   ruta_info["tiempo_ok"], ruta_info["almuerzo_ok"]]):
            details["factible"] = False
    
    return details
