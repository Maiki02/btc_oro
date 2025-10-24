"""
Utilidades para el manejo de tiempo y conversiones de zona horaria.
"""
from datetime import datetime, timedelta
import pytz
from typing import Tuple

def get_art_timezone():
    """
    Retorna el objeto timezone de Argentina.
    """
    return pytz.timezone('America/Argentina/Buenos_Aires')

def get_utc_timezone():
    """
    Retorna el objeto timezone UTC.
    """
    return pytz.utc

def get_current_time_art() -> datetime:
    """
    Obtiene la hora actual en zona horaria de Argentina.
    """
    art_tz = get_art_timezone()
    return datetime.now(art_tz)

def get_timestamp_range_for_bitcoin(target_hour_art: int, range_minutes: int = 10) -> Tuple[int, int, datetime]:
    """
    Genera los timestamps de Unix (en segundos) para consultar la API de CoinGecko.
    
    Args:
        target_hour_art: Hora objetivo en ART (10 o 17)
        range_minutes: Rango de minutos antes y después (default: 10)
    
    Returns:
        Tupla con (from_timestamp, to_timestamp, target_datetime_utc)
        Los timestamps están en segundos (Unix timestamp)
    """
    art_tz = get_art_timezone()
    utc_tz = get_utc_timezone()
    
    # Obtener la fecha actual en ART
    now_art = get_current_time_art()
    
    # Crear el datetime objetivo en ART (hoy a la hora especificada)
    target_datetime_art = art_tz.localize(
        datetime(now_art.year, now_art.month, now_art.day, target_hour_art, 0, 0)
    )
    
    # Convertir a UTC
    target_datetime_utc = target_datetime_art.astimezone(utc_tz)
    
    # Calcular el rango (±range_minutes)
    from_datetime = target_datetime_utc - timedelta(minutes=range_minutes)
    to_datetime = target_datetime_utc + timedelta(minutes=range_minutes)
    
    # Convertir a Unix timestamp en segundos
    from_timestamp = int(from_datetime.timestamp())
    to_timestamp = int(to_datetime.timestamp())
    
    return from_timestamp, to_timestamp, target_datetime_utc

def get_date_string_for_metals_api() -> str:
    """
    Retorna la fecha actual en formato YYYY-MM-DD para la API de Metals-API.
    """
    now_art = get_current_time_art()
    return now_art.strftime('%Y-%m-%d')

def get_art_date_string() -> str:
    """
    Retorna la fecha actual en formato YYYY-MM-DD (zona horaria ART).
    
    Utilizada para indexar documentos consolidados diarios en MongoDB.
    
    Returns:
        Fecha en formato YYYY-MM-DD (ej: "2025-10-24")
    """
    now_art = get_current_time_art()
    return now_art.strftime('%Y-%m-%d')

def find_closest_price(prices_data: list, target_timestamp_utc: datetime) -> Tuple[float, datetime]:
    """
    Encuentra el precio más cercano al timestamp objetivo.
    
    Args:
        prices_data: Lista de objetos CoinGeckoPricePoint
        target_timestamp_utc: Datetime objetivo en UTC
    
    Returns:
        Tupla con (precio, datetime_del_precio)
    """
    if not prices_data:
        raise ValueError("La lista de precios está vacía")
    
    target_timestamp_ms = int(target_timestamp_utc.timestamp() * 1000)
    
    # Encontrar el punto más cercano
    closest_point = min(
        prices_data,
        key=lambda point: abs(point.timestamp - target_timestamp_ms)
    )
    
    # Convertir el timestamp de milisegundos a datetime
    price_datetime = datetime.fromtimestamp(closest_point.timestamp / 1000, tz=pytz.utc)
    
    return closest_point.price, price_datetime

def should_execute_now(tolerance_minutes: int = 5) -> Tuple[bool, int]:
    """
    Determina si el script debe ejecutarse ahora basándose en la hora actual en ART.
    
    Args:
        tolerance_minutes: Tolerancia en minutos para considerar que estamos en la hora objetivo
    
    Returns:
        Tupla (should_execute: bool, target_hour: int)
        Si should_execute es False, target_hour será 0
    """
    now_art = get_current_time_art()
    current_hour = now_art.hour
    current_minute = now_art.minute
    
    target_hours = [10, 17]
    
    for target_hour in target_hours:
        # Calcular la diferencia en minutos desde la hora objetivo
        if current_hour == target_hour and current_minute <= tolerance_minutes:
            return True, target_hour
        elif current_hour == target_hour - 1 and current_minute >= (60 - tolerance_minutes):
            return True, target_hour
    
    return False, 0

def convert_utc_to_art(utc_datetime: datetime) -> datetime:
    """
    Convierte un datetime UTC a zona horaria de Argentina.
    
    Args:
        utc_datetime: Datetime en UTC
    
    Returns:
        Datetime en ART
    """
    if utc_datetime.tzinfo is None:
        utc_datetime = pytz.utc.localize(utc_datetime)
    
    art_tz = get_art_timezone()
    return utc_datetime.astimezone(art_tz)