"""
src/utils/config.py
Configurazione dell'applicazione
"""

import os
from pathlib import Path


class Config:
    """
    Classe di configurazione per lo scraper
    
    Carica impostazioni da variabili d'ambiente o usa valori di default
    """
    
    def __init__(self):
        # Directory base del progetto
        self.base_dir = Path(__file__).parent.parent.parent
        self.data_dir = self.base_dir / "data"
        self.output_dir = self.data_dir / "output"
        self.logs_dir = self.base_dir / "logs"
        
        # Crea directory se non esistono
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Parametri di scraping
        # Numero massimo di richieste HTTP simultanee
        self.max_concurrent_requests = int(
            os.getenv('MAX_CONCURRENT_REQUESTS', '10')
        )
        
        # Timeout in secondi per ogni richiesta
        self.request_timeout = int(
            os.getenv('REQUEST_TIMEOUT', '30')
        )
        
        # Numero di tentativi in caso di errore
        self.retry_attempts = int(
            os.getenv('RETRY_ATTEMPTS', '3')
        )
        
        # User agent per le richieste HTTP
        self.user_agent = (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
        
        # URL base del sito
        self.base_url = "https://tipsterarea.com"
        
    def __repr__(self):
        """Rappresentazione stringa della configurazione"""
        return (
            f"Config("
            f"max_concurrent={self.max_concurrent_requests}, "
            f"timeout={self.request_timeout}s, "
            f"retry={self.retry_attempts}"
            f")"
        )
    
    def get_output_path(self, filename: str) -> Path:
        """
        Genera path completo per file di output
        
        Args:
            filename: Nome del file
            
        Returns:
            Path completo
        """
        return self.output_dir / filename
    
    def get_log_path(self, filename: str) -> Path:
        """
        Genera path completo per file di log
        
        Args:
            filename: Nome del file
            
        Returns:
            Path completo
        """
        return self.logs_dir / filename
