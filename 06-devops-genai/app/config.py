"""Politica de seguranca lida das variaveis de ambiente."""

import os


def carregar_politica() -> dict:
    """Le a politica de senhas do ambiente.

    - TENTATIVAS_POR_SEGUNDO: capacidade do atacante (padrao: 1e10, uma GPU moderna
      atacando um hash rapido).
    - TEMPO_MINIMO_ANOS: tempo medio de quebra exigido para a senha ser aceita.
    """
    return {
        "tentativas_por_segundo": os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10"),
        "tempo_minimo_anos": float(os.getenv("TEMPO_MINIMO_ANOS", "100")),
    }
