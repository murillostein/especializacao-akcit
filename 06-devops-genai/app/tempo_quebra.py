"""Estimativa do tempo medio para quebrar uma senha por forca bruta.

A entropia (em bits) vem do PasswordService.evaluate_strength do modulo 01.
"""

from __future__ import annotations

import math

from app.config import carregar_politica

SEGUNDOS_POR_MINUTO = 60
SEGUNDOS_POR_HORA = 60 * SEGUNDOS_POR_MINUTO
SEGUNDOS_POR_DIA = 24 * SEGUNDOS_POR_HORA
SEGUNDOS_POR_ANO = 365.25 * SEGUNDOS_POR_DIA

# Acima disso 2.0 ** bits estoura o float (limite ~1024).
ENTROPIA_MAXIMA_CALCULAVEL = 1000


def estimar_tempo_quebra(entropia_bits: float, tentativas_por_segundo: float | None = None) -> float:
    """Tempo medio, em segundos, para achar a senha testando metade do espaco de busca."""
    if entropia_bits < 0:
        raise ValueError("A entropia nao pode ser negativa.")
    if tentativas_por_segundo is None:
        tentativas_por_segundo = carregar_politica()["tentativas_por_segundo"]
    if entropia_bits > ENTROPIA_MAXIMA_CALCULAVEL:
        return math.inf

    combinacoes = 2.0 ** entropia_bits
    return (combinacoes / 2) / tentativas_por_segundo


def formatar_tempo(segundos: float) -> str:
    """Converte segundos em texto legivel para a interface."""
    if segundos < 1:
        return "instantaneo"
    if segundos < SEGUNDOS_POR_MINUTO:
        return f"{segundos:.0f} segundos"
    if segundos < SEGUNDOS_POR_HORA:
        return f"{segundos / SEGUNDOS_POR_MINUTO:.0f} minutos"
    if segundos < SEGUNDOS_POR_DIA:
        return f"{segundos / SEGUNDOS_POR_HORA:.0f} horas"
    if segundos < SEGUNDOS_POR_ANO:
        return f"{segundos / SEGUNDOS_POR_DIA:.0f} dias"
    anos = segundos / SEGUNDOS_POR_ANO
    if anos < 1000:
        return f"{anos:.0f} anos"
    return "mais de mil anos"


def avaliar_senha(entropia_bits: float) -> dict:
    """Resumo usado pela interface: tempo estimado e se atende a politica."""
    politica = carregar_politica()
    segundos = estimar_tempo_quebra(entropia_bits)
    return {
        "segundos": segundos,
        "tempo_legivel": formatar_tempo(segundos),
        "atende_politica": segundos / SEGUNDOS_POR_ANO >= politica["tempo_minimo_anos"],
    }
