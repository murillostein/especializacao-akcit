"""Politica de seguranca lida das variaveis de ambiente."""

import math
import os


def _ler_float_positivo(nome: str, padrao: str) -> float:
    """Le uma variavel de ambiente numerica e falha cedo se o valor nao fizer sentido.

    os.getenv sempre devolve str: a conversao precisa acontecer aqui, na fronteira,
    e nao em quem consome a politica.
    """
    bruto = os.getenv(nome, padrao)
    try:
        valor = float(bruto)
    except ValueError:
        raise ValueError(f"{nome} deve ser numerico; recebido {bruto!r}.") from None
    if not math.isfinite(valor) or valor <= 0:
        raise ValueError(f"{nome} deve ser um numero positivo e finito; recebido {bruto!r}.")
    return valor


def carregar_politica() -> dict:
    """Le a politica de senhas do ambiente.

    - TENTATIVAS_POR_SEGUNDO: capacidade do atacante (padrao: 1e10, uma GPU moderna
      atacando um hash rapido).
    - TEMPO_MINIMO_ANOS: tempo medio de quebra exigido para a senha ser aceita.
    """
    return {
        "tentativas_por_segundo": _ler_float_positivo("TENTATIVAS_POR_SEGUNDO", "1e10"),
        "tempo_minimo_anos": _ler_float_positivo("TEMPO_MINIMO_ANOS", "100"),
    }
