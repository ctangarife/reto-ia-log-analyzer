"""
Debug script para LogParser
Ejecutar: python -m debug.test_log_parser
"""
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.log_analysis import LogParser

def test_log_parser():
    """Prueba el parser de logs con diferentes tipos de logs"""
    parser = LogParser()
    
    test_logs = [
        "2024-01-15 10:30:45 ERROR [Apache] Connection timeout from 192.168.1.100",
        "Jan 15 10:30:45 server nginx: WARNING: Too many connections",
        "15/Jan/2024:10:30:45 +0000 ERROR mysql: Connection refused",
        "2024.01.15 kernel: CRITICAL: Out of memory",
        "DEBUG sshd: Authentication failed for user admin",
        "INFO mail server: SMTP connection established",
        "ERROR dns: Failed to resolve domain example.com",
        "2024-01-15 10:30:45 [systemd] Service failed to start"
    ]
    
    print("=" * 80)
    print("TEST: LogParser")
    print("=" * 80)
    
    for i, log_entry in enumerate(test_logs, 1):
        print(f"\n[{i}] Log Entry: {log_entry}")
        metadata = parser.parse(log_entry)
        print(f"    Timestamp: {metadata.timestamp}")
        print(f"    Level:      {metadata.level}")
        print(f"    Service:    {metadata.service}")
        print(f"    Raw:        {metadata.raw_entry[:60]}...")
    
    print("\n" + "=" * 80)
    print("✅ LogParser test completado")
    print("=" * 80)

if __name__ == "__main__":
    test_log_parser()
