"""
Capa de repositorio para acceso a la base de datos MongoDB.
Implementa el patrón UPSERT para consolidar precios diarios.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from ..models.schemas import DailyPriceRecord

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceRepository:
    """
    Repositorio para manejar la persistencia de precios en MongoDB.
    
    Implementa la estructura de esquema consolidada donde todos los precios
    de un día se almacenan en un único documento, organizados por activo y hora.
    """
    
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str = "daily_prices"):
        """
        Inicializa el repositorio y la conexión con MongoDB.
        
        Args:
            mongo_uri: URI de conexión a MongoDB
            db_name: Nombre de la base de datos
            collection_name: Nombre de la colección (default: "daily_prices")
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
            
            # Crear índices
            self._create_indexes()
            
            logger.info(f"Conexión exitosa a MongoDB: {self.db_name}.{self.collection_name}")
            
        except ConnectionFailure as e:
            logger.error(f"Error al conectar con MongoDB: {e}")
            raise
        except Exception as e:
            logger.error(f"Error inesperado al conectar con MongoDB: {e}")
            raise
    
    def _create_indexes(self):
        """
        Crea índices para optimizar las consultas.
        """
        try:
            # Índice único en 'date' para búsquedas rápidas
            self.collection.create_index("date", unique=True)
            logger.info("Índices creados exitosamente")
        except Exception as e:
            logger.warning(f"No se pudieron crear índices: {e}")
    
    def upsert_daily_prices(
        self,
        date: str,
        asset: str,
        hour: int,
        price_entry_dict: Dict[str, Any]
    ) -> bool:
        """
        Inserta o actualiza los precios diarios usando el patrón UPSERT.
        
        NUEVO: Con estructura array-based.
        - Si el documento no existe, lo crea.
        - Si la entrada (asset/hour) existe, la reemplaza.
        - Usa $pull para remover entrada vieja y $push para añadir la nueva.
        
        Ejemplo:
            date: "2025-10-24"
            asset: "BTC"
            hour: 15
            price_entry_dict: {
                "hour": 15,
                "price_usd": 43300.50,
                "timestamp_utc": "2025-10-24T18:15:00Z",
                "source_api": "coingecko",
                "collection_time_art": "2025-10-24T15:15:00-03:00"
            }
        
        Args:
            date: Fecha en formato YYYY-MM-DD
            asset: Código del activo (ej: "BTC", "XAU")
            hour: Hora (0-23)
            price_entry_dict: Dict con datos de la entrada de precio
        
        Returns:
            True si la operación fue exitosa, False en caso contrario
        """
        try:
            if self.collection is None:
                logger.warning("Colección MongoDB no disponible")
                return False
            
            # OPERACIÓN 1: Remover entrada existente con la misma hora (si existe)
            pull_result = self.collection.update_one(
                {"date": date},
                {
                    "$pull": { f"prices.{asset}": {"hour": hour} },
                    "$set": { "date": date, "updated_at": datetime.utcnow() },
                    "$setOnInsert": { "created_at": datetime.utcnow() }
                },
                upsert=True
            )
            
            # OPERACIÓN 2: Agregar la nueva entrada
            push_result = self.collection.update_one(
                {"date": date},
                {
                    "$push": { f"prices.{asset}": price_entry_dict },
                    "$set": { "updated_at": datetime.utcnow() }
                }
            )
            
            if pull_result.upserted_id:
                logger.info(f"Documento creado para {date}: {pull_result.upserted_id}")
            elif push_result.modified_count > 0:
                logger.info(f"Documento actualizado para {date} - {asset}/hour_{hour}")
            else:
                logger.debug(f"Sin cambios en documento para {date}")
            
            return True
            
        except PyMongoError as e:
            logger.error(f"Error al realizar upsert: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en upsert_daily_prices: {e}")
            return False
    
    def save_price_record(self, record: DailyPriceRecord) -> bool:
        """
        Guarda un registro de precios diario completo (estructura consolidada).
        
        Args:
            record: Instancia de DailyPriceRecord
        
        Returns:
            True si la operación fue exitosa, False en caso contrario
        """
        try:
            if self.collection is None:
                logger.warning("Colección MongoDB no disponible")
                return False
            # Convertir el modelo Pydantic a dict nativo
            # mode='json' serializa datetimes a ISO 8601 strings
            record_dict = record.model_dump(mode='json')

            logger.info(f"Guardando DailyPriceRecord para {record.date}:")
            logger.info(f"  Activos: {list(record_dict.get('prices', {}).keys())}")

            # Para evitar reemplazar todo el documento (y perder entradas previas),
            # iteramos por cada asset y cada entry y realizamos un upsert por entrada:
            # 1) $pull para eliminar una posible entrada con la misma 'hour'
            # 2) $push para añadir la nueva entrada
            # Esto preserva entradas previas de horas distintas.

            prices_map = record_dict.get('prices', {})

            for asset_name, entries in prices_map.items():
                for entry in entries:
                    try:
                        hour = entry.get('hour')

                        # OPERACIÓN 1: Eliminar entrada existente con la misma hora (si existe)
                        pull_result = self.collection.update_one(
                            { "date": record.date },
                            {
                                "$pull": { f"prices.{asset_name}": {"hour": hour} },
                                "$set": { 
                                    "date": record.date, 
                                    "date_art": record_dict.get('date_art'),
                                    "updated_at": datetime.utcnow() 
                                },
                                "$setOnInsert": { "created_at": datetime.utcnow() }
                            },
                            upsert=True
                        )

                        # OPERACIÓN 2: Agregar la nueva entrada
                        push_result = self.collection.update_one(
                            { "date": record.date },
                            {
                                "$push": { f"prices.{asset_name}": entry },
                                "$set": { "updated_at": datetime.utcnow() }
                            }
                        )

                        if pull_result.upserted_id:
                            logger.info(f"Documento creado para {record.date}: {pull_result.upserted_id} (asset={asset_name}, hour={hour})")
                        elif push_result.modified_count > 0:
                            logger.info(f"Documento actualizado para {record.date} - {asset_name}/hour_{hour}")
                        else:
                            logger.debug(f"Sin cambios para {record.date} - {asset_name}/hour_{hour}")

                    except Exception as e:
                        logger.error(f"Error al upsertear entrada {asset_name} hour={entry.get('hour')}: {e}")

            return True
            
        except PyMongoError as e:
            logger.error(f"Error PyMongo al guardar registro: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en save_price_record: {e}", exc_info=True)
            return False
    
    def get_daily_prices(self, date: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene los precios para un día específico.
        
        Args:
            date: Fecha en formato YYYY-MM-DD
        
        Returns:
            Dict con el documento MongoDB o None si no existe
        """
        try:
            if self.collection is None:
                logger.warning("Colección MongoDB no disponible")
                return None
            
            result = self.collection.find_one({"date": date})
            if result:
                # Remover el ObjectId para serialización
                result.pop("_id", None)
            
            return result
            
        except PyMongoError as e:
            logger.error(f"Error al obtener precios diarios: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en get_daily_prices: {e}")
            return None
    
    def get_date_range(
        self,
        start_date: str,
        end_date: str
    ) -> list:
        """
        Obtiene precios para un rango de fechas.
        
        Args:
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
        
        Returns:
            Lista de documentos MongoDB ordenados por fecha
        """
        try:
            if self.collection is None:
                logger.warning("Colección MongoDB no disponible")
                return []
            
            results = list(self.collection.find({
                "date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }).sort("date", 1))
            
            # Remover _id para serialización
            for doc in results:
                doc.pop("_id", None)
            
            return results
            
        except PyMongoError as e:
            logger.error(f"Error al obtener rango de fechas: {e}")
            return []
        except Exception as e:
            logger.error(f"Error inesperado en get_date_range: {e}")
            return []
    
    def get_latest_price(self, asset_name: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene el último precio registrado para un activo.
        
        Nota: Con la nueva estructura consolidada, esto busca el documento
        más reciente que tenga datos para el activo especificado.
        
        Args:
            asset_name: Código del activo (BTC, XAU)
        
        Returns:
            Dict con el último registro o None si no existe
        """
        try:
            if self.collection is None:
                logger.warning("Colección MongoDB no disponible")
                return None
            
            # Buscar el documento más reciente que tenga datos para este activo
            result = self.collection.find_one(
                {f"prices.{asset_name}": {"$exists": True}},
                sort=[("date", -1)]
            )
            
            if result:
                result.pop("_id", None)
            
            return result
            
        except PyMongoError as e:
            logger.error(f"Error al obtener último precio: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado en get_latest_price: {e}")
            return None
    
    def delete_collection(self) -> bool:
        """
        Elimina toda la colección (útil para testing).
        
        Returns:
            True si fue exitosa, False en caso contrario
        """
        try:
            if self.collection is None:
                logger.warning("Colección MongoDB no disponible")
                return False
            
            result = self.collection.delete_many({})
            logger.info(f"Colección eliminada: {result.deleted_count} documentos removidos")
            return True
            
        except PyMongoError as e:
            logger.error(f"Error al eliminar colección: {e}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado en delete_collection: {e}")
            return False
    
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