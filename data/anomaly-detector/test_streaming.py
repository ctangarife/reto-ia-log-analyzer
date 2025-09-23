import asyncio
import aiohttp
import json

async def test_streaming():
    try:
        print('Testing streaming response...')
        async with aiohttp.ClientSession() as session:
            with open('test_data/logs_normal_1mb.txt', 'rb') as f:
                form = aiohttp.FormData()
                form.add_field('file', f, filename='test.txt')
                
                async with session.post('http://localhost:8000/detect', data=form) as response:
                    print(f'Status: {response.status}')
                    print(f'Content-Type: {response.headers.get(" Content-Type\)}')
