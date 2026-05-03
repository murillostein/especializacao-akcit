# Gerador de Senhas em Python

Aplicacao web desenvolvida em Python para geracao de senhas seguras com frontend integrado, copia para a area de transferencia, avaliacao de forca por entropia e organizacao orientada a boas praticas de engenharia de software.

O projeto foi inspirado conceitualmente no repositório `lucasdeoliveir/Gerador-Senhas`, mas foi refeito integralmente em Python com backend web, frontend servido pela aplicacao, configuracao por ambiente, testes automatizados e documentacao completa.

## Objetivos do projeto

- Demonstrar separacao de responsabilidades entre interface, rotas, configuracao e dominio.
- Aplicar principios de organizacao de repositorio para um projeto academico apresentavel.
- Utilizar geracao criptograficamente segura de senhas.
- Oferecer uma base simples de evolucao para novos requisitos.

## Funcionalidades

- Geracao de senhas seguras com comprimento configuravel.
- Selecao de letras maiusculas, minusculas, numeros e simbolos.
- Garantia de inclusao dos grupos selecionados na senha final.
- Avaliacao de forca com base em entropia estimada.
- Copia da senha para a area de transferencia no frontend.
- Validacao de entrada com mensagens de erro amigaveis.

## Stack tecnologica

- Python 3.11+
- Flask
- python-dotenv
- pytest

## Estrutura do repositorio

```text
01-projeto-pratico/
|-- app.py
|-- requirements.txt
|-- .env.example
|-- pytest.ini
|-- README.md
|-- docs/
|   `-- architecture.md
|-- password_generator/
|   |-- __init__.py
|   |-- config.py
|   |-- routes.py
|   |-- domain/
|   |   |-- __init__.py
|   |   `-- models.py
|   |-- services/
|   |   |-- __init__.py
|   |   `-- password_service.py
|   |-- static/
|   |   |-- css/
|   |   |   `-- styles.css
|   |   `-- js/
|   |       `-- app.js
|   `-- templates/
|       `-- index.html
`-- tests/
    |-- test_app.py
    `-- test_password_service.py
```

## Como executar

1. Crie e ative um ambiente virtual:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

2. Instale as dependencias:

```powershell
pip install -r requirements.txt
```

3. Crie seu arquivo de ambiente:

```powershell
Copy-Item .env.example .env
```

4. Inicie a aplicacao:

```powershell
python app.py
```

5. Acesse no navegador:

```text
http://127.0.0.1:5000
```

## Variaveis de ambiente

| Variavel | Descricao | Padrao |
|---|---|---|
| `FLASK_APP` | modulo principal da aplicacao | `app.py` |
| `FLASK_ENV` | ambiente de execucao | `development` |
| `SECRET_KEY` | chave da aplicacao Flask | `change-me` |
| `APP_HOST` | host da aplicacao | `127.0.0.1` |
| `APP_PORT` | porta da aplicacao | `5000` |
| `DEFAULT_PASSWORD_LENGTH` | tamanho padrao da senha | `16` |
| `MIN_PASSWORD_LENGTH` | tamanho minimo permitido | `8` |
| `MAX_PASSWORD_LENGTH` | tamanho maximo permitido | `64` |

## Testes

Para executar os testes:

```powershell
pytest
```

Para gerar cobertura:

```powershell
coverage run -m pytest
coverage report
```

## Boas praticas aplicadas

- Separacao entre camada web, servico e dominio.
- Centralizacao das configuracoes em um unico modulo.
- Testes unitarios para regra de negocio e testes funcionais para rotas.
- Uso do modulo `secrets` para geracao segura.
- Frontend desacoplado da logica de negocio.
- Documentacao de arquitetura para apoio academico.

## Evolucoes sugeridas

- Adicionar historico local de senhas geradas no navegador.
- Implementar indicador visual em barra para forca da senha.
- Criar container Docker para padronizar execucao.
- Publicar em nuvem para demonstracao online.

## Referencia utilizada

Repositorio de inspiracao:

- https://github.com/lucasdeoliveir/Gerador-Senhas/tree/main
