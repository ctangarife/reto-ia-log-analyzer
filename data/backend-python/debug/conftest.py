"""
Pytest configuration and fixtures for course system tests
"""
import pytest
import pytest_asyncio
from uuid import uuid4
from httpx import AsyncClient, ASGITransport

from main import app


# Fixtures simples que no crean nuevas conexiones
# Los tests usarán las conexiones existentes del servidor

@pytest_asyncio.fixture(scope="function")
async def client():
    """Test client for FastAPI app - uses existing server connections"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture(scope="function")
def test_user():
    """Test user UUID"""
    return uuid4()
