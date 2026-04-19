# Scripts de Backend

Esta carpeta contiene scripts utilitarios para administración del sistema.

## Estrategia de Testing Actual

La estrategia actual de testing y debug está en la carpeta [`debug/`](../debug/README.md), que contiene:

- Tests individuales de componentes
- Scripts de debug independientes
- Tests de integración con LLM

Para más información, consulta:
- [`debug/README.md`](../debug/README.md) - Guía de tests de componentes
- [`doc/debug_readme.md`](../../../doc/debug_readme.md) - Documentación completa

## Scripts Disponibles


---

## Scripts Eliminados (Legacy)

Los siguientes scripts fueron eliminados por ser obsoletos:

- `test_processing.py` - Usaba WebSockets legacy (sistema actual usa SSE)
- `test_processing_backup.py` - Backup obsoleto
- `test_processing_fixed.py` - Versión "fixed" obsoleta
- `setup_v2.sh` - Script de setup V2 (ya no hay V1/V2)
- `run_tests.sh` - Script legacy de pruebas
- `test_service.sh` - Script legacy de pruebas
- `generate_test_logs.py` - Generador de logs de prueba (solo usado en scripts obsoletos)
- `README_WARP.md` - Documentación específica de Warp
- `test_data/` - Datos de prueba (solo usados en scripts obsoletos)

---

**Última actualización**: 2026-02-01
