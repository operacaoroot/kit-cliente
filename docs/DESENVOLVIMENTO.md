# O cliente desenvolve as próprias ferramentas

A última etapa do kit é o cliente criar ferramentas (skills) para as tarefas dele. É a mesma regra
que a Root adotou para si em 2026-09-29: nada entra em uso sem passar por homologação.

## As três estações

| Estação | Onde | Quem move | O Claude usa sozinho? |
|---|---|---|---|
| Oficina | `oficina/<nome>/SKILL.md` + `TESTES.md` | `skills.py nova` | não; só quando a pessoa pede para testar |
| Teste | caso real, resultado em `entregas/`, registro em `TESTES.md` | a pessoa aprova | só no teste |
| Em uso | `.claude/skills/<nome>/` | `skills.py promover` | sim |

`ferramentas/skills.py` (no kit) faz as mudanças; a skill `criar-skill` conduz a conversa. O
catálogo `catalogo.json` guarda cada ferramenta com `origem` (`root`, `frente`, `cliente`),
`estado` (`homologacao`, `ativa`, `aposentada`) e `versao`.

## O que a conferência barra antes de promover

- cabeçalho sem `name` igual à pasta, ou `description` curta ou ainda com texto de exemplo;
- comentário do modelo sem preencher, ou corpo curto demais;
- senha, token, chave de API, CPF ou CNPJ escritos;
- caminho da pasta do usuário (`/Users/...`, `C:\Users\...`): ferramenta tem de rodar em qualquer máquina;
- nenhum teste, ou o último teste reprovado.

## Regras

- Ferramenta da Root (`root` e `frente`) não se edita: `atualizar.py` sobrescreve. O cliente cria
  a dele com `--a-partir-de`.
- Nada é apagado: versão substituída e ferramenta aposentada vão para `oficina/_aposentadas/`.
- Melhorar uma ferramenta do cliente sobe a versão (1.0.0, 1.1.0...), com novo teste.
- Tarefa que pede sistema de terceiro ou programa fora do catálogo vira pedido de ajuda: a Root
  avalia antes.

## O que a Root vê

O catálogo e o texto das ferramentas chegam quando o cliente fecha o dia. O acompanhador
(`acompanhador/acompanhar.py`) mostra quantas estão em uso e em teste e avisa quando nasce uma
nova ou quando uma muda de estado. É assim que a Root aprende com a forma de trabalho do cliente e
acha ferramentas que valem virar receita do cardápio.
