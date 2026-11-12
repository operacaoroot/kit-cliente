# Sistemas de trabalho e conversa conduzida

Kit Claude para quem trabalha dentro de sistemas da empresa (ERP, plataforma interna) e não domina
a ferramenta. O kit liga o Claude a esses sistemas e conduz tudo pela conversa, na aba Code do
aplicativo Claude. Vale só para `agente: claude`; no kit Codex o servidor da empresa vai no bloco
`mcp` ([Kit em versão Codex](KIT-CODEX.md)).

## O que entra no kit

| Peça | O que faz |
|---|---|
| skill `comecar` | Na primeira mensagem de cada conversa, enquanto houver passo aberto, o Claude conduz: diz onde a pessoa está, faz o passo junto, um clique por mensagem, e confere com `verificar.py`. Vai para todo kit Claude. |
| skill `ligar-sistemas` | Conduz o passo `sistemas`: credencial, plugin, conector, conversa nova e prova. |
| `ferramentas/sistemas.py` | `--conferir`, `--gravar-credencial <id>`, `--instalar-plugins`, `--testar-plugin <plugin>`, `--registrar <conector> ok`. Nunca mostra valor de credencial. |
| `instalar/pedir-segredo.ps1` | Janela do Windows em que a pessoa digita a senha. No Mac é o `osascript`; sem janela, o terminal pergunta sem eco. |
| `.root/sistemas.json` | O bloco `sistemas` do manifesto, sem segredo. |
| `.claude/settings.json` | Leitura dos plugins liberada; toda ferramenta de gravação em `ask`. A regra `ask` pergunta mesmo no modo sem permissão que o `autonomia.py` liga. |
| passo `sistemas` | Entra depois do perfil, só em kit com `sistemas`. Fica feito quando cada plugin está instalado e testado, cada credencial completa e cada conector testado numa conversa. |
| Windows | O instalador termina abrindo `claude://code/new?folder=<kit>&q=<mensagem>` e o atalho "Claude do kit" faz o mesmo. Sem o aplicativo, o atalho abre o Claude Code no terminal, como antes. |

## O bloco no manifesto

```json
"sistemas": {
  "plugins": [{
    "nome": "plugin Exemplo", "marketplace": "exemplo", "repo": "dono/repositorio", "plugin": "exemplo",
    "para_que": "o que o plugin faz pela pessoa",
    "teste": {"script": "mcp/servidor.py", "args": ["--selftest"]},
    "servidores": {"nome-do-servidor": {"leitura": ["listar"], "escrita": ["incluir", "baixar"]}}
  }],
  "conectores": [{
    "id": "erp", "nome": "ERP", "para_que": "...", "link": "https://claude.ai/directory/connectors/...",
    "ferramenta_de_teste": "erp_listar", "leitura": ["erp_listar"], "escrita": ["erp_executar"]
  }],
  "credenciais": [{
    "id": "erp", "nome": "Login do ERP", "para": "...", "arquivo": "~/.empresa/credenciais.env",
    "como_recuperar": "como a pessoa recupera a senha se não lembrar",
    "campos": [
      {"nome": "ERP_EMAIL", "valor": "pessoa@empresa.com"},
      {"nome": "ERP_ANON_KEY", "valor": "...", "publico": true},
      {"nome": "ERP_PASSWORD", "segredo": true, "pergunta": "Senha do ERP"}
    ]
  }],
  "regras": ["frase que entra no CLAUDE.md, na seção dos sistemas"]
}
```

O montador recusa: segredo com valor; campo com cara de segredo (`PASS`, `SENHA`, `SECRET`,
`TOKEN`, `CRYPT`, `PRIVATE`) sem `segredo: true`; chave (`KEY`) com valor sem `publico: true`;
arquivo fora da pasta da pessoa (`~/`); script de teste fora do plugin; link sem `https://`;
ferramenta em leitura e escrita ao mesmo tempo; ferramenta de teste que grava; `sistemas` em kit
Codex. As ferramentas do plugin ganham o nome `mcp__plugin_<plugin>_<servidor>__<ferramenta>`. As
do conector da conta do Claude têm servidor que muda por pessoa, então a escrita delas vai como
`mcp__*__<ferramenta>`, curinga que a regra `ask` aceita.

## A regra de gravação

O `CLAUDE.md` do kit ganha a seção "Sistemas de trabalho", acima dos bons hábitos: gravar em
sistema vale acima da autonomia. Prévia com empresa, valores e datas; "sim" da pessoa para aquela
gravação; uma por vez; leitura de volta; lote começa por um item. O pedido de permissão do Claude
nas ferramentas de gravação é a segunda trava, e a prévia (`dry_run`) do próprio sistema é a terceira.

## Revisão: roteiro, erros explicados e kit de revisão

Para quando o Claude já está instalado e a pessoa "não consegue usar os sistemas".

| Peça | O que faz |
|---|---|
| `ferramentas/revisar_sistemas.py` | Confere Claude Code, uv, cada plugin (instalado, `versao_minima`, pasta inteira), cada credencial (só o nome do campo; acusa linha grudada), roda o teste do plugin e mostra a prova de cada conector. Sai com `[ok]`, `[aviso]` ou `[falta]` e grava `relatorio-revisao.txt`, sem senha, chave nem e-mail. `--explicar "<erro>"` traduz um erro que apareceu no trabalho. `--sem-teste` e `--json` existem. |
| skill `revisar-sistemas` | Conduz a revisão, um ponto por vez, e traz a regra da fila: "pendente de aprovação" não é erro, não se repete a chamada, lote começa por um item. |
| `sistemas.plugins[].versao_minima` | Versão abaixo dela vira `[falta]` com os comandos de atualização. |
| `sistemas.erros` | O dicionário de erros da empresa: `id`, `sinais` (trechos do erro), `significa`, `resolve`, `quem_resolve` (`voce` ou `responsavel`). O que é do responsável sai separado no relatório. Erro de rede e de biblioteca já vêm no script. |
| `montador/revisao.py` | Monta o kit de revisão a partir de `manifestos/revisao-<nome>.json`: uma pasta e um ZIP por pessoa em `saida/revisao-<slug>`, com o roteiro, a skill, o bloco `sistemas` e as regras `ask`. Não tem chave nem repositório. `{email}` no bloco vira o e-mail de cada pessoa. |

```json
{"nome": "empresa", "empresa": "Empresa", "responsavel": "Nome", "canal": "WhatsApp com ...",
 "pessoas": [{"slug": "ana-silva", "nome": "Ana Silva", "primeiro_nome": "Ana", "email": "ana@empresa.com", "sistema": "windows"}],
 "sistemas": {"plugins": [], "conectores": [], "credenciais": [], "regras": [], "erros": []}}
```

A pessoa extrai o ZIP, abre a pasta no Claude e escreve "revisar". O relatório ela mesma manda.
O roteiro não liga gravação em empresa, não aprova pendência e não muda permissão: isso sai no
relatório como decisão do responsável.

## O que ainda não foi provado

- Instalação real no Windows: a janela do `pedir-segredo.ps1`, o atalho `.url` e a abertura do
  aplicativo pelo link. Os testes conferem o texto e o ASCII, sem executar PowerShell.
- A regra `ask` no modo sem permissão e o curinga `mcp__*__` no conector: estão na documentação
  do Claude Code (permissions e permission-modes), mas não rodaram num teste daqui.
- O parâmetro `folder` do link `claude://code/new`: o próprio aplicativo usa (atalho de pasta do
  macOS), mas a documentação pública só cita a versão SSH.
- O roteiro de revisão no Windows: os testes rodam em Mac e Linux com `uv` e `claude` de mentira.
  No kit de revisão o Windows usa `python` do computador ou `uv run --no-project`; sem os dois, a
  skill confere à mão.
