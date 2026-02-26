"""
Generador de explicaciones de fallback - Principio de Responsabilidad Única (SRP)
Responsabilidad: Generar explicaciones cuando el LLM no está disponible
"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class FallbackExplanationGenerator:
    """
    Generador de explicaciones de fallback - Responsabilidad Única: 
    Generar explicaciones básicas sin LLM.
    """
    
    # Patrones de error comunes y sus explicaciones
    ERROR_PATTERNS: Dict[str, str] = {
        'timeout': "El sistema está experimentando timeouts - algún servicio no responde a tiempo, lo que puede causar fallos en la aplicación",
        'connection': "Hay problemas de conectividad - el sistema no puede establecer conexiones con otros servicios, afectando la funcionalidad",
        'memory': "El sistema se está quedando sin memoria - esto puede causar que las aplicaciones fallen o funcionen muy lento",
        'oom': "El sistema se está quedando sin memoria - esto puede causar que las aplicaciones fallen o funcionen muy lento",
        'disk': "El disco está lleno - esto impide que el sistema guarde archivos y puede causar fallos en las aplicaciones",
        'space': "El disco está lleno - esto impide que el sistema guarde archivos y puede causar fallos en las aplicaciones",
        'permission': "Hay problemas de permisos - el sistema no puede acceder a ciertos archivos o recursos, limitando su funcionamiento",
        'denied': "Hay problemas de permisos - el sistema no puede acceder a ciertos archivos o recursos, limitando su funcionamiento"
    }
    
    def generate(self, log_entry: str, score: float) -> str:
        """
        Genera una explicación de fallback basada en análisis básico del log.
        
        Args:
            log_entry: Entrada de log
            score: Score de anomalía
            
        Returns:
            Explicación de fallback
        """
        content_lower = log_entry.lower()
        
        # Buscar patrones de error específicos
        if 'error' in content_lower or 'failed' in content_lower:
            for pattern, explanation in self.ERROR_PATTERNS.items():
                if pattern in content_lower:
                    return explanation
            
            # Error genérico
            severity = self._get_severity_text(score)
            return f"Se detectó un error en el sistema (severidad: {severity}) - esto indica un problema que necesita atención"
        
        # Advertencia
        elif 'warning' in content_lower or 'warn' in content_lower:
            return "Se detectó una advertencia - el sistema está funcionando pero hay algo que podría convertirse en un problema"
        
        # Anomalía genérica
        else:
            severity = self._get_severity_text(score)
            return f"Se detectó una anomalía inusual en el sistema (nivel: {severity}) - el comportamiento no es normal y requiere revisión"
    
    def _get_severity_text(self, score: float) -> str:
        """Convierte score a texto de severidad."""
        if score < -0.2:
            return "crítico"
        elif score < -0.1:
            return "alto"
        elif score < -0.05:
            return "medio"
        else:
            return "bajo"
