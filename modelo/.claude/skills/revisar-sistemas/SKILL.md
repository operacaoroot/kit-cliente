---
name: revisar-sistemas
description: Revisa a ligação do Claude com os sistemas de trabalho (Claude Code, uv, plugin, credencial, teste do plugin, conector), explica em português o que cada erro significa e como se resolve, e escreve um relatório curto para mandar ao responsável. Use quando a pessoa disser "revisar", "revisa o MCP", "o plugin não funciona", "as ferramentas do sistema sumiram", "deu erro ao gravar", "ficou pendente de aprovação", "o que significa esse erro", ou quando uma ferramenta de sistema falhar duas vezes seguidas.
---

# Revisar os sistemas

Quem confere é `ferramentas/revisar_sistemas.py`. Você roda, lê o resultado e conversa. O que
conferir e o que cada erro quer dizer vêm de `.root/sistemas.json`. Nada aqui grava em sistema.

## O que não muda nunca

- **Não abra o arquivo da credencial**, nem para conferir. O script diz só o nome do campo.
- **Senha não entra no chat.** Faltou senha: `python3 ferramentas/sistemas.py --gravar-credencial <id>`
  abre uma janela e a pessoa digita lá.
- **Você não muda permissão, não liga gravação em empresa e não aprova pendência.** O que o
  relatório marca como decisão do responsável vai para ele, do jeito que está.
- **Não invente causa.** Erro fora da lista vai no relatório com o texto que apareceu.

## A ordem

1. **Rodar.** `python3 ferramentas/revisar_sistemas.py`. Se o Python não responder, use
   `uv run --no-project ferramentas/revisar_sistemas.py`. Se nenhum dos dois existir, vá para
   "Sem Python e sem uv", mais abaixo.
2. **Ler com a pessoa.** Cada linha sai com `[ok]`, `[aviso]` ou `[falta]`. Diga em uma frase o
   que está certo e qual é o primeiro `[falta]`. Um ponto por vez.
3. **Resolver o que é dela**, na ordem de "O que você faz" do relatório. Os casos comuns:
   - **uv ausente:** sem ele o servidor do plugin não sobe. Instale pelo comando que o relatório
     mostra, feche o Claude inteiro e abra de novo.
   - **plugin ausente ou desatualizado:** os comandos `/plugin ...` do relatório quem digita é a
     pessoa, na caixa de mensagem. Depois, conversa nova.
   - **credencial incompleta ou com linha grudada:** `--gravar-credencial <id>` (com `--trocar`
     para regravar a senha).
   - **teste do plugin falhou:** o relatório já traz o significado e a solução quando o erro é
     conhecido.
4. **Provar o conector** (linhas `conector ...` em `[aviso]`). Use a ferramenta de teste que a
   linha indica, que só lê. Funcionou: `python3 ferramentas/sistemas.py --registrar <id> ok`.
   Não apareceu: a pessoa liga o conector na conta dela, em Configurações, Conectores, e abre
   uma conversa nova.
5. **Rodar de novo** até não sobrar `[falta]` que seja dela. O que sobrar para o responsável
   fica no relatório.
6. **Entregar.** Diga onde está o `relatorio-revisao.txt` e peça que ela mande ao responsável
   pelo canal combinado. Você não envia.

## Erro no meio do trabalho

Quando uma ferramenta de sistema devolver erro, antes de tentar de novo rode
`python3 ferramentas/revisar_sistemas.py --explicar "<texto do erro>"` e diga à pessoa o que
significa, como se resolve e quem resolve. Erro que não está na lista: copie o texto, sem senha,
para ela mandar ao responsável.

## Pendente de aprovação não é erro

Se o sistema responder que a ação ficou **pendente de aprovação**, nada foi gravado. Então:

- Pare. Não repita a chamada (cada repetição cria outra pendência) e não tente aprovar você mesmo.
- Diga quantas pendências foram criadas, de qual empresa, e onde a pessoa aprova.
- Em lote, faça **um** item, espere a pessoa aprovar e conferir, e só então pergunte se segue
  com os outros, dizendo quantas aprovações o lote vai pedir. Passou de 10, sugira outro caminho
  (importação por planilha no próprio sistema) e deixe a escolha com ela.

## Sem Python e sem uv

Confira à mão e escreva você o `relatorio-revisao.txt`, no mesmo formato (`[ok]`, `[falta]`):

1. `claude --version` e `uv --version`.
2. `claude plugin list` (ou a tela do `/plugin`): cada plugin de `.root/sistemas.json` aparece?
   Em qual versão?
3. O arquivo de cada credencial existe? Só isso: existe ou não existe. Não abra.

O uv ausente é o primeiro conserto, porque sem ele o plugin também não funciona.
