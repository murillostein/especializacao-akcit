"""Testes das partes deterministicas do agente (nao chamam a API)."""

from pathlib import Path

from agente.diagnosticar_falha import (
    anonimizar_caminhos,
    arquivos_citados,
    extrair_secao_falhas,
    mascarar_segredos,
    montar_prompt,
    modulos_importados,
)

RAIZ = Path(__file__).resolve().parents[1]

LOG = """\
============================= test session starts =============================
rootdir: /builds/grupo/projeto
collected 2 items

=================================== FAILURES ===================================
_____________________ test_x _____________________
app/tempo_quebra.py:31: TypeError
=========================== short test summary info ============================
FAILED tests/test_tempo_quebra.py::test_x - TypeError
"""


def test_recorta_a_partir_da_secao_de_falhas():
    trecho, truncado = extrair_secao_falhas(LOG)
    assert trecho.startswith("=" * 35 + " FAILURES")
    assert "rootdir" not in trecho
    assert truncado is False


def test_log_sem_secao_de_falhas_e_enviado_inteiro():
    trecho, _ = extrair_secao_falhas("ERROR: could not install requirements")
    assert trecho == "ERROR: could not install requirements"


def test_arquivos_citados_ficam_dentro_do_projeto():
    log = LOG + 'File "/usr/lib/python3.12/json/__init__.py", line 3\n'
    citados = arquivos_citados(log, RAIZ)
    assert citados == [RAIZ / "app" / "tempo_quebra.py"]


def test_inclui_modulos_importados_pelo_codigo_citado():
    extras = modulos_importados([RAIZ / "app" / "tempo_quebra.py"], RAIZ)
    assert RAIZ / "app" / "config.py" in extras


def test_segredos_sao_mascarados():
    texto = (
        "ANTHROPIC_API_KEY=sk-ant-api03-abcdefghijklmnop "
        "token: glpat-AbCdEfGhIjKlMnOp ghp_abcdefghijklmnopqrstuvwxyz123456"
    )
    mascarado = mascarar_segredos(texto)
    assert "sk-ant-api03" not in mascarado
    assert "glpat-" not in mascarado
    assert "ghp_" not in mascarado
    assert "[REDACTED]" in mascarado


def test_caminhos_locais_sao_anonimizados():
    texto = f"generated xml file: {RAIZ / 'relatorio-testes.xml'}"
    assert str(RAIZ) not in anonimizar_caminhos(texto, RAIZ)


def test_prompt_contem_log_codigo_e_formato():
    prompt = montar_prompt(LOG, RAIZ)
    assert "FAILED tests/test_tempo_quebra.py::test_x" in prompt
    assert "#### `app/tempo_quebra.py`" in prompt
    assert "#### `app/config.py`" in prompt
    assert "## Causa raiz" in prompt


def test_prompt_minimo_nao_inclui_imports():
    prompt = montar_prompt(LOG, RAIZ, incluir_imports=False)
    assert "#### `app/config.py`" not in prompt
