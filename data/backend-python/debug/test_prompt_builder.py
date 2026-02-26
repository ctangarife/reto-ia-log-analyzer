"""
Debug script para PromptBuilder
Ejecutar: python -m debug.test_prompt_builder
"""
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.log_analysis import LogParser, LogMetadata
from services.prompts import PromptBuilder

def test_prompt_builder():
    """Prueba el constructor de prompts con diferentes escenarios"""
    parser = LogParser()
    builder = PromptBuilder()
    
    print("=" * 80)
    print("TEST: PromptBuilder")
    print("=" * 80)
    
    # Test 1: Prompt individual
    print("\n[TEST 1] Prompt Individual")
    print("-" * 80)
    log_entry = "2024-01-15 10:30:45 ERROR [Apache] Connection timeout from 192.168.1.100"
    metadata = parser.parse(log_entry)
    prompt = builder.build_single_prompt(metadata, score=-0.15)
    print(f"Log: {log_entry}")
    print(f"\nPrompt generado ({len(prompt)} caracteres):")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    # Test 2: Prompt de batch
    print("\n[TEST 2] Prompt Batch")
    print("-" * 80)
    anomalies = [
        (parser.parse("ERROR: Database connection failed"), -0.2),
        (parser.parse("WARNING: High memory usage detected"), -0.1),
        (parser.parse("CRITICAL: Disk space exceeded"), -0.25)
    ]
    batch_prompt = builder.build_batch_prompt(anomalies)
    print(f"Batch prompt generado ({len(batch_prompt)} caracteres):")
    print(batch_prompt[:500] + "..." if len(batch_prompt) > 500 else batch_prompt)
    
    # Test 3: System prompt
    print("\n[TEST 3] System Prompt")
    print("-" * 80)
    system_prompt = builder.get_system_prompt()
    print(f"System prompt ({len(system_prompt)} caracteres):")
    print(system_prompt)
    
    print("\n" + "=" * 80)
    print("✅ PromptBuilder test completado")
    print("=" * 80)

if __name__ == "__main__":
    test_prompt_builder()
