"""
Modelos de datos usando Pydantic para validación y estructuración de datos.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator

# =============================================================================
# MODELOS PARA COINGECKO
# =============================================================================
class CoinGeckoPricePoint(BaseModel):
    """
    Modelo para un punto de precio de CoinGecko [timestamp, price].
    """
    timestamp: int  # Unix timestamp en milisegundos
    price: float
    
    @classmethod
    def from_list(cls, data: List[float]):
        """
        Crea una instancia desde una lista [timestamp, price].
        """
        if len(data) != 2:
            raise ValueError("Los datos deben contener exactamente 2 elementos: [timestamp, price]")
        return cls(timestamp=int(data[0]), price=data[1])

class CoinGeckoResponse(BaseModel):
    """
    Modelo para la respuesta de la API de CoinGecko market_chart/range.
    """
    prices: List[List[float]]
    market_caps: Optional[List[List[float]]] = None
    total_volumes: Optional[List[List[float]]] = None
    
    def get_price_points(self) -> List[CoinGeckoPricePoint]:
        """
        Convierte la lista de prices a objetos CoinGeckoPricePoint.
        """
        return [CoinGeckoPricePoint.from_list(price_data) for price_data in self.prices]
# 
# class MetalsApiResponse(BaseModel):
#     """
#     Modelo para la respuesta de la API de Metals-API.
#     """
#     success: bool
#     timestamp: int
#     historical: bool
#     base: str
#     date: str
#     rates: Dict[str, float]
#     
#     def get_xau_usd_rate(self) -> float:
#         """
#         Obtiene la tasa XAU/USD y realiza el cálculo 1/valor para obtener USD por onza.
#         """
#         xau_usd_rate = self.rates.get('XAUUSD')
#         if xau_usd_rate is None:
#             raise ValueError("La respuesta no contiene la tasa XAUUSD")
#         
#         # Cálculo crítico: 1 / valor_recibido para obtener USD por onza
#         return 1.0 / xau_usd_rate


# =============================================================================
# MODELO NUEVO - GoldAPI.io
# =============================================================================
class GoldApiResponse(BaseModel):
    """
    Modelo para la respuesta de la API de GoldAPI.io
    
    Ejemplo de respuesta:
    {
        "timestamp": 1729785599,
        "metal": "XAU",
        "currency": "USD",
        "exchange": "FOREXCOM",
        "symbol": "FOREXCOM:XAUUSD",
        "prev_close_price": 2737.845,
        "open_price": 2748.225,
        "low_price": 2723.845,
        "high_price": 2758.905,
        "open_time": 1729555200,
        "price": 2738.15,
        "ch": 0.305,
        "chp": 0.01,
        "ask": 2738.66,
        "bid": 2737.64
    }
    """
    timestamp: int = Field(..., description="Unix timestamp de la cotización")
    metal: str = Field(..., description="Símbolo del metal (ej: XAU)")
    currency: str = Field(..., description="Moneda de cotización (ej: USD)")
    exchange: str = Field(..., description="Exchange de origen")
    symbol: str = Field(..., description="Símbolo completo")
    prev_close_price: float = Field(..., description="Precio de cierre anterior")
    open_price: float = Field(..., description="Precio de apertura")
    low_price: float = Field(..., description="Precio más bajo del día")
    high_price: float = Field(..., description="Precio más alto del día")
    open_time: int = Field(..., description="Timestamp de apertura")
    price: float = Field(..., description="Precio actual")
    ch: float = Field(..., description="Cambio absoluto")
    chp: float = Field(..., description="Cambio porcentual")
    ask: float = Field(..., description="Precio de venta")
    bid: float = Field(..., description="Precio de compra")
    
    def get_price_usd(self) -> float:
        """
        Obtiene el precio del oro en USD por onza.
        
        Returns:
            Precio en USD
        """
        return self.price

class AssetPriceRecord(BaseModel):
    """
    Modelo normalizado para el registro de precios que se guarda en MongoDB.
    """
    asset_name: str = Field(..., description="Nombre del activo (BTC, XAU)")
    price_usd: float = Field(..., description="Precio en USD")
    timestamp_utc: datetime = Field(..., description="Timestamp en UTC")
    source_api: str = Field(..., description="API de origen (coingecko, metals-api)")
    collection_time_art: datetime = Field(..., description="Hora de recolección en ART")
    target_hour_art: int = Field(..., description="Hora objetivo en ART (10 o 17)")
    
    @validator('asset_name')
    def validate_asset_name(cls, v):
        allowed_assets = ['BTC', 'XAU']
        if v not in allowed_assets:
            raise ValueError(f'asset_name debe ser uno de: {allowed_assets}')
        return v
    
    @validator('source_api')
    def validate_source_api(cls, v):
        allowed_sources = ['coingecko', 'goldapi']
        if v not in allowed_sources:
            raise ValueError(f'source_api debe ser uno de: {allowed_sources}')
        return v
    
    @validator('target_hour_art')
    def validate_target_hour(cls, v):
        allowed_hours = [10, 17]
        if v not in allowed_hours:
            raise ValueError(f'target_hour_art debe ser uno de: {allowed_hours}')
        return v

class GoogleSheetRecord(BaseModel):
    """
    Modelo para los datos que se envían a Google Sheets.
    """
    date: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    time: str = Field(..., description="Hora en formato HH:MM")
    asset: str = Field(..., description="Nombre del activo")
    price_usd: float = Field(..., description="Precio en USD")
    source: str = Field(..., description="Fuente de los datos")
    
    @classmethod
    def from_asset_price_record(cls, record: AssetPriceRecord):
        """
        Crea una instancia desde un AssetPriceRecord.
        """
        return cls(
            date=record.collection_time_art.strftime('%Y-%m-%d'),
            time=record.collection_time_art.strftime('%H:%M'),
            asset=record.asset_name,
            price_usd=record.price_usd,
            source=record.source_api
        )
    
    @classmethod
    def from_daily_price_record(cls, daily_record: 'DailyPriceRecord') -> List['GoogleSheetRecord']:
        """
        Convierte un DailyPriceRecord (estructura consolidada MongoDB) a múltiples GoogleSheetRecord.
        
        Genera una fila por cada combinación de activo-hora en el registro diario.
        
        Ejemplo:
            DailyPriceRecord con BTC (hour_10, hour_17) y XAU (hour_10, hour_17)
            → Retorna 4 GoogleSheetRecord (una por cada combinación)
        
        Args:
            daily_record: DailyPriceRecord desde MongoDB
        
        Returns:
            Lista de GoogleSheetRecord (una por activo-hora)
        """
        records = []
        
        for asset_name, hourly_prices in daily_record.prices.items():
            for hour_key, snapshot in hourly_prices.items():
                # Extraer la hora del formato "hour_XX"
                hour_value = int(hour_key.split('_')[1])
                
                # Construir timestamp de la hora específica en ART
                # Usamos collection_time_art del snapshot como referencia de la fecha
                time_art = snapshot.collection_time_art.replace(
                    hour=hour_value,
                    minute=0,
                    second=0,
                    microsecond=0
                )
                
                record = cls(
                    date=daily_record.date,
                    time=time_art.strftime('%H:%M'),
                    asset=asset_name,
                    price_usd=snapshot.price_usd,
                    source=snapshot.source_api
                )
                records.append(record)
        
        return records

# =============================================================================
# NUEVA ESTRUCTURA - POR DÍA (PROPUESTA OPTIMIZADA)
# =============================================================================

class PriceSnapshot(BaseModel):
    """
    Modelo para un snapshot de precio en una hora específica.
    """
    price_usd: float = Field(..., description="Precio en USD")
    timestamp_utc: datetime = Field(..., description="Timestamp en UTC")
    source_api: str = Field(..., description="API de origen (coingecko, goldapi)")
    collection_time_art: datetime = Field(..., description="Hora de recolección en ART")
    
    @validator('source_api')
    def validate_source_api(cls, v):
        allowed_sources = ['coingecko', 'goldapi']
        if v not in allowed_sources:
            raise ValueError(f'source_api debe ser uno de: {allowed_sources}')
        return v


class HourlyPrice(BaseModel):
    """
    Modelo para los precios de un activo en diferentes horas del día.
    Las claves son strings como "hour_10", "hour_17", etc.
    """
    pass  # Será un Dict[str, PriceSnapshot] en DailyPriceRecord


class DailyPriceRecord(BaseModel):
    """
    Modelo para un registro diario consolidado de todos los activos y horas.
    
    Estructura del documento en MongoDB:
    {
      "_id": ObjectId(...),
      "date": "2025-10-24",
      "date_art": ISODate("2025-10-24T00:00:00-03:00"),
      "prices": {
        "BTC": {
          "hour_10": {
            "price_usd": 43250.75,
            "timestamp_utc": ISODate("2025-10-24T13:00:00Z"),
            "source_api": "coingecko",
            "collection_time_art": ISODate("2025-10-24T10:00:00-03:00")
          },
          "hour_17": {...}
        },
        "XAU": {
          "hour_10": {...},
          "hour_17": {...}
        }
      }
    }
    """
    date: str = Field(..., description="Fecha en formato YYYY-MM-DD")
    date_art: datetime = Field(..., description="Datetime del inicio del día en ART")
    # prices es un diccionario anidado: {asset_name: {hour_XX: PriceSnapshot}}
    prices: Dict[str, Dict[str, PriceSnapshot]] = Field(
        default_factory=dict,
        description="Estructura: {asset_name: {hour_XX: PriceSnapshot}}"
    )
    
    class Config:
        # Permitir tipos complejos
        arbitrary_types_allowed = True
    
    def add_price(self, asset_name: str, hour: int, price_snapshot: PriceSnapshot):
        """
        Agrega un precio a un activo en una hora específica.
        
        Args:
            asset_name: Nombre del activo (BTC, XAU, etc.)
            hour: Hora del día (0-23)
            price_snapshot: Snapshot del precio
        """
        if asset_name not in self.prices:
            self.prices[asset_name] = {}
        
        hour_key = f"hour_{hour:02d}"
        self.prices[asset_name][hour_key] = price_snapshot
    
    def get_price(self, asset_name: str, hour: int) -> Optional[PriceSnapshot]:
        """
        Obtiene el precio de un activo en una hora específica.
        
        Args:
            asset_name: Nombre del activo
            hour: Hora del día
        
        Returns:
            PriceSnapshot o None si no existe
        """
        hour_key = f"hour_{hour:02d}"
        return self.prices.get(asset_name, {}).get(hour_key)
    
    def get_all_prices_for_asset(self, asset_name: str) -> Dict[str, PriceSnapshot]:
        """
        Obtiene todos los precios de un activo durante el día.
        
        Args:
            asset_name: Nombre del activo
        
        Returns:
            Diccionario con todos los precios por hora
        """
        return self.prices.get(asset_name, {})
    
    def to_asset_price_records(self) -> List[AssetPriceRecord]:
        """
        Convierte el registro diario a una lista de AssetPriceRecord (formato antiguo).
        Útil para compatibilidad con código existente.
        
        Returns:
            Lista de AssetPriceRecord
        """
        records = []
        for asset_name, hourly_prices in self.prices.items():
            for hour_key, snapshot in hourly_prices.items():
                # Extraer la hora del formato "hour_XX"
                hour = int(hour_key.split('_')[1])
                
                record = AssetPriceRecord(
                    asset_name=asset_name,
                    price_usd=snapshot.price_usd,
                    timestamp_utc=snapshot.timestamp_utc,
                    source_api=snapshot.source_api,
                    collection_time_art=snapshot.collection_time_art,
                    target_hour_art=hour
                )
                records.append(record)
        
        return records


class ServiceResponse(BaseModel):
    """
    Modelo para la respuesta del servicio.
    """
    success: bool
    message: str
    records_processed: int = 0
    errors: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)