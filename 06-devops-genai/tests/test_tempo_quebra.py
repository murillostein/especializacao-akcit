import math

import pytest

from app.config import carregar_politica
from app.tempo_quebra import (
    SEGUNDOS_POR_ANO,
    avaliar_senha,
    estimar_tempo_quebra,
    formatar_tempo,
)


@pytest.fixture(autouse=True)
def politica_padrao(monkeypatch):
    """Isola os testes de variaveis de ambiente da maquina ou do runner."""
    monkeypatch.delenv("TENTATIVAS_POR_SEGUNDO", raising=False)
    monkeypatch.delenv("TEMPO_MINIMO_ANOS", raising=False)


# --- Configuracao -----------------------------------------------------------


def test_politica_carrega_valores_numericos():
    politica = carregar_politica()
    assert isinstance(politica["tentativas_por_segundo"], float)
    assert isinstance(politica["tempo_minimo_anos"], float)


def test_politica_respeita_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("TENTATIVAS_POR_SEGUNDO", "1000")
    assert carregar_politica()["tentativas_por_segundo"] == 1000.0


# --- Estimativa com taxa explicita (nao depende da politica) ----------------


def test_estimativa_com_taxa_explicita():
    # 2^10 combinacoes, metade testada em media, 1 tentativa/s -> 512 s
    assert estimar_tempo_quebra(10, tentativas_por_segundo=1) == 512


def test_entropia_zero_e_instantanea():
    assert estimar_tempo_quebra(0, tentativas_por_segundo=1e10) < 1


def test_entropia_negativa_e_rejeitada():
    with pytest.raises(ValueError):
        estimar_tempo_quebra(-1, tentativas_por_segundo=1)


def test_entropia_acima_do_limite_vira_infinito():
    assert estimar_tempo_quebra(5000, tentativas_por_segundo=1) == math.inf


# --- Estimativa usando a politica padrao (1e10 tentativas/s) ----------------


def test_estimativa_usa_politica_padrao():
    # 2^40 / 2 / 1e10 = ~55 s
    assert estimar_tempo_quebra(40) == pytest.approx(54.97558, rel=1e-4)


def test_senha_de_16_caracteres_atende_politica():
    # 16 caracteres com os 4 grupos (86 simbolos) -> 102.82 bits no modulo 01
    resultado = avaliar_senha(102.82)
    assert resultado["atende_politica"] is True
    assert resultado["tempo_legivel"] == "mais de mil anos"


def test_senha_fraca_nao_atende_politica():
    resultado = avaliar_senha(40)
    assert resultado["atende_politica"] is False
    assert resultado["tempo_legivel"] == "55 segundos"


# --- Formatacao -------------------------------------------------------------


@pytest.mark.parametrize(
    ("segundos", "esperado"),
    [
        (0.2, "instantaneo"),
        (30, "30 segundos"),
        (120, "2 minutos"),
        (7200, "2 horas"),
        (3 * 86400, "3 dias"),
        (5 * SEGUNDOS_POR_ANO, "5 anos"),
        (5000 * SEGUNDOS_POR_ANO, "mais de mil anos"),
    ],
)
def test_formatar_tempo(segundos, esperado):
    assert formatar_tempo(segundos) == esperado
