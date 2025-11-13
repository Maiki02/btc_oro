"""
Módulo de configuración para cargar variables de entorno.
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Config:
    """
    Clase de configuración que carga y expone las variables de entorno.
    """
    
    # API Keys
    COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
    GOLDAPI_KEY = os.getenv('GOLDAPI_KEY')
    
    # Security - API Authentication
    API_KEY = os.getenv('API_KEY')  # API Key para autenticar requests
    
    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'btc_oro_db')
    
    # Google Sheets API
    GOOGLE_SHEET_API_URL = os.getenv('GOOGLE_SHEET_API_URL')
    
    # Server Configuration
    SERVER_PORT = int(os.getenv('SERVER_PORT', 8080))
    
    # Timezone Configuration
    TARGET_TIMEZONE = 'America/Argentina/Buenos_Aires'
    TARGET_HOURS = [10, 17]  # 10:00 y 17:00 ART
    TIME_RANGE_MINUTES = 10  # ±10 minutos para búsqueda de BTC
    
    @classmethod
    def validate_config(cls):
        """
        Valida que las variables de entorno críticas estén configuradas.
        """
        required_vars = [
            ('GOLDAPI_KEY', cls.GOLDAPI_KEY),
            ('GOOGLE_SHEET_API_URL', cls.GOOGLE_SHEET_API_URL),
            ('API_KEY', cls.API_KEY),
        ]
        
        missing_vars = []
        for var_name, var_value in required_vars:
            if not var_value:
                missing_vars.append(var_name)
        
        if missing_vars:
            raise ValueError(f"Variables de entorno faltantes: {', '.join(missing_vars)}")
        
        return True