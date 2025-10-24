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

class ServiceResponse(BaseModel):
    """
    Modelo para la respuesta del servicio.
    """
    success: bool
    message: str
    records_processed: int = 0
    errors: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)