"""
Servicio de monitoreo de recursos del sistema
"""
import psutil
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class MemoryStats:
    """Estadísticas de memoria del sistema"""
    timestamp: datetime
    total_memory: int  # MB
    available_memory: int  # MB
    used_memory: int  # MB
    memory_percent: float
    process_memory: int  # MB
    process_memory_percent: float
    cpu_percent: float
    active_connections: int
    chunks_in_memory: int

@dataclass
class SystemAlert:
    """Alerta del sistema"""
    timestamp: datetime
    level: str  # 'warning', 'critical'
    message: str
    metric: str
    value: float
    threshold: float

class MonitoringService:
    """Servicio de monitoreo de recursos"""
    
    def __init__(self):
        self.memory_history: List[MemoryStats] = []
        self.alerts: List[SystemAlert] = []
        self.max_history_size = 1000
        self.monitoring_active = False
        
        # Umbrales de alerta
        self.memory_warning_threshold = 80.0  # 80%
        self.memory_critical_threshold = 90.0  # 90%
        self.cpu_warning_threshold = 80.0  # 80%
        self.cpu_critical_threshold = 95.0  # 95%
        
        # Referencias a otros servicios
        self.db_manager = None
        self.worker_service = None
        
    def set_services(self, db_manager, worker_service):
        """Configurar referencias a otros servicios"""
        self.db_manager = db_manager
        self.worker_service = worker_service
    
    async def get_memory_stats(self) -> MemoryStats:
        """Obtener estadísticas actuales de memoria"""
        try:
            # Memoria del sistema
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Memoria del proceso actual
            process = psutil.Process()
            process_memory = process.memory_info()
            process_memory_mb = process_memory.rss / 1024 / 1024
            
            # Conexiones activas
            active_connections = 0
            if self.db_manager:
                try:
                    # Contar conexiones activas en PostgreSQL
                    if hasattr(self.db_manager, 'postgres_pool'):
                        # Para LifoQueue, usar qsize() si está disponible
                        queue = self.db_manager.postgres_pool._queue
                        if hasattr(queue, 'qsize'):
                            active_connections = queue.qsize()
                        else:
                            # Fallback: estimar basado en el pool
                            active_connections = getattr(self.db_manager.postgres_pool, '_size', 0)
                except Exception as e:
                    logger.warning(f"Error obteniendo conexiones activas: {e}")
            
            # Chunks en memoria (estimación)
            chunks_in_memory = 0
            if self.worker_service:
                try:
                    chunks_in_memory = len(getattr(self.worker_service, 'active_chunks', []))
                except Exception as e:
                    logger.warning(f"Error obteniendo chunks en memoria: {e}")
            
            stats = MemoryStats(
                timestamp=datetime.utcnow(),
                total_memory=int(memory.total / 1024 / 1024),
                available_memory=int(memory.available / 1024 / 1024),
                used_memory=int(memory.used / 1024 / 1024),
                memory_percent=memory.percent,
                process_memory=int(process_memory_mb),
                process_memory_percent=(process_memory_mb / (memory.total / 1024 / 1024)) * 100,
                cpu_percent=cpu_percent,
                active_connections=active_connections,
                chunks_in_memory=chunks_in_memory
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de memoria: {e}")
            return None
    
    async def check_alerts(self, stats: MemoryStats) -> List[SystemAlert]:
        """Verificar si hay alertas basadas en las estadísticas"""
        alerts = []
        
        # Alerta de memoria del sistema
        if stats.memory_percent >= self.memory_critical_threshold:
            alert = SystemAlert(
                timestamp=datetime.utcnow(),
                level='critical',
                message=f'Memoria del sistema crítica: {stats.memory_percent:.1f}%',
                metric='system_memory',
                value=stats.memory_percent,
                threshold=self.memory_critical_threshold
            )
            alerts.append(alert)
        elif stats.memory_percent >= self.memory_warning_threshold:
            alert = SystemAlert(
                timestamp=datetime.utcnow(),
                level='warning',
                message=f'Memoria del sistema alta: {stats.memory_percent:.1f}%',
                metric='system_memory',
                value=stats.memory_percent,
                threshold=self.memory_warning_threshold
            )
            alerts.append(alert)
        
        # Alerta de CPU
        if stats.cpu_percent >= self.cpu_critical_threshold:
            alert = SystemAlert(
                timestamp=datetime.utcnow(),
                level='critical',
                message=f'CPU crítico: {stats.cpu_percent:.1f}%',
                metric='cpu',
                value=stats.cpu_percent,
                threshold=self.cpu_critical_threshold
            )
            alerts.append(alert)
        elif stats.cpu_percent >= self.cpu_warning_threshold:
            alert = SystemAlert(
                timestamp=datetime.utcnow(),
                level='warning',
                message=f'CPU alto: {stats.cpu_percent:.1f}%',
                metric='cpu',
                value=stats.cpu_percent,
                threshold=self.cpu_warning_threshold
            )
            alerts.append(alert)
        
        # Alerta de memoria del proceso
        if stats.process_memory_percent >= 50.0:  # 50% de la memoria total
            alert = SystemAlert(
                timestamp=datetime.utcnow(),
                level='warning',
                message=f'Memoria del proceso alta: {stats.process_memory_percent:.1f}%',
                metric='process_memory',
                value=stats.process_memory_percent,
                threshold=50.0
            )
            alerts.append(alert)
        
        return alerts
    
    async def start_monitoring(self, interval: int = 30):
        """Iniciar monitoreo continuo"""
        self.monitoring_active = True
        logger.info(f"Iniciando monitoreo de recursos cada {interval} segundos")
        
        while self.monitoring_active:
            try:
                # Obtener estadísticas
                stats = await self.get_memory_stats()
                if stats:
                    # Agregar al historial
                    self.memory_history.append(stats)
                    
                    # Mantener tamaño del historial
                    if len(self.memory_history) > self.max_history_size:
                        self.memory_history = self.memory_history[-self.max_history_size:]
                    
                    # Verificar alertas
                    alerts = await self.check_alerts(stats)
                    for alert in alerts:
                        self.alerts.append(alert)
                        logger.warning(f"ALERTA [{alert.level.upper()}]: {alert.message}")
                    
                    # Log de estadísticas cada 5 minutos
                    if len(self.memory_history) % 10 == 0:  # 10 * 30s = 5 minutos
                        logger.info(f"Memoria: {stats.memory_percent:.1f}% | "
                                  f"CPU: {stats.cpu_percent:.1f}% | "
                                  f"Proceso: {stats.process_memory:.1f}MB | "
                                  f"Conexiones: {stats.active_connections}")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error en monitoreo: {e}")
                await asyncio.sleep(interval)
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.monitoring_active = False
        logger.info("Monitoreo de recursos detenido")
    
    def get_current_stats(self) -> Optional[MemoryStats]:
        """Obtener estadísticas más recientes"""
        if self.memory_history:
            return self.memory_history[-1]
        return None
    
    def get_memory_history(self, limit: int = 100) -> List[Dict]:
        """Obtener historial de memoria para dashboard"""
        recent_history = self.memory_history[-limit:] if self.memory_history else []
        return [
            {
                'timestamp': stat.timestamp.isoformat(),
                'memory_percent': stat.memory_percent,
                'cpu_percent': stat.cpu_percent,
                'process_memory': stat.process_memory,
                'active_connections': stat.active_connections,
                'chunks_in_memory': stat.chunks_in_memory
            }
            for stat in recent_history
        ]
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict]:
        """Obtener alertas recientes"""
        recent_alerts = self.alerts[-limit:] if self.alerts else []
        return [
            {
                'timestamp': alert.timestamp.isoformat(),
                'level': alert.level,
                'message': alert.message,
                'metric': alert.metric,
                'value': alert.value,
                'threshold': alert.threshold
            }
            for alert in recent_alerts
        ]
    
    def get_system_summary(self) -> Dict:
        """Obtener resumen del sistema"""
        current_stats = self.get_current_stats()
        if not current_stats:
            return {}
        
        return {
            'timestamp': current_stats.timestamp.isoformat(),
            'memory': {
                'total_mb': current_stats.total_memory,
                'used_mb': current_stats.used_memory,
                'available_mb': current_stats.available_memory,
                'percent': current_stats.memory_percent,
                'process_mb': current_stats.process_memory,
                'process_percent': current_stats.process_memory_percent
            },
            'cpu': {
                'percent': current_stats.cpu_percent
            },
            'connections': {
                'active': current_stats.active_connections
            },
            'processing': {
                'chunks_in_memory': current_stats.chunks_in_memory
            },
            'alerts': {
                'total': len(self.alerts),
                'recent': len([a for a in self.alerts if (datetime.utcnow() - a.timestamp).seconds < 3600])
            }
        }

# Instancia global del servicio de monitoreo
monitoring_service = MonitoringService()
