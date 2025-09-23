import asyncio
import aiohttp
import traceback

async def test_upload():
    try:
        print('Iniciando test con timeout extendido...')
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            print('Probando endpoint /detect...')
            with open('test_data/logs_normal_1mb.txt', 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('file', f, filename='test.txt')
                
                async with session.post('http://localhost:8000/detect', data=form) as response:
                    print(f'Status: {response.status}')
                    print(f'Headers: {response.headers}')
                    
                    try:
                        # Intentar leer en chunks pequeños
                        content = await response.read()
                        print(f'Tamaño respuesta: {len(content)} bytes')
                        text_content = content.decode('utf-8', errors='ignore')
                        print(f'Contenido: {text_content[:200]}')
                        
                        if text_content.strip():
                            import json
                            result = json.loads(text_content)
                            print(f'JSON parseado: {result}')
                        
                    except Exception as read_e:
                        print(f'Error leyendo respuesta: {read_e}')
                    
    except Exception as e:
        print(f'Error: {e}')
        traceback.print_exc()

asyncio.run(test_upload())
