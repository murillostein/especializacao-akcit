# Plano de Comunicacao do Projeto

**Projeto**: Gerador de Senhas (01-projeto-pratico)
**Data**: 2026-07-19
**Responsavel**: Murillo Stein

---

## Objetivo

Definir como as informacoes relevantes do projeto — incluindo status, riscos identificados, decisoes tecnicas e incidentes — serao comunicadas entre os envolvidos ao longo do ciclo de vida da aplicacao.

---

## Partes interessadas (Stakeholders)

| Parte interessada | Papel | Interesse principal |
|-------------------|-------|---------------------|
| Desenvolvedor | Autor e mantenedor | Qualidade tecnica e seguranca |
| Professor orientador | Avaliador academico | Aderencia aos requisitos do modulo |
| Usuarios finais | Consumidores da aplicacao | Confiabilidade e seguranca das senhas geradas |
| Pares da especializacao | Revisores de codigo | Boas praticas e aprendizado coletivo |

---

## Matriz de comunicacao

| Informacao | Audiencia | Frequencia | Canal | Responsavel |
|------------|-----------|------------|-------|-------------|
| Status de desenvolvimento | Professor, pares | Por entrega de modulo | GitHub (README + commit history) | Desenvolvedor |
| Riscos identificados | Professor | Unica vez (entrega do modulo) | Repositorio GitHub (este documento) | Desenvolvedor |
| Atualizacao de dependencias | Desenvolvedor | Mensal ou por CVE | GitHub Dependabot + e-mail | Automatico |
| Incidente de seguranca | Usuarios, professor | Imediatamente apos deteccao | E-mail direto | Desenvolvedor |
| Decisoes de arquitetura | Pares, professor | Por mudanca relevante | `docs/architecture.md` no repositorio | Desenvolvedor |
| Novas funcionalidades | Usuarios | Por release | GitHub Releases + README | Desenvolvedor |

---

## Protocolos por tipo de comunicacao

### Comunicacao de risco

Quando um novo risco for identificado ou um risco existente mudar de nivel:

1. Atualizar `docs/registro-de-riscos.md` com data e justificativa da mudanca.
2. Se o nivel for **Alto** ou **Critico**, notificar partes interessadas relevantes em ate 24h.
3. Registrar a decisao de resposta em `docs/estrategias-de-resposta.md`.

**Modelo de notificacao de risco**:

```
Assunto: [RISCO] {ID} - {Titulo} - Nivel: {Nivel}

Projeto: Gerador de Senhas
Data: {data}

Risco identificado: {descricao breve}
Nivel: {Critico / Alto / Medio / Baixo}
Impacto potencial: {descricao do impacto}
Acao em andamento: {acao imediata tomada ou planejada}
Proximos passos: {prazo e responsavel}

Em caso de duvidas, responder a este e-mail.
```

---

### Comunicacao de incidente

Em caso de falha de seguranca ou indisponibilidade da aplicacao:

**Etapa 1 - Deteccao e triagem** (ate 30 minutos):
- Identificar natureza e escopo do incidente.
- Classificar: P1 (critico), P2 (alto), P3 (medio).

**Etapa 2 - Notificacao inicial** (ate 1 hora pos-deteccao):
- Notificar partes afetadas com o seguinte modelo:

```
Assunto: [INCIDENTE {P1/P2/P3}] {Titulo breve} - Em investigacao

Descricao: {O que esta acontecendo}
Impacto: {Quem e afetado e como}
Status: Em investigacao
Proximo update: em {X horas}
```

**Etapa 3 - Resolucao e pos-mortem**:
- Comunicar resolucao com causa raiz e acoes preventivas.
- Registrar lio aprendido no repositorio.

```
Assunto: [INCIDENTE RESOLVIDO] {Titulo}

Duracao: {inicio} - {fim}
Causa raiz: {descricao tecnica}
Solucao aplicada: {o que foi feito}
Acoes preventivas: {o que mudara para evitar recorrencia}
```

---

### Comunicacao de status (entrega academica)

Para cada entrega de modulo da especializacao:

```
Assunto: Entrega - Modulo {N}: {Titulo do modulo}

Repositorio: {URL do GitHub}
Cenario utilizado: {projeto proprio - Gerador de Senhas}

Resumo dos principais riscos identificados:
- {risco 1}
- {risco 2}
- {risco 3}

Estrategia de resposta prioritaria:
{descricao da estrategia escolhida e justificativa}

Como a IA Generativa apoiou a atividade:
{descricao objetiva do uso}

Limitacoes observadas no uso da IA:
{lista de limitacoes percebidas}

Artefatos produzidos:
- docs/registro-de-riscos.md
- docs/estrategias-de-resposta.md
- docs/plano-de-comunicacao.md
```

---

## Ferramentas de comunicacao adotadas

| Ferramenta | Uso no projeto |
|------------|----------------|
| GitHub (repositorio) | Documentacao permanente, historico de decisoes, registro de riscos |
| GitHub Issues | Rastreamento de bugs, features e riscos em aberto |
| GitHub Releases | Comunicacao de novas versoes para usuarios |
| GitHub Dependabot | Alertas automaticos de vulnerabilidades em dependencias |
| E-mail | Comunicacao direta em incidentes ou riscos criticos |

---

## Politica de versionamento dos documentos

Todos os artefatos de gestao (este plano, registro de riscos, estrategias de resposta) sao versionados via Git junto ao codigo-fonte. Isso garante:

- Rastreabilidade de quando cada decisao foi tomada.
- Facilidade de revisao em auditorias.
- Visibilidade para avaliadores e pares via GitHub.

Mudancas significativas nos documentos de gestao devem ser acompanhadas de commit com prefixo `docs:` e mensagem descritiva.
