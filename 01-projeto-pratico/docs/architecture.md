# Arquitetura do Projeto

## Visao geral

O sistema foi organizado em camadas simples e objetivas para facilitar manutencao,
testabilidade e evolucao futura.

## Camadas

- `password_generator/config.py`: concentracao das configuracoes da aplicacao e leitura de variaveis de ambiente.
- `password_generator/domain/`: modelos de dominio que representam as regras centrais do negocio.
- `password_generator/services/`: regras de negocio puras, incluindo geracao e avaliacao de senhas.
- `password_generator/routes.py`: exposicao das rotas HTTP e integracao com a camada web.
- `password_generator/templates/` e `password_generator/static/`: experiencia do usuario no frontend.
- `tests/`: testes unitarios e funcionais da API e da regra de negocio.

## Decisoes tecnicas

- `Flask` foi adotado por ser leve, claro para fins didaticos e suficiente para um frontend server-side simples.
- `secrets` foi escolhido para garantir geracao criptograficamente segura.
- A API foi separada da interface para permitir futuras integracoes com SPA, mobile ou CLI.
- A configuracao por `.env` favorece portabilidade entre ambientes local, homologacao e producao.
