# Bot Discord em Python

Projeto base em Python com `discord.py`, estrutura em COGs, sistema de tickets, comandos de `userinfo` e `serverinfo`, sistema de tomate com cooldown e servidor Flask para manter uma rota web ativa na porta `3000`.

## O que ja veio pronto

- Sistema de tickets com painel em embed e botoes.
- Campo `TICKET_PANEL_IMAGE_URL` vazio para voce editar depois.
- Comando `,userinfo` ou `/userinfo`.
- Comando `,serverinfo` ou `/serverinfo`.
- Comando `,tomate` ou `/tomate`.
- Cooldown de 5 minutos no tomate para usuarios comuns.
- Usuarios com permissao de administrador ignoram o cooldown.
- Servidor Flask na porta `3000`.
- Arquivo `render.yaml` para facilitar deploy no Render.

## Estrutura

```text
.
|-- .env.example
|-- .gitignore
|-- README.md
|-- config.py
|-- keep_alive.py
|-- main.py
|-- render.yaml
|-- requirements.txt
`-- cogs
    |-- __init__.py
    |-- server_info.py
    |-- support_tickets.py
    |-- tomato.py
    `-- user_info.py
```

## Como configurar localmente

1. Crie um arquivo `.env` baseado no `.env.example`.
2. Preencha pelo menos:

```env
DISCORD_TOKEN=SEU_TOKEN
PREFIX=,
PORT=3000
TICKET_CATEGORY_ID=
SUPPORT_ROLE_ID=
TICKET_PANEL_IMAGE_URL=
```

3. Instale as dependencias:

```bash
pip install -r requirements.txt
```

4. Rode o bot:

```bash
python main.py
```

## Comandos

- `,ticketpainel` ou `/ticketpainel`: envia o painel de tickets. Recomendado para admins.
- `,userinfo @usuario` ou `/userinfo usuario:@usuario`
- `,serverinfo` ou `/serverinfo`
- `,tomate` ou `/tomate`

## Como subir no GitHub e Render

1. Suba essa pasta inteira para um repositorio no GitHub.
2. No Render, crie um novo `Web Service` conectado ao repo.
3. O `build command` pode ser `pip install -r requirements.txt`.
4. O `start command` pode ser `python main.py`.
5. Adicione a variavel secreta `DISCORD_TOKEN` no painel do Render.
6. Se quiser, adicione tambem `TICKET_CATEGORY_ID`, `SUPPORT_ROLE_ID` e `TICKET_PANEL_IMAGE_URL`.

## Observacoes

- O servidor Flask responde em `/` e usa a porta `3000` por padrao.
- Em plataformas como Render, a variavel `PORT` pode ser sobrescrita automaticamente e o projeto aceita isso.
- Para o comando de tomate funcionar direito, deixe as permissoes de adicionar reacoes ativadas para o bot.
