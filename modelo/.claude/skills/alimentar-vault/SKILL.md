---
name: alimentar-vault
description: Transforma o que aconteceu no kit (conversas com o Claude, entregas, commits, pedidos de ajuda, arquivos novos em entrada/) em diário e notas do vault, com fonte e marcadas para revisão. Roda sozinha três vezes por dia pela rotina do kit; use também quando a pessoa pedir "alimenta o vault", "atualiza a minha base", "o que eu fiz hoje vai para o Obsidian", "liga a rotina do vault", "muda o horário da rotina" ou "desliga a rotina".
---

# Alimentar o vault

O vault (`vault/`) é a memória do trabalho da pessoa. Esta skill mantém essa memória em dia sem a
pessoa precisar lembrar de anotar. Quem junta o material é `ferramentas/rotina.py` (sem IA); você lê o
resumo e escreve. As regras de cabeçalho e de pastas são as da skill `cuidar-do-vault`: leia-a antes.

## 1. Pegar o material

- **Rodada automática:** o pedido já traz o caminho da coleta em `_privado/rotina/`. Use esse arquivo.
- **Pedido da pessoa:** rode `python3 ferramentas/rotina.py --coletar`. Se imprimir `nada novo`, diga
  que o vault já está em dia e pare.

Leia a coleta inteira. Depois leia o que o vault já tem sobre os assuntos que aparecem nela (Grep por
nome de projeto, cliente, pessoa ou tema) antes de escrever qualquer coisa.

## 2. Escrever o diário

Um arquivo por dia: `vault/_diario/AAAA-MM-DD.md` (a data da coleta). Se já existir, acrescente uma
seção com o horário da rodada; nunca reescreva o que já está lá.

```markdown
---
kind: nota
dono: <nome da pessoa, do perfil.md>
valido_de: AAAA-MM-DD
fonte: rotina do vault
revisar: não
origem: rotina
---

# Diário · AAAA-MM-DD

## Rodada das HH:MM

### O que foi feito
- <frase curta> (fonte: conversa `id` de DD/MM HH:MM | commit `hash` | `entregas/arquivo`)

### Decisões
- <o que foi decidido e por quem> (fonte)

### Pendências
- <o que ficou para depois, com quem e até quando, se foi dito> (fonte)

### O que a IA errou e como foi corrigido
- <o erro e a correção que a pessoa pediu> (fonte)
```

Seção sem conteúdo fica fora. Até 12 linhas por seção; o que passar disso é resumo demais.

## 3. Atualizar as notas que duram

Só o que tem valor além do dia vira nota permanente, na pasta certa:

| Aparece na coleta | Vai para |
|---|---|
| decisão com consequência | `60-Decisoes/AAAA-MM-DD - assunto.md` |
| projeto novo ou mudança de estado de um projeto | `50-Projetos/<projeto>.md` (estado, próximo passo) |
| pessoa ou empresa com quem ela trabalha | `30-Organizacao/` (papel e relação, nunca contato) |
| jeito de fazer uma tarefa que se repete | `40-Operacao/` |
| número de referência com origem | `70-Dados/` |
| objetivo com prazo | `90-Metas/` |
| palavra ou sigla da casa | `10-Identidade/` (vocabulário) |

Para cada nota nova ou alterada:

1. Procure antes; se a nota existe, **acrescente** ou ajuste a parte que mudou, sem reescrever o resto.
2. Cabeçalho com `fonte:` apontando a coleta (`rotina AAAA-MM-DD HH:MM · conversa <id>`), `origem: rotina`
   e `revisar: sim`. Uma nota que a pessoa já revisou e que você alterou volta para `revisar: sim`.
3. No fim da nota, acrescente em `## Histórico`: `- AAAA-MM-DD HH:MM: <o que a rotina mudou>`.
4. Ligue com `[[...]]` as notas relacionadas e acrescente a nova ao `Índice.md` da pasta.

No máximo **8 notas permanentes por rodada**. O que sobrar vai para o diário, em `### Para a próxima`.

## 4. Regras que não mudam

- **Nada sem fonte.** Toda linha aponta de onde veio. O que a pessoa disse vale mais do que o que o
  Claude respondeu; uma sugestão do Claude que ela não aceitou não é decisão.
- **Segredo nunca.** A coleta já vem mascarada; se algo escapou (senha, token, chave, cartão, conta,
  CPF, CNPJ), não copie e registre no diário "havia um segredo na conversa de DD/MM; não foi copiado".
- **Dado de terceiro fica fora:** telefone, e-mail, documento, valor de contrato, preço negociado,
  dado financeiro de cliente dela. Descreva o padrão ("proposta para uma rede de varejo"), sem número.
- **Vida pessoal fica fora:** saúde, família, finanças pessoais, relacionamentos.
- **`entrada/` não se copia:** descreva o que o arquivo é e para que serve; trechos só se forem curtos
  e necessários, e nunca de documento de cliente.
- **Não apague nota, não mova nota, não edite skill, `perfil.md`, `CLAUDE.md` nem nada fora de `vault/`.**
- **Não faça commit nem push.** O envio é da rotina (ou do "fechar o dia").

## 5. Fechar a rodada

Rode `python3 ferramentas/rotina.py --concluir <nome do arquivo da coleta>` e responda em até 3 linhas:
quantas notas criou, quantas alterou e quantas esperam revisão.

## Ligar, mudar horário, desligar (a pedido da pessoa)

- Ver como está: `python3 ferramentas/rotina.py --estado`
- Ligar (padrão três vezes ao dia, 08:00, 12:30 e 17:30): `python3 ferramentas/rotina.py --ligar`
- Outros horários: `python3 ferramentas/rotina.py --ligar --horas 07:30,12:00,18:30`
- Sem envio automático para a Root: acrescente `--sem-envio`
- Desligar: `python3 ferramentas/rotina.py --desligar`

Antes de ligar, explique em duas frases o que a rotina lê (só as conversas feitas dentro da pasta do
kit e os arquivos do kit) e o que ela envia (o vault e o progresso, para o repositório do kit), e
peça o OK. A revisão das notas marcadas é pela skill `cuidar-do-vault` ("me ajuda a revisar as notas").
