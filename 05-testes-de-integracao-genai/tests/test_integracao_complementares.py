"""Casos complementares obtidos por CURADORIA HUMANA das saídas v1 (prompts genéricos).

As respostas v1 (docs/saidas-llm/p1-v1-cenarios.md e p2-v1-erros.md) inventaram o
contrato da API e não rodam contra o sistema real, mas trouxeram ideias de casos
que nenhuma v2 cobriu. Cada ideia abaixo foi reescrita para o contrato real e teve
o comportamento confirmado executando a API antes de virar teste.

Mesma convenção dos demais arquivos: xfail(strict=True) documenta defeito real.
"""
import json
import threading

import pytest

from password_generator.config import Config

URL = "/api/passwords"
DEFAULT = Config.DEFAULT_PASSWORD_LENGTH
MSG_INTEIRO = "O comprimento da senha deve ser um inteiro."
MSG_MAX = f"O comprimento maximo e {Config.MAX_PASSWORD_LENGTH} caracteres."


def _post_raw(client, corpo, content_type="application/json"):
    return client.post(URL, data=corpo, content_type=content_type)


# ---------------------------------------------------------------------------
# Comportamentos corretos (passam hoje)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_literais_nao_padrao_do_json_sao_rejeitados(client, literal):
    """INT-X01 (origem: P2 v1): NaN/Infinity em length são rejeitados como não inteiros."""
    resp = _post_raw(client, f'{{"length": {literal}}}')
    # Real: json.loads aceita NaN/Infinity como float -> isinstance(int) falha -> 400.
    assert resp.status_code == 400
    assert resp.get_json() == {"error": MSG_INTEIRO}


@pytest.mark.parametrize(
    "corpo, status",
    [('{"length": 16, "length": 5000}', 400), ('{"length": 5000, "length": 16}', 200)],
    ids=["ultimo_invalido", "ultimo_valido"],
)
def test_chave_duplicada_valida_o_ultimo_valor(client, corpo, status):
    """INT-X02 (origem: P2 v1): com chave duplicada vale o último valor, e ele passa pela validação."""
    resp = _post_raw(client, corpo)
    assert resp.status_code == status
    if status == 400:
        assert resp.get_json() == {"error": MSG_MAX}


def test_erro_nao_reflete_entrada_nem_vaza_stacktrace(client):
    """INT-X03 (origem: P1 v1 e P2 v1): a mensagem de erro não ecoa a entrada nem expõe traceback."""
    ataque = "<script>alert(1)</script>"
    resp = client.post(URL, json={"length": ataque})
    texto = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert ataque not in texto
    assert "Traceback" not in texto


def test_api_continua_funcional_apos_sequencia_de_erros(client):
    """INT-X04 (origem: P2 v1): requisições inválidas, inclusive uma que gera 500, não afetam as seguintes."""
    for corpo in ("{", "[]", "[8]", '{"length": -1}', '{"length": NaN}', ""):
        _post_raw(client, corpo)

    resp = client.post(URL, json={"length": 20})
    assert resp.status_code == 200
    assert len(resp.get_json()["password"]) == 20


def test_requisicoes_concorrentes_geram_senhas_distintas(app):
    """INT-X05 (origem: P1 v1): 50 requisições em paralelo respondem 200 com senhas distintas."""
    resultados, erros = [], []

    def worker():
        try:
            resp = app.test_client().post(URL, json={"length": 24})
            resultados.append((resp.status_code, resp.get_json()["password"]))
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not erros
    assert all(status == 200 for status, _ in resultados)
    senhas = [senha for _, senha in resultados]
    assert len(set(senhas)) == len(senhas) == 50


# ---------------------------------------------------------------------------
# Defeitos confirmados (xfail estrito)
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: inteiro com mais de 4300 dígitos gera ValueError no parse, que "
    "get_json(silent=True) engole; length é ignorado e a API devolve 200 com o padrão",
)
def test_inteiro_com_milhares_de_digitos_retorna_400(client):
    """INT-X06 (origem: P2 v1): length com 5000 dígitos deveria ser rejeitado, não ignorado."""
    resp = _post_raw(client, '{"length": 1' + "0" * 5000 + "}")
    # Real: 200 com senha de comprimento DEFAULT.
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: JSON muito aninhado estoura RecursionError, que não é ValueError; "
    "get_json não o trata e a API responde 500 em HTML",
)
def test_json_profundamente_aninhado_retorna_400(client):
    """INT-X07 (origem: P2 v1): JSON com 100 mil níveis deveria gerar 400, não 500.

    Ajuste da curadoria: a v1 sugeria 2.000 níveis, mas o decoder do Python 3.12
    aceita essa profundidade; o 500 só aparece com profundidade bem maior.
    """
    profundidade = 100_000
    resp = _post_raw(client, '{"a":' * profundidade + "1" + "}" * profundidade)
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: corpo com UTF-8 inválido é descartado em silêncio e a API "
    "devolve 200 com os padrões",
)
def test_utf8_invalido_retorna_400(client):
    """INT-X08 (origem: P2 v1): corpo com bytes UTF-8 inválidos deveria ser rejeitado."""
    resp = _post_raw(client, b'{"length": "\xff\xfe"}')
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO (decisão de contrato): campos desconhecidos são ignorados; um "
    "erro de digitação como 'lenght' faz a validação ser pulada sem aviso",
)
def test_campo_desconhecido_e_rejeitado(client):
    """INT-X09 (origem: P2 v1): {"lenght": 7} deveria ser rejeitado em vez de virar senha padrão."""
    resp = client.post(URL, json={"lenght": 7})
    # Real: 200 com senha de comprimento DEFAULT.
    assert resp.status_code == 400


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO (segurança): a resposta contém uma senha e não envia "
    "Cache-Control: no-store; proxies e o navegador podem armazená-la",
)
def test_resposta_com_senha_nao_e_cacheavel(client):
    """INT-X10 (origem: P1 v1 e P3): a resposta 200 deveria proibir cache."""
    resp = client.post(URL, json={})
    assert resp.status_code == 200
    assert "no-store" in resp.headers.get("Cache-Control", "")


@pytest.mark.xfail(
    strict=True,
    reason="DEFEITO: MAX_CONTENT_LENGTH não está configurado; corpos de qualquer "
    "tamanho são lidos e processados",
)
def test_corpo_grande_demais_e_rejeitado(client):
    """INT-X11 (origem: P1 v1 e P2 v1): um corpo de 1 MB deveria receber 413."""
    corpo = json.dumps({"length": 16, "lixo": "x" * 1_000_000})
    resp = _post_raw(client, corpo)
    # Real: 200, o campo extra é ignorado.
    assert resp.status_code == 413
