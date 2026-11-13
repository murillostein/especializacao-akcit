<!--
Saida bruta da LLM, sem edicao.
Entrada: docs/evidencias/prompt-com-imports.md (padrao do agente: arquivos do traceback + modulos do projeto importados por eles).
Execucao: Claude Opus 5.5 em sessao isolada (sem historico, sem acesso ao repositorio), via Claude Code.
-->

## Resumo
Os 5 testes falharam porque `carregar_politica()` devolve `tentativas_por_segundo` como string (`'1e10'` ou `'1000'`), lida do ambiente sem conversão. O `TypeError` em `estimar_tempo_quebra` é consequência desse valor errado. O problema começa em `app/config.py`.

## Evidências no log
- `test_politica_carrega_valores_numericos` (`tests\test_tempo_quebra.py:26`): `isinstance('1e10', float)` deu `False`. O valor padrão chega como `str`.
- `test_politica_respeita_variavel_de_ambiente` (`tests\test_tempo_quebra.py:32`): `assert '1000' == 1000.0`. O valor da variável de ambiente também chega como `str`, sem conversão.
- `test_estimativa_usa_politica_padrao` (`tests\test_tempo_quebra.py:61`): o traceback mostra `tentativas_por_segundo = '1e10'` e termina em `app\tempo_quebra.py:31` com `TypeError: unsupported operand type(s) for /: 'float' and 'str'`.
- `test_senha_de_16_caracteres_atende_politica` (`:66`) e `test_senha_fraca_nao_atende_politica` (`:72`): o erro é o mesmo, pelo caminho `avaliar_senha` (`app\tempo_quebra.py:55`), depois `estimar_tempo_quebra`, depois a linha 31.
- Os testes que passam `tentativas_por_segundo` explicitamente (`test_estimativa_com_taxa_explicita`, `test_entropia_zero_e_instantanea` etc.) não aparecem entre as falhas. Os 11 que passaram batem com 4 testes de taxa explícita e 7 casos parametrizados de `test_formatar_tempo`. Isso mostra que a conta em si está certa e que o defeito está só no valor que vem da política.

## Causa raiz
- **Onde nasce:** `app/config.py`, linha 14:
  ```python
  "tentativas_por_segundo": os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10"),
  ```
  `os.getenv` sempre devolve `str`, e aqui o valor não passa por `float()`. A linha 15 faz isso corretamente para `tempo_minimo_anos`. O resultado é um dicionário com tipos inconsistentes, que contraria a anotação `tentativas_por_segundo: float | None` de `estimar_tempo_quebra`.
- **Onde estoura:** `app/tempo_quebra.py`, linha 31 (`(combinacoes / 2) / tentativas_por_segundo`), que divide um `float` por uma `str`.
- O erro aparece num lugar e nasce em outro. Converter com `float(...)` na linha 31, ou na linha 26 de `tempo_quebra.py`, trataria só o sintoma: os testes de configuração (`:26` e `:32`) continuariam falhando, e outros usuários de `carregar_politica()` continuariam recebendo string.
- Os testes estão corretos. Eles exigem um contrato razoável e documentado: a política tem valores numéricos e respeita a variável de ambiente. Não há motivo para alterá-los.

## Correção sugerida
```diff
--- a/app/config.py
+++ b/app/config.py
@@ -11,6 +11,6 @@ def carregar_politica() -> dict:
     - TEMPO_MINIMO_ANOS: tempo medio de quebra exigido para a senha ser aceita.
     """
     return {
-        "tentativas_por_segundo": os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10"),
+        "tentativas_por_segundo": float(os.getenv("TENTATIVAS_POR_SEGUNDO", "1e10")),
         "tempo_minimo_anos": float(os.getenv("TEMPO_MINIMO_ANOS", "100")),
     }
```
Com a correção, os valores esperados conferem. Para 40 bits, `2^40 / 2 / 1e10 ≈ 54,9756 s`, o que dá `"55 segundos"` e `atende_politica` igual a `False`. Para 102,82 bits, o tempo passa de mil anos, então `atende_politica` fica `True`.

## Como validar
```bash
# Testes do módulo afetado (esperado: 16 passed)
python -m pytest tests/test_tempo_quebra.py -v

# Só os 5 que falhavam
python -m pytest tests/test_tempo_quebra.py -v -k "politica or padrao or atende"

# Suíte completa, gerando o relatório XML como no pipeline
python -m pytest --junitxml=relatorio-testes.xml
```
Também dá para conferir à mão:
```bash
python -c "from app.config import carregar_politica as c; print(c())"
# esperado: {'tentativas_por_segundo': 10000000000.0, 'tempo_minimo_anos': 100.0}
```

## Confiança e premissas
**Confiança: alta.** O log mostra diretamente o valor `'1e10'` (tipo `str`) e a linha de `config.py` que não faz a conversão.

Premissas que não pude verificar:
- Nenhum outro código do projeto depende de `tentativas_por_segundo` como string. Recebi apenas os três arquivos.
- O comando exato do pipeline não aparece no log. Deduzi o uso de `--junitxml` pela linha `generated xml file: <projeto>\relatorio-testes.xml`.
- Hipótese, não confirmada pelo log: se `TENTATIVAS_POR_SEGUNDO` tiver um valor não numérico no ambiente, o `float()` passa a lançar `ValueError` ao carregar a política. Considero esse comportamento melhor que um erro tardio, mas ele não aparece nesta execução.

## Prevenção
1. Centralizar a leitura de variáveis numéricas num helper, por exemplo `_ler_float(nome, padrao)`, que converta e valide. Assim um campo não fica sem conversão enquanto o outro tem.
2. Rodar um verificador de tipos (mypy ou pyright) no CI, com `carregar_politica()` devolvendo um `TypedDict` ou `dataclass` tipado. A divergência entre `str` e `float` seria pega antes dos testes.
3. Manter testes de contrato da configuração, como `test_politica_carrega_valores_numericos`, para cada nova variável de ambiente adicionada à política.
