import sys
from pathlib import Path

import pytest

# Os testes de integracao exercitam o codigo real do modulo 01, sem copia-lo.
PROJETO_PRATICO = Path(__file__).resolve().parents[2] / "01-projeto-pratico"
sys.path.insert(0, str(PROJETO_PRATICO))

from password_generator import create_app  # noqa: E402


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return app.test_client()
