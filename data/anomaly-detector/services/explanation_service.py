"""
Servicio para generar explicaciones inteligentes de anomalías usando LLM
"""
import re
import logging
import requests
import json
from typing import Dict, List, Tuple
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ExplanationService:
    """Servicio para generar explicaciones inteligentes usando LLM"""
    
    def __init__(self):
        self.ollama_url = "http://ollama-service:11434/api/generate"
        self.model_name = "qwen2.5:3b"
    
    async def get_llm_explanation(self, log_entry: str, score: float) -> str:
        """Obtiene una explicación inteligente del LLM para un log anómalo"""
        try:
            logger.info(f"=== Análisis de Log Sospechoso ===")
            logger.debug(f"Log a analizar: {log_entry}")
            
            # Crear prompt inteligente para el LLM
            prompt = self._create_intelligent_prompt(log_entry, score)
            
            logger.debug("Prompt enviado al LLM:")
            logger.debug(prompt)
            
            # Llamar al LLM
            response = await self._call_llm(prompt)
            
            if response:
                logger.info(f"Explicación generada por LLM: {response}")
                return response
            else:
                return self._generate_fallback_explanation(log_entry, score)
                
        except Exception as e:
            logger.error(f"Error obteniendo explicación del LLM: {e}")
            return self._generate_fallback_explanation(log_entry, score)
    
    def _create_intelligent_prompt(self, log_entry: str, score: float) -> str:
        """Crea un prompt inteligente para el LLM"""
        
        # Extraer información básica del log
        timestamp = self._extract_timestamp(log_entry)
        level = self._extract_log_level(log_entry)
        service = self._identify_service(log_entry)
        
        prompt = f"""Eres un experto en análisis de logs de sistemas. Analiza este log y explica QUÉ ESTÁ PASANDO de manera simple y clara para una persona sin conocimientos técnicos.

INFORMACIÓN DEL LOG:
- Log: {log_entry}
- Timestamp: {timestamp if timestamp else 'No detectado'}
- Nivel: {level if level else 'No detectado'}
- Servicio: {service if service else 'No detectado'}
- Score de anomalía: {score:.3f}

INSTRUCCIONES:
1. Explica QUÉ está pasando en términos simples
2. Explica POR QUÉ es un problema
3. Explica QUÉ puede pasar si no se soluciona
4. Sugiere QUÉ hacer para solucionarlo
5. Usa un lenguaje claro y comprensible para cualquier persona
6. Máximo 3 oraciones, sé conciso pero informativo

FORMATO DE RESPUESTA:
Problema: [Qué está pasando]
Impacto: [Por qué es importante]
Solución: [Qué hacer]

Ejemplo:
Problema: El servidor web no puede comunicarse con la base de datos
Impacto: Los usuarios no podrán acceder a la aplicación
Solución: Verificar que la base de datos esté funcionando y revisar la configuración de conexión

ANALIZA ESTE LOG:"""
        
        return prompt
    
    def _extract_timestamp(self, log_entry: str) -> str:
        """Extrae timestamp del log"""
        timestamp_patterns = [
            r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})',
            r'(\w+ \d+ \d+:\d+:\d+)',
            r'(\d{2}/\w+/\d{4}:\d{2}:\d{2}:\d{2})',
            r'(\d{4}\.\d{2}\.\d{2})',
            r'(\d{10,})'  # Unix timestamp
        ]
        
        for pattern in timestamp_patterns:
            match = re.search(pattern, log_entry)
            if match:
                return match.group(1)
        return None
    
    def _extract_log_level(self, log_entry: str) -> str:
        """Extrae nivel de log"""
        log_levels = ['DEBUG', 'INFO', 'WARN', 'WARNING', 'ERROR', 'FATAL', 'CRITICAL', 'ALERT', 'EMERG']
        for level in log_levels:
            if level in log_entry.upper():
                return level
        return None
    
    def _identify_service(self, log_entry: str) -> str:
        """Identifica el servicio basado en el contenido del log"""
        content_lower = log_entry.lower()
        
        # Servicios comunes
        if any(service in content_lower for service in ['apache', 'httpd', 'mod_']):
            return "Apache Web Server"
        elif any(service in content_lower for service in ['nginx']):
            return "Nginx Web Server"
        elif any(service in content_lower for service in ['mysql', 'postgresql', 'mongodb', 'database']):
            return "Base de Datos"
        elif any(service in content_lower for service in ['kernel', 'systemd', 'init']):
            return "Sistema Operativo"
        elif any(service in content_lower for service in ['ssh', 'telnet', 'ftp']):
            return "Servicio de Red"
        elif any(service in content_lower for service in ['mail', 'smtp', 'pop', 'imap']):
            return "Servidor de Correo"
        elif any(service in content_lower for service in ['dns', 'bind', 'named']):
            return "Servidor DNS"
        else:
            return "Sistema General"
    
    async def _call_llm(self, prompt: str) -> str:
        """Llama al LLM para obtener explicación"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 200
                }
            }
            
            response = requests.post(
                self.ollama_url,
                json=payload,
                timeout=15  # Timeout más corto para lotes
            )
            
            if response.status_code == 200:
                result = response.json()
                explanation = result.get('response', '').strip()
                
                # Limpiar la respuesta
                explanation = self._clean_llm_response(explanation)
                
                return explanation if explanation else None
            else:
                logger.error(f"Error en LLM: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error llamando al LLM: {e}")
            return None
    
    def _clean_llm_response(self, response: str) -> str:
        """Limpia la respuesta del LLM"""
        if not response:
            return None
        
        # Remover prefijos comunes
        prefixes_to_remove = [
            "Problema:", "Impacto:", "Solución:",
            "Análisis:", "Explicación:", "Respuesta:",
            "El problema es:", "El log indica:", "Este log muestra:"
        ]
        
        for prefix in prefixes_to_remove:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        # Limpiar caracteres especiales al inicio
        response = re.sub(r'^[:\-\s]+', '', response)
        
        # Limitar longitud
        if len(response) > 300:
            response = response[:297] + "..."
        
        return response.strip()
    
    def _generate_fallback_explanation(self, log_entry: str, score: float) -> str:
        """Genera una explicación de respaldo si el LLM falla"""
        
        # Análisis básico para fallback
        content_lower = log_entry.lower()
        
        if 'error' in content_lower or 'failed' in content_lower:
            if 'timeout' in content_lower:
                return "El sistema está experimentando timeouts - algún servicio no responde a tiempo, lo que puede causar fallos en la aplicación"
            elif 'connection' in content_lower:
                return "Hay problemas de conectividad - el sistema no puede establecer conexiones con otros servicios, afectando la funcionalidad"
            elif 'memory' in content_lower or 'oom' in content_lower:
                return "El sistema se está quedando sin memoria - esto puede causar que las aplicaciones fallen o funcionen muy lento"
            elif 'disk' in content_lower or 'space' in content_lower:
                return "El disco está lleno - esto impide que el sistema guarde archivos y puede causar fallos en las aplicaciones"
            elif 'permission' in content_lower or 'denied' in content_lower:
                return "Hay problemas de permisos - el sistema no puede acceder a ciertos archivos o recursos, limitando su funcionamiento"
            else:
                return f"Se detectó un error en el sistema (severidad: {self._get_severity_text(score)}) - esto indica un problema que necesita atención"
        
        elif 'warning' in content_lower or 'warn' in content_lower:
            return "Se detectó una advertencia - el sistema está funcionando pero hay algo que podría convertirse en un problema"
        
        else:
            return f"Se detectó una anomalía inusual en el sistema (nivel: {self._get_severity_text(score)}) - el comportamiento no es normal y requiere revisión"
    
    def _get_severity_text(self, score: float) -> str:
        """Convierte score a texto de severidad"""
        if score < -0.2:
            return "crítico"
        elif score < -0.1:
            return "alto"
        elif score < -0.05:
            return "medio"
        else:
            return "bajo"
    
    async def get_batch_explanations(self, anomaly_batch: List[Tuple[str, float]]) -> List[str]:
        """Obtiene explicaciones para un lote de anomalías de una vez"""
        try:
            if not anomaly_batch:
                return []
            
            logger.info(f"Procesando lote de {len(anomaly_batch)} anomalías con LLM")
            
            # Crear prompt para el lote completo
            prompt = self._create_batch_prompt(anomaly_batch)
            
            # Llamar al LLM una sola vez para todo el lote
            response = await self._call_llm(prompt)
            
            if response:
                logger.info(f"Respuesta del LLM: {response[:200]}...")
                
                # Parsear las explicaciones del lote
                explanations = self._parse_batch_response(response, len(anomaly_batch))
                logger.info(f"Explicaciones generadas para lote: {len(explanations)}")
                
                # Log de las explicaciones generadas
                for i, explanation in enumerate(explanations):
                    logger.info(f"Explicación {i+1}: {explanation[:100]}...")
                
                return explanations
            else:
                logger.warning("LLM no respondió, usando fallback individual")
                # Fallback individual si falla el lote
                return [self._generate_fallback_explanation(line, score) for line, score in anomaly_batch]
                
        except Exception as e:
            logger.error(f"Error procesando lote de anomalías: {e}")
            # Fallback individual si hay error
            return [self._generate_fallback_explanation(line, score) for line, score in anomaly_batch]
    
    def _create_batch_prompt(self, anomaly_batch: List[Tuple[str, float]]) -> str:
        """Crea un prompt para procesar múltiples anomalías"""
        
        prompt = f"""Eres un experto en análisis de logs. Analiza estas {len(anomaly_batch)} anomalías y explica QUÉ ESTÁ PASANDO en cada una de manera simple y clara.

INSTRUCCIONES:
1. Explica QUÉ está pasando en cada log
2. Explica POR QUÉ es un problema
3. Explica QUÉ puede pasar si no se soluciona
4. Usa un lenguaje claro y comprensible
5. Máximo 3 oraciones por anomalía
6. Sé conciso pero informativo
7. Explica a una persona sin conocimientos técnicos

FORMATO DE RESPUESTA:
Para cada anomalía, responde en una línea separada:
ANOMALÍA 1: [explicación]
ANOMALÍA 2: [explicación]
ANOMALÍA 3: [explicación]
...

ANOMALÍAS A ANALIZAR:"""
        
        for i, (line, score) in enumerate(anomaly_batch, 1):
            prompt += f"\n\nANOMALÍA {i} (Score: {score:.3f}):\n{line}"
        
        return prompt
    
    def _parse_batch_response(self, response: str, expected_count: int) -> List[str]:
        """Parsea la respuesta del LLM para extraer explicaciones individuales"""
        try:
            explanations = []
            lines = response.strip().split('\n')
            
            logger.info(f"Parseando respuesta del LLM con {len(lines)} líneas")
            logger.info(f"Respuesta completa: {response}")
            
            # Buscar patrones más flexibles
            for line in lines:
                line = line.strip()
                logger.debug(f"Línea a parsear: {line}")
                
                # Patrón 1: "ANOMALÍA X: explicación"
                if line.startswith('ANOMALÍA ') and ':' in line:
                    explanation = line.split(':', 1)[1].strip()
                    if explanation and explanation != "Anomalía detectada - análisis detallado no disponible":
                        explanations.append(explanation)
                        logger.debug(f"Explicación extraída (patrón 1): {explanation}")
                
                # Patrón 2: "ANOMALÍA X explicación" (sin dos puntos)
                elif line.startswith('ANOMALÍA ') and not ':' in line:
                    # Extraer todo después de "ANOMALÍA X"
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        explanation = parts[2].strip()
                        if explanation and explanation != "Anomalía detectada - análisis detallado no disponible":
                            explanations.append(explanation)
                            logger.debug(f"Explicación extraída (patrón 2): {explanation}")
                
                # Patrón 3: Líneas que contienen explicaciones técnicas (sin prefijo ANOMALÍA)
                elif (any(keyword in line.lower() for keyword in ['apache', 'mod_jk', 'error', 'servidor', 'problema', 'estado']) 
                      and not line.startswith('ANOMALÍA') 
                      and len(line) > 20
                      and len(explanations) < expected_count):
                    explanations.append(line)
                    logger.debug(f"Explicación extraída (patrón 3): {line}")
            
            logger.info(f"Explicaciones parseadas: {len(explanations)} de {expected_count}")
            
            # Si no se pudieron parsear todas, completar con fallbacks
            while len(explanations) < expected_count:
                explanations.append("Anomalía detectada - análisis detallado no disponible")
            
            return explanations[:expected_count]  # Limitar al número esperado
            
        except Exception as e:
            logger.error(f"Error parseando respuesta del lote: {e}")
            return ["Anomalía detectada - análisis detallado no disponible"] * expected_count
    
    async def get_detailed_explanation(self, log_entry: str, score: float) -> str:
        """Obtiene una explicación detallada para una anomalía individual (fallback)"""
        try:
            # Usar LLM para explicación inteligente
            explanation = await self.get_llm_explanation(log_entry, score)
            
            logger.debug(f"Explicación generada para log: {explanation}")
            return explanation
            
        except Exception as e:
            logger.error(f"Error generando explicación: {e}")
            return self._generate_fallback_explanation(log_entry, score)

# Instancia global del servicio
explanation_service = ExplanationService()