# Descrição do Sistema - Gerador de Senhas

Documento de entrada da fase de discovery, escrito em linguagem natural antes de qualquer geração de diagrama, para servir de base de comparação com o que a IA Generativa inferiu a partir do código.

## Escopo

O sistema é uma aplicação web de página única cujo único propósito é gerar senhas aleatórias e criptograficamente seguras, com base em opções escolhidas pelo usuário (comprimento e quais grupos de caracteres incluir), e informar o nível de força da senha gerada. Não há cadastro de usuários, autenticação, histórico persistido ou qualquer funcionalidade além da geração pontual de uma senha por requisição.

## Nível de visão escolhido

Optou-se por descrever o sistema em dois níveis inspirados no C4 Model:

- **Nível 1 (Contexto)**: apenas uma pessoa (o usuário) interagindo com o sistema, sem sistemas externos.
- **Nível 2 (Containers)**: o nível de maior valor para este projeto, pois expõe a separação real entre frontend e backend sem o excesso de detalhe de um diagrama de componentes.

Um diagrama de componentes (nível 3, detalhando `routes.py`, `password_service.py`, `domain/models.py`, `config.py`) foi avaliado e descartado por ora: o backend é um único processo Flask pequeno, e a granularidade de componentes traria mais ruído do que valor para quem está conhecendo o sistema pela primeira vez. Fica registrado como possível extensão futura.

## Limites e responsabilidades

| Elemento | Responsabilidade | Não é responsável por |
|---|---|---|
| Frontend (HTML/CSS/JS servidos pelo Flask) | Capturar as opções do formulário, chamar a API, exibir a senha e a força, copiar para a área de transferência | Gerar a senha, validar regras de negócio, persistir qualquer dado |
| Aplicação Flask (rotas) | Expor `GET /` e `POST /api/passwords`, traduzir erros de negócio em respostas HTTP | Lógica de geração/avaliação de senha (delegada ao serviço) |
| Camada de serviço (`PasswordService`) | Validar opções, montar o conjunto de caracteres, gerar a senha com `secrets`, calcular a entropia e classificar a força | Acesso a rede, I/O de request/response HTTP |
| Configuração (`Config`) | Definir limites de comprimento e valores padrão via variáveis de ambiente | Regras de negócio |

## Integrações

Não há integrações externas. O sistema não depende de banco de dados, serviços de terceiros, filas, cache ou provedores de identidade. Essa ausência é intencional e está ligada a um requisito de negócio explícito levantado no módulo de elicitação (`03-elicitacao-de-requisitos`): a senha gerada nunca deve ser armazenada em nenhum lugar.

## Restrições

- Sem persistência de dados (por decisão de produto, não por limitação técnica).
- Sem autenticação/autorização: qualquer pessoa com acesso à URL pode gerar senhas.
- Execução em processo único (`app.run`), sem orquestração de múltiplas instâncias documentada.
- Configuração via variáveis de ambiente (`.env`), sem suporte a múltiplos ambientes simultâneos no mesmo processo.

## Lacunas conhecidas (assumidas, não resolvidas nesta fase)

- Sem rate limiting na API de geração (já registrado como risco R03 em `02-gestao-de-projetos`).
- Sem HTTPS documentado como parte do próprio sistema (assume-se responsabilidade de infraestrutura/deploy, risco R02).
- Sem logging ou observabilidade estruturada — não há como saber, em produção, quantas gerações falham por opções inválidas.
- Sem diagrama de implantação (deployment): não há decisão registrada sobre onde e como o processo Flask roda em produção (servidor WSGI, contêiner, PaaS).
