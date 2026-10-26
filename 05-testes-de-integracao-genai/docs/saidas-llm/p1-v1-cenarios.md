# Saída bruta – P1 v1 (cenários de integração, prompt genérico)

> Resposta da LLM copiada **sem edição**. Prompt na seção "P1 v1" de [`../prompts.md`](../prompts.md). Execução isolada, sem acesso ao repositório.

# Testes de integração para uma API Flask de geração de senhas

Não tenho o código da sua API, então parti de um contrato comum. Ajuste as constantes e os nomes de campo ao que a sua API realmente faz.

## Contrato assumido

| Item | Valor assumido |
|---|---|
| Endpoint | `POST /api/generate` |
| Corpo (JSON) | `length` (int), `uppercase`, `lowercase`, `digits`, `symbols` (bool), `count` (int, opcional) |
| Padrões | `length=16`, todas as classes ativas, `count=1` |
| Limites | `8 <= length <= 128`, `1 <= count <= 50` |
| Sucesso | `200` com `{"password": "..."}`, ou `{"passwords": [...]}` quando `count > 1` |
| Erro de validação | `400` com `{"error": "<mensagem>"}` |
| Outros | `GET /health` responde `200` |

---

## Estrutura

```
tests/
├── conftest.py
└── integration/
    └── test_password_api.py
```

## `tests/conftest.py`

```python
import pytest

# Se você usa application factory:
from app import create_app
# Se não usa, troque por:  from app import app as flask_app


@pytest.fixture(scope="session")
def app():
    app = create_app({"TESTING": True})
    # app = flask_app; app.config.update(TESTING=True)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()
```

## `tests/integration/test_password_api.py`

```python
import string
import threading

import pytest

ENDPOINT = "/api/generate"
MIN_LEN, MAX_LEN, DEFAULT_LEN = 8, 128, 16
MAX_COUNT = 50

UPPER = set(string.ascii_uppercase)
LOWER = set(string.ascii_lowercase)
DIGITS = set(string.digits)
SYMBOLS = set(string.punctuation)  # ajuste ao conjunto de símbolos da sua API


def gerar(client, **payload):
    return client.post(ENDPOINT, json=payload)


def senha_de(resp):
    assert resp.status_code == 200, resp.get_data(as_text=True)
    return resp.get_json()["password"]


# ---------------------------------------------------------------------------
# 1. Caminho feliz
# ---------------------------------------------------------------------------
class TestCaminhoFeliz:
    def test_gera_senha_com_valores_padrao(self, client):
        resp = client.post(ENDPOINT, json={})
        senha = senha_de(resp)
        assert isinstance(senha, str)
        assert len(senha) == DEFAULT_LEN

    def test_resposta_e_json(self, client):
        resp = gerar(client, length=12)
        assert resp.status_code == 200
        assert resp.is_json
        assert resp.content_type.startswith("application/json")

    @pytest.mark.parametrize("length", [MIN_LEN, 12, 32, 64, MAX_LEN])
    def test_respeita_tamanho_solicitado(self, client, length):
        assert len(senha_de(gerar(client, length=length))) == length

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 2. Classes de caracteres
# ---------------------------------------------------------------------------
class TestClassesDeCaracteres:
    @pytest.mark.parametrize(
        "flags, permitidos",
        [
            ({"uppercase": True, "lowercase": False, "digits": False, "symbols": False}, UPPER),
            ({"uppercase": False, "lowercase": True, "digits": False, "symbols": False}, LOWER),
            ({"uppercase": False, "lowercase": False, "digits": True, "symbols": False}, DIGITS),
            ({"uppercase": False, "lowercase": False, "digits": False, "symbols": True}, SYMBOLS),
            ({"uppercase": True, "lowercase": True, "digits": False, "symbols": False}, UPPER | LOWER),
        ],
    )
    def test_usa_apenas_classes_habilitadas(self, client, flags, permitidos):
        # Repete a chamada para reduzir a chance de um falso positivo por sorte
        for _ in range(20):
            senha = senha_de(gerar(client, length=32, **flags))
            assert set(senha) <= permitidos, f"caractere inesperado em {senha!r}"

    def test_contem_ao_menos_um_de_cada_classe_habilitada(self, client):
        """Só vale se a API garante pelo menos um caractere de cada classe."""
        for _ in range(50):
            senha = senha_de(gerar(client, length=MIN_LEN, uppercase=True,
                                   lowercase=True, digits=True, symbols=True))
            s = set(senha)
            assert s & UPPER and s & LOWER and s & DIGITS and s & SYMBOLS, senha

    def test_sem_espacos_ou_caracteres_de_controle(self, client):
        senha = senha_de(gerar(client, length=MAX_LEN))
        assert all(c.isprintable() and not c.isspace() for c in senha)

    def test_todas_as_classes_desabilitadas_retorna_400(self, client):
        resp = gerar(client, length=16, uppercase=False, lowercase=False,
                     digits=False, symbols=False)
        assert resp.status_code == 400
        assert "error" in resp.get_json()


# ---------------------------------------------------------------------------
# 3. Validação de entrada
# ---------------------------------------------------------------------------
class TestValidacao:
    @pytest.mark.parametrize("length", [MIN_LEN - 1, 0, -1, MAX_LEN + 1, 10**9])
    def test_tamanho_fora_dos_limites(self, client, length):
        resp = gerar(client, length=length)
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    @pytest.mark.parametrize("length", ["16", 16.5, None, [16], {"v": 16}, True])
    def test_tamanho_com_tipo_invalido(self, client, length):
        # Atenção: True passa por isinstance(x, int) em Python; a API deve rejeitar
        resp = gerar(client, length=length)
        assert resp.status_code == 400

    @pytest.mark.parametrize("campo", ["uppercase", "lowercase", "digits", "symbols"])
    @pytest.mark.parametrize("valor", ["true", 1, "sim", None])
    def test_flag_com_tipo_invalido(self, client, campo, valor):
        resp = gerar(client, length=16, **{campo: valor})
        assert resp.status_code == 400

    def test_json_malformado(self, client):
        resp = client.post(ENDPOINT, data="{length: 16", content_type="application/json")
        assert resp.status_code == 400

    def test_content_type_incorreto(self, client):
        resp = client.post(ENDPOINT, data="length=16",
                           content_type="application/x-www-form-urlencoded")
        assert resp.status_code in (400, 415)

    def test_corpo_nao_e_objeto(self, client):
        resp = client.post(ENDPOINT, json=[1, 2, 3])
        assert resp.status_code == 400

    def test_campos_desconhecidos(self, client):
        resp = gerar(client, length=16, foo="bar")
        # Defina a política e mantenha só uma das asserções:
        assert resp.status_code in (200, 400)

    def test_erro_nao_vaza_stacktrace(self, client):
        resp = gerar(client, length="abc")
        corpo = resp.get_data(as_text=True)
        assert "Traceback" not in corpo
        assert "File \"" not in corpo


# ---------------------------------------------------------------------------
# 4. Geração em lote (se a API suportar o parâmetro `count`)
# ---------------------------------------------------------------------------
class TestLote:
    def test_gera_quantidade_solicitada(self, client):
        resp = gerar(client, length=16, count=10)
        assert resp.status_code == 200
        senhas = resp.get_json()["passwords"]
        assert len(senhas) == 10
        assert all(len(s) == 16 for s in senhas)

    def test_senhas_do_lote_sao_distintas(self, client):
        senhas = gerar(client, length=20, count=MAX_COUNT).get_json()["passwords"]
        assert len(set(senhas)) == len(senhas)

    @pytest.mark.parametrize("count", [0, -1, MAX_COUNT + 1, "5"])
    def test_count_invalido(self, client, count):
        assert gerar(client, length=16, count=count).status_code == 400


# ---------------------------------------------------------------------------
# 5. Aleatoriedade (verificações básicas, não substituem análise estatística)
# ---------------------------------------------------------------------------
class TestAleatoriedade:
    def test_chamadas_consecutivas_geram_senhas_diferentes(self, client):
        senhas = {senha_de(gerar(client, length=16)) for _ in range(200)}
        assert len(senhas) == 200

    def test_distribuicao_nao_e_degenerada(self, client):
        texto = "".join(
            senha_de(gerar(client, length=64, uppercase=False, lowercase=False,
                           digits=True, symbols=False))
            for _ in range(100)
        )
        # 6400 dígitos: cada um deve aparecer ~640 vezes; tolerância ampla
        for d in string.digits:
            assert 400 < texto.count(d) < 900, f"dígito {d} com frequência anômala"


# ---------------------------------------------------------------------------
# 6. HTTP e roteamento
# ---------------------------------------------------------------------------
class TestHTTP:
    @pytest.mark.parametrize("metodo", ["get", "put", "delete", "patch"])
    def test_metodo_nao_permitido(self, client, metodo):
        resp = getattr(client, metodo)(ENDPOINT)
        assert resp.status_code == 405

    def test_rota_inexistente(self, client):
        assert client.post("/api/inexistente", json={}).status_code == 404

    def test_resposta_nao_e_cacheada(self, client):
        resp = gerar(client, length=16)
        cache = resp.headers.get("Cache-Control", "")
        assert "no-store" in cache

    def test_cabecalhos_de_seguranca(self, client):
        resp = gerar(client, length=16)
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"


# ---------------------------------------------------------------------------
# 7. Segurança e observabilidade
# ---------------------------------------------------------------------------
class TestSeguranca:
    def test_senha_nao_aparece_nos_logs(self, client, caplog):
        caplog.set_level("DEBUG")
        senha = senha_de(gerar(client, length=32))
        assert senha not in caplog.text

    def test_payload_muito_grande_e_rejeitado(self, client, app):
        app.config["MAX_CONTENT_LENGTH"] = 1024
        resp = client.post(ENDPOINT, data="x" * 10_000, content_type="application/json")
        assert resp.status_code in (400, 413)


# ---------------------------------------------------------------------------
# 8. Concorrência
# ---------------------------------------------------------------------------
def test_requisicoes_concorrentes(app):
    resultados, erros = [], []

    def worker():
        try:
            c = app.test_client()  # um client por thread
            r = c.post(ENDPOINT, json={"length": 24})
            resultados.append((r.status_code, r.get_json()["password"]))
        except Exception as exc:  # noqa: BLE001
            erros.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not erros
    assert all(status == 200 for status, _ in resultados)
    senhas = [s for _, s in resultados]
    assert len(set(senhas)) == len(senhas)
```

---

## Resumo dos casos

| # | Categoria | O que é verificado | Resultado esperado |
|---|---|---|---|
| 1 | Caminho feliz | Valores padrão, tamanhos válidos (mínimo, típico, máximo), `/health` | 200, tamanho correto |
| 2 | Classes de caracteres | Só usa as classes habilitadas, inclui pelo menos uma de cada, nenhum caractere invisível | 200; 400 se todas as classes estiverem desligadas |
| 3 | Validação | Limites, tipos errados (inclusive `True` como int), JSON malformado, Content-Type errado, campos extras | 400 ou 415, sem stack trace |
| 4 | Lote | Valor de `count`, senhas distintas no lote, `count` inválido | 200 ou 400 |
| 5 | Aleatoriedade | Unicidade entre chamadas, distribuição aproximadamente uniforme | Sem repetições, sem viés grosseiro |
| 6 | HTTP | 405, 404, `Cache-Control: no-store`, `nosniff` | Status e cabeçalhos corretos |
| 7 | Segurança | A senha não aparece nos logs, payload grande demais | Sem vazamento; 400 ou 413 |
| 8 | Concorrência | 50 requisições paralelas | Todas 200, todas distintas |

## Como rodar

```bash
pip install pytest pytest-cov
pytest tests/integration -v --cov=app --cov-report=term-missing
```

## Observações

- **Pontos para adaptar:** se a API usa `GET` com query string, troque o helper `gerar` por `client.get(ENDPOINT, query_string=payload)`. Ajuste também os nomes dos campos e as constantes de limite.
- **Regras que dependem da sua especificação:** o teste "ao menos um de cada classe" e o comportamento para campos desconhecidos só valem se você definir essas regras. Remova ou adapte esses testes conforme a sua especificação.
- **Testes de aleatoriedade:** eles só pegam falhas grosseiras, como uma seed fixa ou o uso de `random` em vez de `secrets`. Complemente com um teste unitário que confirme o uso de `secrets.choice` ou `SystemRandom`.
- **Testes mais lentos:** marque os de aleatoriedade e concorrência com `@pytest.mark.slow` se quiser rodá-los separados no CI.
