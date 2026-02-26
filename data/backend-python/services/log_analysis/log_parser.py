"""
Servicio de análisis de logs - Principio de Responsabilidad Única (SRP)
Responsabilidad: Extraer información estructurada de logs
"""
import re
import logging
from typing import Optional, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LogMetadata:
    """Metadatos extraídos de un log entry"""
    timestamp: Optional[str] = None
    level: Optional[str] = None
    service: Optional[str] = None
    raw_entry: str = ""


class LogParser:
    """
    Parser de logs - Responsabilidad Única: Extraer información de logs.
    No conoce nada sobre LLM, prompts, o explicaciones.
    """
    
    # Patrones de timestamp comunes
    TIMESTAMP_PATTERNS = [
        r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',  # ISO format
        r'(\w+ \d+ \d+:\d+:\d+)',  # Syslog format
        r'(\d{2}/\w+/\d{4}:\d{2}:\d{2}:\d{2})',  # Apache/Nginx format
        r'(\d{4}\.\d{2}\.\d{2})',  # Date only
        r'(\d{10,})'  # Unix timestamp
    ]
    
    # Niveles de log estándar
    LOG_LEVELS = [
        'DEBUG', 'INFO', 'WARN', 'WARNING', 
        'ERROR', 'FATAL', 'CRITICAL', 'ALERT', 'EMERG'
    ]
    
    # Patrones de servicios comunes
    SERVICE_PATTERNS = {
        'Apache Web Server': ['apache', 'httpd', 'mod_'],
        'Nginx Web Server': ['nginx'],
        'Base de Datos': ['mysql', 'postgresql', 'mongodb', 'database'],
        'Sistema Operativo': ['kernel', 'systemd', 'init'],
        'Servicio de Red': ['ssh', 'telnet', 'ftp'],
        'Servidor de Correo': ['mail', 'smtp', 'pop', 'imap'],
        'Servidor DNS': ['dns', 'bind', 'named']
    }
    
    def parse(self, log_entry: str) -> LogMetadata:
        """
        Parsea un log entry y extrae metadatos.
        
        Args:
            log_entry: Entrada de log en texto plano
            
        Returns:
            LogMetadata con información extraída
        """
        return LogMetadata(
            timestamp=self._extract_timestamp(log_entry),
            level=self._extract_log_level(log_entry),
            service=self._identify_service(log_entry),
            raw_entry=log_entry
        )
    
    def _extract_timestamp(self, log_entry: str) -> Optional[str]:
        """Extrae timestamp del log entry."""
        for pattern in self.TIMESTAMP_PATTERNS:
            match = re.search(pattern, log_entry)
            if match:
                return match.group(1)
        return None
    
    def _extract_log_level(self, log_entry: str) -> Optional[str]:
        """Extrae nivel de log."""
        log_entry_upper = log_entry.upper()
        for level in self.LOG_LEVELS:
            if level in log_entry_upper:
                return level
        return None
    
    def _identify_service(self, log_entry: str) -> Optional[str]:
        """Identifica el servicio basado en el contenido del log."""
        content_lower = log_entry.lower()
        
        for service_name, keywords in self.SERVICE_PATTERNS.items():
            if any(keyword in content_lower for keyword in keywords):
                return service_name
        
        return "Sistema General"
