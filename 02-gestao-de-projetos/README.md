# Gestao de Projetos - Modulo de Riscos e Comunicacao

## Contexto

Este modulo aplica conceitos de gestao de riscos e comunicacao de projetos ao **Gerador de Senhas** desenvolvido no modulo anterior (`01-projeto-pratico`). A Inteligencia Artificial Generativa foi utilizada como ferramenta de apoio na identificacao, analise e planejamento de respostas aos riscos.

## Cenario utilizado

**Projeto real academico**: Aplicacao web de geracao de senhas seguras em Python/Flask.

- Repositorio: `01-projeto-pratico/`
- Tecnologias: Python 3.11, Flask, pytest
- Tipo: aplicacao web com backend, API REST e frontend integrado
- Contexto: projeto academico com potencial de uso em ambiente de producao

## Estrutura dos artefatos

```text
02-gestao-de-projetos/
|-- README.md                         (este arquivo)
`-- docs/
    |-- registro-de-riscos.md         (identificacao e analise de riscos)
    |-- estrategias-de-resposta.md    (plano de resposta por risco)
    `-- plano-de-comunicacao.md       (estrutura de comunicacao do projeto)
```

## Resumo dos principais riscos identificados

| ID | Categoria | Risco | Probabilidade | Impacto | Nivel |
|----|-----------|-------|---------------|---------|-------|
| R01 | Seguranca | Exposicao da SECRET_KEY em repositorio | Media | Alto | Alto |
| R02 | Seguranca | Ausencia de HTTPS em ambiente de producao | Alta | Alto | Critico |
| R03 | Seguranca | Sem rate limiting na API de geracao | Media | Medio | Medio |
| R04 | Tecnico | Vulnerabilidades em dependencias desatualizadas | Alta | Alto | Critico |
| R05 | Tecnico | Ausencia de monitoramento e alertas | Alta | Medio | Alto |
| R06 | Projeto | Escopo mal definido para evolucoes futuras | Baixa | Medio | Baixo |
| R07 | Operacional | Ausencia de processo de incidente | Media | Alto | Alto |

## Estrategia de resposta prioritaria

**R04 - Vulnerabilidades em dependencias desatualizadas** foi considerado o risco mais urgente por combinar alta probabilidade com alto impacto e por ser facilmente mitigavel com automacao (GitHub Dependabot + `pip-audit`). Uma dependencia vulneravel pode comprometer a seguranca das senhas geradas, tornando inutil o uso do modulo `secrets`.

## Como a IA Generativa apoiou a atividade

- Geracao do primeiro rascunho da matriz de riscos a partir da descricao da arquitetura
- Sugestao de categorias de risco nao consideradas inicialmente (ex: riscos operacionais)
- Elaboracao de modelos de comunicacao adaptados ao contexto academico
- Validacao da coerencia entre probabilidade, impacto e nivel de risco atribuidos

## Limitacoes e cuidados percebidos no uso da IA

1. **Riscos genericos**: a IA tende a sugerir riscos padrao para qualquer projeto web. Foi necessario filtrar e adaptar ao contexto especifico do projeto.
2. **Niveis de risco sem calibracao**: os valores de probabilidade e impacto precisaram de ajuste manual com base no contexto real.
3. **Ausencia de contexto organizacional**: a IA nao conhece restricoes de equipe, budget ou prazos reais, exigindo complementacao humana.
4. **Alucinacoes pontuais**: em algumas respostas, a IA sugeriu ferramentas que nao se aplicavam ao stack Python/Flask utilizado.
