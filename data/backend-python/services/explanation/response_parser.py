"""
Parser de respuestas del LLM - Principio de Responsabilidad Única (SRP)
Responsabilidad: Parsear y limpiar respuestas del LLM
"""
import re
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class ResponseParser:
    """
    Parser de respuestas - Responsabilidad Única: Limpiar y parsear respuestas del LLM.
    No conoce nada sobre cómo se generó la respuesta o qué hacer con ella.
    """
    
    # Prefijos comunes a remover
    PREFIXES_TO_REMOVE = [
        "Problema:", "Impacto:", "Solución:",
        "Análisis:", "Explicación:", "Respuesta:",
        "El problema es:", "El log indica:", "Este log muestra:"
    ]
    
    MAX_LENGTH = 300
    
    def clean_response(self, response: str) -> Optional[str]:
        """
        Limpia una respuesta del LLM removiendo prefijos y caracteres especiales.
        
        Args:
            response: Respuesta cruda del LLM
            
        Returns:
            Respuesta limpia o None si está vacía
        """
        if not response:
            return None
        
        cleaned = response.strip()
        
        # Remover prefijos comunes
        for prefix in self.PREFIXES_TO_REMOVE:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Limpiar caracteres especiales al inicio
        cleaned = re.sub(r'^[:\-\s]+', '', cleaned)
        
        # Limitar longitud
        if len(cleaned) > self.MAX_LENGTH:
            cleaned = cleaned[:self.MAX_LENGTH - 3] + "..."
        
        return cleaned.strip() if cleaned else None
    
    def parse_batch_response(
        self, 
        response: str, 
        expected_count: int
    ) -> List[str]:
        """
        Parsea una respuesta de batch y extrae explicaciones individuales.
        
        Args:
            response: Respuesta del LLM con múltiples explicaciones
            expected_count: Número esperado de explicaciones
            
        Returns:
            Lista de explicaciones parseadas
        """
        explanations = []
        lines = response.strip().split('\n')
        
        logger.debug(f"Parseando respuesta con {len(lines)} líneas")
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Patrón 1: "ANOMALÍA X: explicación"
            if line.startswith('ANOMALÍA ') and ':' in line:
                explanation = line.split(':', 1)[1].strip()
                if explanation:
                    explanations.append(explanation)
                    logger.debug(f"Explicación extraída (patrón 1): {explanation[:50]}...")
            
            # Patrón 2: "ANOMALÍA X explicación" (sin dos puntos)
            elif line.startswith('ANOMALÍA ') and ':' not in line:
                parts = line.split(' ', 2)
                if len(parts) >= 3:
                    explanation = parts[2].strip()
                    if explanation:
                        explanations.append(explanation)
                        logger.debug(f"Explicación extraída (patrón 2): {explanation[:50]}...")
            
            # Patrón 3: Líneas técnicas sin prefijo ANOMALÍA
            elif (self._is_technical_line(line) 
                  and len(explanations) < expected_count):
                explanations.append(line)
                logger.debug(f"Explicación extraída (patrón 3): {line[:50]}...")
        
        # Completar con fallbacks si faltan
        while len(explanations) < expected_count:
            explanations.append("Anomalía detectada - análisis detallado no disponible")
        
        return explanations[:expected_count]
    
    def _is_technical_line(self, line: str) -> bool:
        """Verifica si una línea contiene contenido técnico relevante."""
        keywords = [
            'apache', 'mod_jk', 'error', 'servidor', 
            'problema', 'estado', 'timeout', 'connection'
        ]
        return (
            any(keyword in line.lower() for keyword in keywords)
            and len(line) > 20
            and not line.startswith('ANOMALÍA')
        )
