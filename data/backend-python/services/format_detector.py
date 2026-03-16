"""
Servicio para detectar el formato de archivo y parsear estructuras.
Soporta CSV/TSV, Bro/Zeek logs, JSON logs, y texto plano.
"""
import re
import csv
import io
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum


class FileFormat(Enum):
    """Formatos de archivo soportados"""
    PLAIN_TEXT = "plain_text"
    CSV_COMMA = "csv_comma"
    CSV_SEMICOLON = "csv_semicolon"
    CSV_PIPE = "csv_pipe"
    CSV_TAB = "csv_tab"
    BRO_ZEEK = "bro_zeek"
    JSON_LINES = "json_lines"
    JSON_ARRAY = "json_array"
    SYSLOG = "syslog"
    APACHE = "apache"
    NGINX = "nginx"


class FormatDetector:
    """Detecta el formato de un archivo basado en su contenido"""

    def __init__(self):
        # Patrones para detectar formatos específicos
        self.patterns = {
            FileFormat.BRO_ZEEK: [
                r'^\d+\.\d+\|[a-zA-Z0-9]+\|\d+\.\d+\.\d+\.\d+\|\d+\|',  # Bro conn.log
                r'^ts\|uid\|id\.orig_h\|',  # Bro con headers
            ],
            FileFormat.SYSLOG: [
                r'^\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}\s+',  # Jan 01 12:00:00
                r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}',  # ISO timestamp
            ],
            FileFormat.APACHE: [
                r'^\d+\.\d+\.\d+\.\d+.*\[.*\].*".*".*\d{3}',  # Combined format
                r'^\d+\.\d+\.\d+\.\d+.*\[.*\].*".*"',  # Common format
            ],
            FileFormat.NGINX: [
                r'^\d+\.\d+\.\d+\.\d+.*-.*-.*\[.*\].*".*".*\d{3}.*".*".*".*',  # Nginx combined
            ],
        }

        # Palabras clave sospechosas por formato
        self.suspicious_keywords = {
            FileFormat.BRO_ZEEK: {
                'label': ['malicious', 'attack', 'botnet', 'c&c', 'command', 'control', 'torii', 'mirai'],
                'detailed-label': ['torii', 'mirai', 'botnet', 'ransomware', 'trojan'],
                'service': ['irc', 'telnet'],  # Servicios sospechosos en IoT
            },
            FileFormat.PLAIN_TEXT: [
                'error', 'failed', 'unauthorized', 'exception', 'timeout',
                'denied', 'critical', 'fatal', 'warning', 'attack', 'intrusion',
                'breach', 'malware', 'virus', 'exploit'
            ],
        }

        # IPs privadas (para detectar conexiones a IPs públicas sospechosas)
        self.private_ip_ranges = [
            r'10\.\d+\.\d+\.\d+',
            r'172\.(1[6-9]|2\d|3[01])\.\d+\.\d+',
            r'192\.168\.\d+\.\d+',
            r'127\.\d+\.\d+\.\d+',
        ]

    def detect_format(self, sample_lines: List[str]) -> Tuple[FileFormat, Dict[str, Any]]:
        """
        Detecta el formato del archivo basado en las primeras líneas.

        Returns:
            Tuple[FileFormat, metadata]: Formato detectado y metadata relevante
        """
        if not sample_lines:
            return FileFormat.PLAIN_TEXT, {}

        # Analizar las primeras 20 líneas
        lines_to_analyze = sample_lines[:min(20, len(sample_lines))]

        # 1. Detectar Bro/Zeek logs (específico)
        for line in lines_to_analyze:
            for pattern in self.patterns[FileFormat.BRO_ZEEK]:
                if re.match(pattern, line, re.IGNORECASE):
                    metadata = self._parse_bro_zeek_metadata(line)
                    return FileFormat.BRO_ZEEK, metadata

        # 2. Detectar formato JSON
        json_count = 0
        for line in lines_to_analyze:
            if line.strip().startswith('{') and line.strip().endswith('}'):
                json_count += 1
        if json_count > len(lines_to_analyze) * 0.8:
            # Verificar si es JSON array o JSON lines
            first_line = lines_to_analyze[0].strip()
            if first_line.startswith('['):
                return FileFormat.JSON_ARRAY, {}
            return FileFormat.JSON_LINES, {}

        # 3. Detectar delimitador CSV
        delimiter = self._detect_csv_delimiter(lines_to_analyze[0])
        if delimiter:
            if delimiter == ',':
                return FileFormat.CSV_COMMA, {'delimiter': ','}
            elif delimiter == ';':
                return FileFormat.CSV_SEMICOLON, {'delimiter': ';'}
            elif delimiter == '|':
                return FileFormat.CSV_PIPE, {'delimiter': '|'}
            elif delimiter == '\t':
                return FileFormat.CSV_TAB, {'delimiter': '\t'}

        # 4. Detectar formatos de log comunes
        for line in lines_to_analyze:
            for fmt, patterns in self.patterns.items():
                if fmt in [FileFormat.BRO_ZEEK, FileFormat.PLAIN_TEXT]:
                    continue
                for pattern in patterns:
                    if re.match(pattern, line):
                        return fmt, {}

        # 5. Default: texto plano
        return FileFormat.PLAIN_TEXT, {}

    def _detect_csv_delimiter(self, line: str) -> Optional[str]:
        """Detecta el delimitador CSV en una línea"""
        delimiters = ['|', ',', ';', '\t']
        counts = {}

        for delim in delimiters:
            counts[delim] = line.count(delim)

        # El delimitador debe aparecer al menos 3 veces y ser el más frecuente
        max_count = max(counts.values())
        if max_count < 3:
            return None

        for delim, count in counts.items():
            if count == max_count:
                return delim
        return None

    def _parse_bro_zeek_metadata(self, line: str) -> Dict[str, Any]:
        """Extrae metadata de logs de Bro/Zeek"""
        fields = line.split('|')
        metadata = {
            'has_header': False,
            'column_names': [],
            'expected_columns': len(fields)
        }

        # Verificar si la línea parece un header
        if any(field in fields for field in ['ts', 'uid', 'id.orig_h', 'label', 'detailed-label']):
            metadata['has_header'] = True
            metadata['column_names'] = fields

        # Intentar identificar columnas clave
        if len(fields) >= 22:
            # Bro conn.log tiene 23 columnas estándar
            # ts|uid|id.orig_h|id.orig_p|id.resp_h|id.resp_p|proto|service|...
            # Las últimas columnas suelen ser: ...|label|detailed-label
            metadata['label_idx'] = len(fields) - 2
            metadata['detailed_label_idx'] = len(fields) - 1

        return metadata

    def parse_structured_line(
        self,
        line: str,
        format_type: FileFormat,
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Parsea una línea según el formato detectado.

        Returns:
            Dict con la línea parseada y campos extraídos
        """
        result = {
            'raw': line,
            'format': format_type.value,
            'fields': {},
            'is_anomaly': False,
            'anomaly_reason': []
        }

        if format_type == FileFormat.BRO_ZEEK:
            result.update(self._parse_bro_zeek_line(line, metadata))
        elif format_type in [FileFormat.CSV_COMMA, FileFormat.CSV_SEMICOLON,
                            FileFormat.CSV_PIPE, FileFormat.CSV_TAB]:
            result.update(self._parse_csv_line(line, metadata))
        elif format_type in [FileFormat.JSON_LINES, FileFormat.JSON_ARRAY]:
            result.update(self._parse_json_line(line))
        else:
            # Texto plano: análisis simple
            result.update(self._parse_plain_text_line(line))

        return result

    def _parse_bro_zeek_line(self, line: str, metadata: Dict) -> Dict[str, Any]:
        """Parsea una línea de Bro/Zeek y detecta anomalías"""
        fields = line.split('|')
        result = {
            'fields': {},
            'is_anomaly': False,
            'anomaly_reason': []
        }

        # Mapeo de columnas de Bro conn.log
        if len(fields) >= 22:
            result['fields'] = {
                'ts': fields[0] if len(fields) > 0 else '',
                'uid': fields[1] if len(fields) > 1 else '',
                'orig_ip': fields[2] if len(fields) > 2 else '',
                'orig_port': fields[3] if len(fields) > 3 else '',
                'resp_ip': fields[4] if len(fields) > 4 else '',
                'resp_port': fields[5] if len(fields) > 5 else '',
                'proto': fields[6] if len(fields) > 6 else '',
                'service': fields[7] if len(fields) > 7 else '',
                'duration': fields[8] if len(fields) > 8 else '',
                'orig_bytes': fields[9] if len(fields) > 9 else '',
                'resp_bytes': fields[10] if len(fields) > 10 else '',
                'conn_state': fields[11] if len(fields) > 11 else '',
                'label': fields[21] if len(fields) > 21 else '',
                'detailed_label': fields[22] if len(fields) > 22 else '',
            }

            # Detectar anomalías específicas de Bro/Zeek
            label = result['fields']['label'].lower()
            detailed_label = result['fields']['detailed_label'].lower()

            # 1. Label explícitamente malicioso
            if any(kw in label for kw in self.suspicious_keywords[FileFormat.BRO_ZEEK]['label']):
                result['is_anomaly'] = True
                result['anomaly_reason'].append(f"Malicious label: {result['fields']['label']}")

            # 2. Detailed-label con malware conocido
            if any(kw in detailed_label for kw in self.suspicious_keywords[FileFormat.BRO_ZEEK]['detailed-label']):
                result['is_anomaly'] = True
                result['anomaly_reason'].append(f"Known malware: {result['fields']['detailed_label']}")

            # 3. Servicio sospechoso
            service = result['fields']['service'].lower()
            if any(kw in service for kw in self.suspicious_keywords[FileFormat.BRO_ZEEK]['service']):
                result['is_anomaly'] = True
                result['anomaly_reason'].append(f"Suspicious service: {service}")

            # 4. Conexión a IP externa en puertos sospechosos
            resp_ip = result['fields']['resp_ip']
            resp_port = result['fields']['resp_port']

            if not self._is_private_ip(resp_ip):
                # IP pública
                suspicious_ports = ['443', '80', '6667', '1337', '31337']
                if resp_port in suspicious_ports:
                    # Verificar si no es tráfico web normal
                    if result['fields']['service'] not in ['http', 'dns', 'ssl', 'tls']:
                        result['is_anomaly'] = True
                        result['anomaly_reason'].append(
                            f"Connection to external IP {resp_ip}:{resp_port}"
                        )

        return result

    def _parse_csv_line(self, line: str, metadata: Dict) -> Dict[str, Any]:
        """Parsea una línea CSV genérica"""
        delimiter = metadata.get('delimiter', ',')
        reader = csv.reader(io.StringIO(line), delimiter=delimiter)
        fields = next(reader, [])

        return {
            'fields': {str(i): field for i, field in enumerate(fields)},
            'is_anomaly': False,
            'anomaly_reason': []
        }

    def _parse_json_line(self, line: str) -> Dict[str, Any]:
        """Parsea una línea JSON"""
        import json
        try:
            data = json.loads(line)
            return {
                'fields': data,
                'is_anomaly': False,
                'anomaly_reason': []
            }
        except json.JSONDecodeError:
            return {
                'fields': {},
                'is_anomaly': False,
                'anomaly_reason': ['Invalid JSON']
            }

    def _parse_plain_text_line(self, line: str) -> Dict[str, Any]:
        """Analiza una línea de texto plano para anomalías"""
        keywords = self.suspicious_keywords[FileFormat.PLAIN_TEXT]
        line_lower = line.lower()

        anomaly_reasons = []

        for keyword in keywords:
            if keyword in line_lower:
                anomaly_reasons.append(f"Suspicious keyword: {keyword}")

        return {
            'fields': {},
            'is_anomaly': len(anomaly_reasons) > 0,
            'anomaly_reason': anomaly_reasons
        }

    def _is_private_ip(self, ip: str) -> bool:
        """Verifica si una IP es privada"""
        if not ip:
            return True
        for pattern in self.private_ip_ranges:
            if re.match(pattern, ip):
                return True
        return False


# Instancia global del detector
format_detector = FormatDetector()
