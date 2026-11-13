<!--
Saida bruta da LLM, sem edicao.
Entrada: docs/evidencias/prompt-sem-imports.md (gerado com `--sem-imports`: so os arquivos citados no traceback).
Execucao: Claude Opus 5.5 em sessao isolada (sem historico, sem acesso ao repositorio), via Claude Code.
-->

## Resumo
5 dos 16 testes falharam porque `carregar_politica()` (em `app/config.py`) devolve `tentativas_por_segundo` como **string** (`'1e10'` no padrão, `'1000'` quando vem da variável de ambiente), e não como `float`. Por isso a divisão em `estimar_tempo_quebra` dá `TypeError`. O erro nasce na carga da configuração. A linha 31 de `app/tempo_quebra.py` é só onde ele aparece.

## Evidências no log
- `test_politica_carrega_valores_numericos` (`tests\test_tempo_quebra.py:26`):
  `E +  where False = isinstance('1e10', float)`. Sem variável de ambiente (a fixture `autouse` remove `TENTATIVAS_POR_SEGUNDO`), o valor padrão já chega como `str`.
- `test_politica_respeita_variavel_de_ambiente` (`tests\test_tempo_quebra.py:32`):
  `E AssertionError: assert '1000' == 1000.0`. O valor lido do ambiente também não é convertido.
- `test_estimativa_usa_politica_padrao`, `test_senha_de_16_caracteres_atende_politica` e `test_senha_fraca_nao_atende_politica` (`app\tempo_quebra.py:31`):
  `tentativas_por_segundo = '1e10'` e `E TypeError: unsupported operand type(s) for /: 'float' and 'str'`.
- Os testes que passam a taxa explicitamente (`test_estimativa_com_taxa_explicita`, `test_entropia_zero_e_instantanea` etc.) não aparecem entre as falhas (`5 failed, 11 passed`). Isso confirma que a fórmula está correta e que o problema está só no valor vindo da política.

## Causa raiz
- **Onde estoura:** `app/tempo_quebra.py`, linha 31: `return (combinacoes / 2) / tentativas_por_segundo`, quando `tentativas_por_segundo` vem da linha 26 (`carregar_politica()["tentativas_por_segundo"]`).
- **Onde nasce:** em `carregar_politica()`, no arquivo `app/config.py`. O log prova que essa função devolve `str` tanto no caminho padrão (`'1e10'`) quanto no caminho da variável de ambiente (`'1000'`). Variáveis de ambiente são sempre strings, e o valor padrão aparentemente também está definido como string. Falta a conversão para `float`.
- **Limitação:** o conteúdo de `app/config.py` **não foi fornecido**, então não consigo apontar a linha exata. Hipótese provável, não verificada: algo como `os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10")` sem `float(...)`.
- **Hipótese adicional:** `tempo_minimo_anos` provavelmente tem o mesmo defeito. O teste da linha 27 nem chegou a rodar, porque a asserção da linha 26 falhou antes. Se for o caso, `avaliar_senha` (linha 59, `segundos / SEGUNDOS_POR_ANO >= politica["tempo_minimo_anos"]`) também quebraria com `TypeError` ao comparar `float` com `str`, mesmo depois de corrigir a divisão.

## Correção sugerida
A correção certa fica em `app/config.py`: converter os valores para `float` dentro de `carregar_politica()`, nos dois caminhos (padrão e variável de ambiente), para `tentativas_por_segundo` e `tempo_minimo_anos`. Como o arquivo não foi fornecido, segue um **esboço**. As linhas de contexto são supostas e precisam ser ajustadas ao código real:

```diff
--- a/app/config.py
+++ b/app/config.py
@@ def carregar_politica():
-    tentativas = os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10")
-    tempo_minimo = os.getenv("TEMPO_MINIMO_ANOS", <padrao>)
+    tentativas = float(os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10"))
+    tempo_minimo = float(os.getenv("TEMPO_MINIMO_ANOS", <padrao>))
     return {
         "tentativas_por_segundo": tentativas,
         "tempo_minimo_anos": tempo_minimo,
     }
```

Também vale validar o valor convertido (por exemplo, `tentativas > 0`) e gerar um `ValueError` com mensagem clara quando a variável não for numérica.

**Não recomendado como correção principal:** o único diff possível contra os arquivos fornecidos seria um `float(...)` em `app/tempo_quebra.py`:

```diff
--- a/app/tempo_quebra.py
+++ b/app/tempo_quebra.py
@@ -23,7 +23,7 @@ def estimar_tempo_quebra(entropia_bits: float, tentativas_por_segundo: float | None = None) -> float:
     if entropia_bits < 0:
         raise ValueError("A entropia nao pode ser negativa.")
     if tentativas_por_segundo is None:
-        tentativas_por_segundo = carregar_politica()["tentativas_por_segundo"]
+        tentativas_por_segundo = float(carregar_politica()["tentativas_por_segundo"])
     if entropia_bits > ENTROPIA_MAXIMA_CALCULAVEL:
         return math.inf
```

Esse diff só trata o **sintoma**. Os dois testes de configuração (`test_politica_carrega_valores_numericos` e `test_politica_respeita_variavel_de_ambiente`) continuariam falhando, já que eles testam o contrato de `carregar_politica()`. E se `tempo_minimo_anos` também vier como string, `avaliar_senha` ainda quebraria na linha 59. Os testes estão corretos: eles exigem um contrato razoável (valores numéricos) e não devem ser relaxados.

## Como validar
```bash
pytest tests/test_tempo_quebra.py -v
pytest tests/test_tempo_quebra.py::test_politica_carrega_valores_numericos tests/test_tempo_quebra.py::test_politica_respeita_variavel_de_ambiente -v
pytest tests/test_tempo_quebra.py -k "politica_padrao or atende_politica" -v
pytest   # suíte completa, esperado: 16 passed
```
- Confirme que `test_politica_carrega_valores_numericos` passa nas **duas** asserções (linhas 26 e 27). Isso cobre `tempo_minimo_anos`.
- Teste manual: `TENTATIVAS_POR_SEGUNDO=abc` deve gerar um erro claro, e não um `TypeError` lá na frente.

## Confiança e premissas
**Confiança: alta** para o diagnóstico de que `carregar_politica()` devolve `str`, porque o log mostra isso diretamente em dois testes. **Média** para a forma exata da correção, porque `app/config.py` não foi fornecido.

Premissas não verificadas:
- `carregar_politica()` lê os valores com `os.getenv`/`os.environ` e usa um padrão em string. Não há outro carregador, como `.env` ou YAML, que também devolva strings.
- `tempo_minimo_anos` sofre do mesmo problema (não comprovado pelo log).
- A execução foi local (Python 3.12.10). Não há indício de que o ambiente do runner mude o resultado, pois a fixture `autouse` isola as variáveis.

## Prevenção
1. Centralizar a leitura de configuração com tipagem e validação, por exemplo uma função `_ler_float(nome, padrao)` ou `pydantic-settings`, que falhe cedo e com mensagem clara quando o valor não for numérico.
2. Rodar um verificador de tipos (`mypy`/`pyright`) no CI, com retorno tipado em `carregar_politica()` (`TypedDict` com campos `float`), para pegar `str` onde se espera `float`.
3. Manter e ampliar os testes de contrato da configuração, por exemplo valores inválidos no ambiente e os dois campos numéricos, como etapa rápida antes dos testes de domínio.
