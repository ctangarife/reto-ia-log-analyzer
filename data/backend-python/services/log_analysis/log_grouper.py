"""
Utilidades para agrupar logs similares y evitar redundancia
"""
from typing import List, Dict, Tuple
from collections import Counter
from difflib import SequenceMatcher
import re


def extract_pattern(log_line: str) -> str:
    """
    Extrae el patrón base de un log removiendo:
    - Timestamps
    - IDs numéricos
    - Números de proceso/puerto
    - Marcas de tiempo únicas

    Args:
        log_line: Línea de log original

    Returns:
        Patrón base del log
    """
    # Remover timestamps comunes
    pattern = re.sub(r'\[\w{3} \w{3} \s+\d+ \d{2}:\d{2}:\d{2} \d{4}\]', '[TIMESTAMP]', log_line)
    pattern = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', '[TIMESTAMP]', pattern)
    pattern = re.sub(r'\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2}', '[TIMESTAMP]', pattern)

    # Remover IDs numéricos (process IDs, slot numbers, etc)
    pattern = re.sub(r'\bchild \d+\b', 'child [ID]', pattern)
    pattern = re.sub(r'\bslot \d+\b', 'slot [ID]', pattern)
    pattern = re.sub(r'\bstate \d+\b', 'state [ID]', pattern)
    pattern = re.sub(r'\b0x[0-9a-fA-F]+\b', '[HEX]', pattern)

    # Remover números de puerto
    pattern = re.sub(r':\d{4,5}', ':[PORT]', pattern)

    # Remover UUIDs
    pattern = re.sub(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b', '[UUID]', pattern)

    return pattern.strip()


def calculate_similarity(log1: str, log2: str) -> float:
    """
    Calcula similitud entre dos logs usando SequenceMatcher.

    Args:
        log1: Primera línea de log
        log2: Segunda línea de log

    Returns:
        Valor de similitud entre 0.0 y 1.0
    """
    return SequenceMatcher(None, log1, log2).ratio()


def group_similar_logs(
    logs: List[str],
    similarity_threshold: float = 0.85,
    min_group_size: int = 1
) -> Dict[str, Dict]:
    """
    Agrupa logs similares para evitar explicaciones redundantes.

    Args:
        logs: Lista de logs a agrupar
        similarity_threshold: Umbral de similitud (0.0-1.0)
        min_group_size: Tamaño mínimo para crear un grupo

    Returns:
        Diccionario de grupos con:
        {
            "pattern": "patrón base",
            "count": n,
            "logs": ["log1", "log2", ...],
            "first_occurrence": "log más reciente del grupo",
            "representative": "log más representativo"
        }
    """
    if not logs:
        return {}

    groups = {}
    pattern_to_logs = {}

    # Extraer patrones
    for log in logs:
        pattern = extract_pattern(log)
        if pattern not in pattern_to_logs:
            pattern_to_logs[pattern] = []
        pattern_to_logs[pattern].append(log)

    # Agrupar patrones similares
    processed_patterns = set()

    for pattern, pattern_logs in pattern_to_logs.items():
        if pattern in processed_patterns:
            continue

        # Buscar patrones similares existentes
        merged = False
        for existing_pattern in list(groups.keys()):
            similarity = calculate_similarity(pattern, existing_pattern)
            if similarity >= similarity_threshold:
                # Fusionar con grupo existente
                groups[existing_pattern]["logs"].extend(pattern_logs)
                groups[existing_pattern]["count"] += len(pattern_logs)
                processed_patterns.add(pattern)
                merged = True
                break

        if not merged:
            # Crear nuevo grupo
            groups[pattern] = {
                "pattern": pattern,
                "count": len(pattern_logs),
                "logs": pattern_logs,
                "first_occurrence": pattern_logs[0],  # Primer log del grupo
                "representative": pattern_logs[0]  # Podría mejorarse
            }
            processed_patterns.add(pattern)

    # Filtrar grupos por tamaño mínimo
    filtered_groups = {
        k: v for k, v in groups.items()
        if v["count"] >= min_group_size
    }

    return filtered_groups


def sample_representative_logs(
    groups: Dict[str, Dict],
    max_samples_per_group: int = 3,
    max_total_samples: int = 100
) -> List[str]:
    """
    Selecciona logs representantes de cada grupo para enviar al LLM.

    Args:
        groups: Grupos de logs (output de group_similar_logs)
        max_samples_per_group: Máximo de muestras por grupo
        max_total_samples: Máximo total de muestras

    Returns:
        Lista de logs representativos
    """
    representatives = []

    # Ordenar grupos por tamaño (descendente)
    sorted_groups = sorted(
        groups.values(),
        key=lambda x: x["count"],
        reverse=True
    )

    for group in sorted_groups:
        if len(representatives) >= max_total_samples:
            break

        # Tomar logs del grupo (limitado por max_samples_per_group)
        group_logs = group["logs"][:max_samples_per_group]
        representatives.extend(group_logs)

    return representatives[:max_total_samples]


def create_repetition_summary(groups: Dict[str, Dict]) -> str:
    """
    Crea un resumen de repeticiones para incluir en el prompt del LLM.

    Args:
        groups: Grupos de logs (output de group_similar_logs)

    Returns:
        String con resumen de repeticiones
    """
    if not groups:
        return ""

    # Ordenar por frecuencia
    sorted_groups = sorted(
        groups.values(),
        key=lambda x: x["count"],
        reverse=True
    )

    summary = "\n\n**NOTA IMPORTANTE - Anomalías Repetitivas:**\n"
    summary += "Se detectaron patrones que se repiten múltiples veces:\n\n"

    for i, group in enumerate(sorted_groups[:10], 1):  # Máximo 10 patrones
        pattern_short = group["pattern"][:80]
        if len(group["pattern"]) > 80:
            pattern_short += "..."

        summary += f"{i}. Patrón: \"{pattern_short}\"\n"
        summary += f"   - Se repite {group['count']} veces en el log\n"
        summary += f"   - Primera ocurrencia: {group['first_occurrence'][:60]}...\n\n"

    summary += "**IMPORTANTE:** Para anomalías repetitivas, proporciona una sola explicación "
    summary += "que aplique a todas las ocurrencias, e indica explícitamente cuántas veces se repite el patrón.\n"

    return summary


def count_unique_patterns(logs: List[str]) -> Tuple[int, int]:
    """
    Cuenta patrones únicos vs total de logs.

    Args:
        logs: Lista de logs

    Returns:
        Tuple (total_logs, unique_patterns)
    """
    patterns = set(extract_pattern(log) for log in logs)
    return len(logs), len(patterns)


def format_anomaly_groups_for_ui(groups: Dict[str, Dict]) -> List[Dict]:
    """
    Formatea grupos de anomalías para mostrar en el frontend.

    Args:
        groups: Grupos de logs (output de group_similar_logs)

    Returns:
        Lista de anomalías formateadas para UI
    """
    formatted = []

    for group_data in groups.values():
        formatted.append({
            "log_entry": group_data["representative"],
            "pattern": group_data["pattern"],
            "count": group_data["count"],
            "occurrences": group_data["count"],
            "first_occurrence": group_data["first_occurrence"],
            "is_grouped": True,
            "group_size": group_data["count"]
        })

    return formatted
