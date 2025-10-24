"""
Capa de repositorio para acceso a la base de datos MongoDB.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from typing import Optional
import logging

from ..models.schemas import AssetPriceRecord

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceRepository:
    """
    Repositorio para manejar la persistencia de precios en MongoDB.
    """
    
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str = "asset_prices"):
        """
        Inicializa el repositorio y la conexión con MongoDB.
        
        Args:
            mongo_uri: URI de conexión a MongoDB
            db_name: Nombre de la base de datos
            collection_name: Nombre de la colección (default: "asset_prices")
        """
        self.mongo_uri = mongo_uri
        self.db_name = db_name
        self.collection_name = collection_name
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
        
        self._connect()
    
    def _connect(self):
        """
        Establece la conexión con MongoDB.
        
        Raises:
            ConnectionFailure: Si no se puede conectar a MongoDB
        """
        try:
            logger.info(f"Conectando a MongoDB: {self.db_name}")
            self.client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Verificar la conexión
            self.client.admin.command('ping')
            
            self.db = self.client[self.db_name]
            self.collection = self.db[self.collection_name]
            
            logger.info(f"Conexión exitosa a MongoDB: {self.db_name}.{self.collection_name}")
            
        except ConnectionFailure as e:
            logger.error(f"Error al conectar con MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar con MongoDB: {e}")
            raise
    
    def save_price_record(self, record: AssetPriceRecord) -> str:
        """
        Guarda un registro de precio en la colección.
        
        Args:
            record: Objeto AssetPriceRecord a guardar
        
        Returns:
            ID del documento insertado como string
        
        Raises:
            PyMongoError: Si hay un error al guardar en MongoDB
        """
        try:
            # Convertir el modelo Pydantic a diccionario
            record_dict = record.model_dump()
            
            logger.info(f"Guardando registro en MongoDB: {record.asset_name} - ${record.price_usd}")
            
            result = self.collection.insert_one(record_dict)
            
            logger.info(f"Registro guardado exitosamente con ID: {result.inserted_id}")
            
            return str(result.inserted_id)
            
        except PyMongoError as e:
            logger.error(f"Error al guardar registro en MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al guardar registro: {e}")
            raise
    
    def get_latest_price(self, asset_name: str) -> Optional[dict]:
        """
        Obtiene el último precio registrado para un activo.
        
        Args:
            asset_name: Nombre del activo (BTC, XAU)
        
        Returns:
            Diccionario con el último registro o None si no existe
        """
        try:
            result = self.collection.find_one(
                {'asset_name': asset_name},
                sort=[('timestamp_utc', -1)]
            )
            return result
        except PyMongoError as e:
            logger.error(f"Error al obtener último precio: {e}")
            raise
    
    def close(self):
        """
        Cierra la conexión con MongoDB.
        """
        if self.client:
            logger.info("Cerrando conexión con MongoDB")
            self.client.close()
            self.client = None
            self.db = None
            self.collection = None
    
    def __enter__(self):
        """Soporte para context manager."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cierra la conexión al salir del context manager."""
        self.close()
    
    def __del__(self):
        """Asegura que la conexión se cierre al destruir el objeto."""
        self.close()