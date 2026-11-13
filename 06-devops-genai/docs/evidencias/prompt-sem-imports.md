<!-- system -->
Você é um engenheiro DevOps sênior que diagnostica falhas de pipelines de CI em projetos Python.

Regras:
- Baseie-se apenas no log e no código fornecidos. Não invente arquivos, funções, variáveis ou linhas.
- Separe o que o log prova do que é hipótese.
- Procure a causa raiz, não só a linha onde a exceção estourou. Se a correção mais simples tratar só o sintoma, diga isso.
- Não proponha relaxar, pular ou apagar testes para o pipeline passar, a menos que o teste esteja comprovadamente errado; nesse caso, justifique.
- Responda em português do Brasil, em Markdown, usando exatamente as seções pedidas.

<!-- user -->
O pipeline de CI falhou na etapa de testes automatizados (pytest).

### Contexto da execução
- Plataforma: execução local
- Python: 3.12.10

### Log do pytest (seção de falhas)
```text
================================== FAILURES ===================================
___________________ test_politica_carrega_valores_numericos ___________________

    def test_politica_carrega_valores_numericos():
        politica = carregar_politica()
>       assert isinstance(politica["tentativas_por_segundo"], float)
E       AssertionError: assert False
E        +  where False = isinstance('1e10', float)

tests\test_tempo_quebra.py:26: AssertionError
_________________ test_politica_respeita_variavel_de_ambiente _________________

monkeypatch = <_pytest.monkeypatch.MonkeyPatch object at 0x00000146D522E450>

    def test_politica_respeita_variavel_de_ambiente(monkeypatch):
        monkeypatch.setenv("TENTATIVAS_POR_SEGUNDO", "1000")
>       assert carregar_politica()["tentativas_por_segundo"] == 1000.0
E       AssertionError: assert '1000' == 1000.0

tests\test_tempo_quebra.py:32: AssertionError
_____________________ test_estimativa_usa_politica_padrao _____________________

    def test_estimativa_usa_politica_padrao():
        # 2^40 / 2 / 1e10 = ~55 s
>       assert estimar_tempo_quebra(40) == pytest.approx(54.97558, rel=1e-4)

tests\test_tempo_quebra.py:61: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

entropia_bits = 40, tentativas_por_segundo = '1e10'

    def estimar_tempo_quebra(entropia_bits: float, tentativas_por_segundo: float | None = None) -> float:
        """Tempo medio, em segundos, para achar a senha testando metade do espaco de busca."""
        if entropia_bits < 0:
            raise ValueError("A entropia nao pode ser negativa.")
        if tentativas_por_segundo is None:
            tentativas_por_segundo = carregar_politica()["tentativas_por_segundo"]
        if entropia_bits > ENTROPIA_MAXIMA_CALCULAVEL:
            return math.inf
    
        combinacoes = 2.0 ** entropia_bits
>       return (combinacoes / 2) / tentativas_por_segundo
E       TypeError: unsupported operand type(s) for /: 'float' and 'str'

app\tempo_quebra.py:31: TypeError
_________________ test_senha_de_16_caracteres_atende_politica _________________

    def test_senha_de_16_caracteres_atende_politica():
        # 16 caracteres com os 4 grupos (86 simbolos) -> 102.82 bits no modulo 01
>       resultado = avaliar_senha(102.82)

tests\test_tempo_quebra.py:66: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
app\tempo_quebra.py:55: in avaliar_senha
    segundos = estimar_tempo_quebra(entropia_bits)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

entropia_bits = 102.82, tentativas_por_segundo = '1e10'

    def estimar_tempo_quebra(entropia_bits: float, tentativas_por_segundo: float | None = None) -> float:
        """Tempo medio, em segundos, para achar a senha testando metade do espaco de busca."""
        if entropia_bits < 0:
            raise ValueError("A entropia nao pode ser negativa.")
        if tentativas_por_segundo is None:
            tentativas_por_segundo = carregar_politica()["tentativas_por_segundo"]
        if entropia_bits > ENTROPIA_MAXIMA_CALCULAVEL:
            return math.inf
    
        combinacoes = 2.0 ** entropia_bits
>       return (combinacoes / 2) / tentativas_por_segundo
E       TypeError: unsupported operand type(s) for /: 'float' and 'str'

app\tempo_quebra.py:31: TypeError
____________________ test_senha_fraca_nao_atende_politica _____________________

    def test_senha_fraca_nao_atende_politica():
>       resultado = avaliar_senha(40)

tests\test_tempo_quebra.py:72: 
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
app\tempo_quebra.py:55: in avaliar_senha
    segundos = estimar_tempo_quebra(entropia_bits)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _

entropia_bits = 40, tentativas_por_segundo = '1e10'

    def estimar_tempo_quebra(entropia_bits: float, tentativas_por_segundo: float | None = None) -> float:
        """Tempo medio, em segundos, para achar a senha testando metade do espaco de busca."""
        if entropia_bits < 0:
            raise ValueError("A entropia nao pode ser negativa.")
        if tentativas_por_segundo is None:
            tentativas_por_segundo = carregar_politica()["tentativas_por_segundo"]
        if entropia_bits > ENTROPIA_MAXIMA_CALCULAVEL:
            return math.inf
    
        combinacoes = 2.0 ** entropia_bits
>       return (combinacoes / 2) / tentativas_por_segundo
E       TypeError: unsupported operand type(s) for /: 'float' and 'str'

app\tempo_quebra.py:31: TypeError
- generated xml file: <projeto>\relatorio-testes.xml -
=========================== short test summary info ===========================
FAILED tests/test_tempo_quebra.py::test_politica_carrega_valores_numericos - ...
FAILED tests/test_tempo_quebra.py::test_politica_respeita_variavel_de_ambiente
FAILED tests/test_tempo_quebra.py::test_estimativa_usa_politica_padrao - Type...
FAILED tests/test_tempo_quebra.py::test_senha_de_16_caracteres_atende_politica
FAILED tests/test_tempo_quebra.py::test_senha_fraca_nao_atende_politica - Typ...
======================== 5 failed, 11 passed in 0.85s =========================
```

### Código-fonte
Arquivos citados no traceback.

#### `tests/test_tempo_quebra.py`
```python
   1 | import math
   2 | 
   3 | import pytest
   4 | 
   5 | from app.config import carregar_politica
   6 | from app.tempo_quebra import (
   7 |     SEGUNDOS_POR_ANO,
   8 |     avaliar_senha,
   9 |     estimar_tempo_quebra,
  10 |     formatar_tempo,
  11 | )
  12 | 
  13 | 
  14 | @pytest.fixture(autouse=True)
  15 | def politica_padrao(monkeypatch):
  16 |     """Isola os testes de variaveis de ambiente da maquina ou do runner."""
  17 |     monkeypatch.delenv("TENTATIVAS_POR_SEGUNDO", raising=False)
  18 |     monkeypatch.delenv("TEMPO_MINIMO_ANOS", raising=False)
  19 | 
  20 | 
  21 | # --- Configuracao -----------------------------------------------------------
  22 | 
  23 | 
  24 | def test_politica_carrega_valores_numericos():
  25 |     politica = carregar_politica()
  26 |     assert isinstance(politica["tentativas_por_segundo"], float)
  27 |     assert isinstance(politica["tempo_minimo_anos"], float)
  28 | 
  29 | 
  30 | def test_politica_respeita_variavel_de_ambiente(monkeypatch):
  31 |     monkeypatch.setenv("TENTATIVAS_POR_SEGUNDO", "1000")
  32 |     assert carregar_politica()["tentativas_por_segundo"] == 1000.0
  33 | 
  34 | 
  35 | # --- Estimativa com taxa explicita (nao depende da politica) ----------------
  36 | 
  37 | 
  38 | def test_estimativa_com_taxa_explicita():
  39 |     # 2^10 combinacoes, metade testada em media, 1 tentativa/s -> 512 s
  40 |     assert estimar_tempo_quebra(10, tentativas_por_segundo=1) == 512
  41 | 
  42 | 
  43 | def test_entropia_zero_e_instantanea():
  44 |     assert estimar_tempo_quebra(0, tentativas_por_segundo=1e10) < 1
  45 | 
  46 | 
  47 | def test_entropia_negativa_e_rejeitada():
  48 |     with pytest.raises(ValueError):
  49 |         estimar_tempo_quebra(-1, tentativas_por_segundo=1)
  50 | 
  51 | 
  52 | def test_entropia_acima_do_limite_vira_infinito():
  53 |     assert estimar_tempo_quebra(5000, tentativas_por_segundo=1) == math.inf
  54 | 
  55 | 
  56 | # --- Estimativa usando a politica padrao (1e10 tentativas/s) ----------------
  57 | 
  58 | 
  59 | def test_estimativa_usa_politica_padrao():
  60 |     # 2^40 / 2 / 1e10 = ~55 s
  61 |     assert estimar_tempo_quebra(40) == pytest.approx(54.97558, rel=1e-4)
  62 | 
  63 | 
  64 | def test_senha_de_16_caracteres_atende_politica():
  65 |     # 16 caracteres com os 4 grupos (86 simbolos) -> 102.82 bits no modulo 01
  66 |     resultado = avaliar_senha(102.82)
  67 |     assert resultado["atende_politica"] is True
  68 |     assert resultado["tempo_legivel"] == "mais de mil anos"
  69 | 
  70 | 
  71 | def test_senha_fraca_nao_atende_politica():
  72 |     resultado = avaliar_senha(40)
  73 |     assert resultado["atende_politica"] is False
  74 |     assert resultado["tempo_legivel"] == "55 segundos"
  75 | 
  76 | 
  77 | # --- Formatacao -------------------------------------------------------------
  78 | 
  79 | 
  80 | @pytest.mark.parametrize(
  81 |     ("segundos", "esperado"),
  82 |     [
  83 |         (0.2, "instantaneo"),
  84 |         (30, "30 segundos"),
  85 |         (120, "2 minutos"),
  86 |         (7200, "2 horas"),
  87 |         (3 * 86400, "3 dias"),
  88 |         (5 * SEGUNDOS_POR_ANO, "5 anos"),
  89 |         (5000 * SEGUNDOS_POR_ANO, "mais de mil anos"),
  90 |     ],
  91 | )
  92 | def test_formatar_tempo(segundos, esperado):
  93 |     assert formatar_tempo(segundos) == esperado
```

#### `app/tempo_quebra.py`
```python
   1 | """Estimativa do tempo medio para quebrar uma senha por forca bruta.
   2 | 
   3 | A entropia (em bits) vem do PasswordService.evaluate_strength do modulo 01.
   4 | """
   5 | 
   6 | from __future__ import annotations
   7 | 
   8 | import math
   9 | 
  10 | from app.config import carregar_politica
  11 | 
  12 | SEGUNDOS_POR_MINUTO = 60
  13 | SEGUNDOS_POR_HORA = 60 * SEGUNDOS_POR_MINUTO
  14 | SEGUNDOS_POR_DIA = 24 * SEGUNDOS_POR_HORA
  15 | SEGUNDOS_POR_ANO = 365.25 * SEGUNDOS_POR_DIA
  16 | 
  17 | # Acima disso 2.0 ** bits estoura o float (limite ~1024).
  18 | ENTROPIA_MAXIMA_CALCULAVEL = 1000
  19 | 
  20 | 
  21 | def estimar_tempo_quebra(entropia_bits: float, tentativas_por_segundo: float | None = None) -> float:
  22 |     """Tempo medio, em segundos, para achar a senha testando metade do espaco de busca."""
  23 |     if entropia_bits < 0:
  24 |         raise ValueError("A entropia nao pode ser negativa.")
  25 |     if tentativas_por_segundo is None:
  26 |         tentativas_por_segundo = carregar_politica()["tentativas_por_segundo"]
  27 |     if entropia_bits > ENTROPIA_MAXIMA_CALCULAVEL:
  28 |         return math.inf
  29 | 
  30 |     combinacoes = 2.0 ** entropia_bits
  31 |     return (combinacoes / 2) / tentativas_por_segundo
  32 | 
  33 | 
  34 | def formatar_tempo(segundos: float) -> str:
  35 |     """Converte segundos em texto legivel para a interface."""
  36 |     if segundos < 1:
  37 |         return "instantaneo"
  38 |     if segundos < SEGUNDOS_POR_MINUTO:
  39 |         return f"{segundos:.0f} segundos"
  40 |     if segundos < SEGUNDOS_POR_HORA:
  41 |         return f"{segundos / SEGUNDOS_POR_MINUTO:.0f} minutos"
  42 |     if segundos < SEGUNDOS_POR_DIA:
  43 |         return f"{segundos / SEGUNDOS_POR_HORA:.0f} horas"
  44 |     if segundos < SEGUNDOS_POR_ANO:
  45 |         return f"{segundos / SEGUNDOS_POR_DIA:.0f} dias"
  46 |     anos = segundos / SEGUNDOS_POR_ANO
  47 |     if anos < 1000:
  48 |         return f"{anos:.0f} anos"
  49 |     return "mais de mil anos"
  50 | 
  51 | 
  52 | def avaliar_senha(entropia_bits: float) -> dict:
  53 |     """Resumo usado pela interface: tempo estimado e se atende a politica."""
  54 |     politica = carregar_politica()
  55 |     segundos = estimar_tempo_quebra(entropia_bits)
  56 |     return {
  57 |         "segundos": segundos,
  58 |         "tempo_legivel": formatar_tempo(segundos),
  59 |         "atende_politica": segundos / SEGUNDOS_POR_ANO >= politica["tempo_minimo_anos"],
  60 |     }
```

Responda com estas seções, nesta ordem:

## Resumo
Uma ou duas frases: o que falhou e por quê.

## Evidências no log
Trechos curtos do log (com teste e linha) que sustentam o diagnóstico.

## Causa raiz
Arquivo, linha e explicação. Diga se há diferença entre onde o erro estoura e onde ele nasce.

## Correção sugerida
Um diff unificado mínimo contra os arquivos fornecidos.

## Como validar
Comandos e testes que confirmam a correção.

## Confiança e premissas
Nível de confiança (alta, média ou baixa) e o que você assumiu sem poder verificar.

## Prevenção
No máximo três medidas para evitar a recorrência.

