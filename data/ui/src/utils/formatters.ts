/**
 * Formatea bytes a una unidad legible
 * @param bytes Número de bytes a formatear
 * @returns String formateado (ej: "1.5 MB")
 */
export const formatBytes = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

/**
 * Formatea un timestamp ISO a formato legible
 * @param timestamp Timestamp en formato ISO
 * @returns String formateado (ej: "15 Ene 2025, 14:30")
 */
export const formatTimestamp = (timestamp: string): string => {
    if (!timestamp) return '';
    
    const date = new Date(timestamp);
    const options: Intl.DateTimeFormatOptions = {
        day: 'numeric',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    };
    
    return date.toLocaleDateString('es-ES', options);
};

/**
 * Formatea un número a porcentaje
 * @param value Número a formatear
 * @param decimals Número de decimales
 * @returns String formateado (ej: "85.5%")
 */
export const formatPercentage = (value: number, decimals: number = 1): string => {
    return `${value.toFixed(decimals)}%`;
};

/**
 * Formatea una duración en segundos a formato legible
 * @param seconds Número de segundos
 * @returns String formateado (ej: "2h 30m" o "45s")
 */
export const formatDuration = (seconds: number): string => {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    }
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    
    return `${minutes}m`;
};

/**
 * Formatea un score de anomalía a un texto descriptivo
 * @param score Score de anomalía
 * @returns String descriptivo del nivel
 */
export const formatAnomalyLevel = (score: number): string => {
    if (score < -0.3) return 'Alto';
    if (score < -0.2) return 'Medio';
    return 'Bajo';
};
