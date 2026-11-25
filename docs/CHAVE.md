# O acesso ao kit: a chave, sempre

**Desde 2026-11-24 o kit fala com a Root só pela chave do kit.** O cliente não precisa de conta
no GitHub, não faz login e não digita código. Os instaladores (Mac, Windows e Linux) e a página
guiada do Mac rodam `ferramentas/conectar.py --usar-chave`; o `--conectar` antigo continua aceito
só para não quebrar instrução velha e faz o mesmo que `--usar-chave`. O GitHub CLI virou opcional
no catálogo.

Por quê: no jeito anterior (abaixo), o `gh auth login --web` mostrava um código de 8 letras para a
pessoa confirmar no navegador. Na instalação dos clientes esse código não aparecia de forma
confiável (a página guiada roda os comandos sem terminal, e no Windows a janela some atrás do
navegador), a instalação travava e o cliente ficava sem saber o que fazer.

## Colaborador (jeito antigo, de 2026-09-29 a 2026-11-24)

O cliente entrava no repositório privado como colaborador, com a conta dele no GitHub: passava o
nome de usuário no kickoff (`cliente.github` no manifesto), `montar.py --github` convidava esse
usuário e o `conectar.py --conectar` fazia o login pelo navegador. O montador e o
`montador/acesso.py` ainda sabem convidar, ver e tirar colaboradores, e o acompanhador ainda mostra
quem está no repositório, mas o kit não usa mais esse caminho para se ligar. Kits antigos ligados
pela conta (remoto `https://`) continuam funcionando; para não depender de login, basta rodar
`--usar-chave` neles.

Ver quem tem acesso, convidar ou trocar usuário (se um dia for preciso de novo):

```bash
python3 montador/acesso.py estado <slug>
python3 montador/acesso.py convidar <slug> --usuario <login>
```

## Encerrar ("o repositório se autodestrói")

```bash
python3 montador/acesso.py encerrar <slug> --motivo "fim do contrato"        # mostra o plano
python3 montador/acesso.py encerrar <slug> --motivo "fim do contrato" --sim  # executa
```

Cancela convites, tira os colaboradores, revoga a chave do kit e arquiva o repositório. O kit
continua funcionando na máquina do cliente com o que já tem, mas para de enviar e de receber.

# A chave do kit

Cada kit sai com uma chave própria, gerada pelo montador. Ela faz três coisas ao mesmo tempo.

## 1. Deixa o cliente enviar e receber sem conta no GitHub

A chave é um par SSH ed25519 (`.root/chave` e `.root/chave.pub`). A parte pública é cadastrada
como **deploy key com escrita** no repositório privado `operacaoroot/kit-<slug>`, e só nele. O
instalador liga a chave ao git local (`core.sshCommand`). Com isso o `fechar-o-dia` faz commit,
pull e push sem o cliente ter conta no GitHub, senha ou token.

A chave privada vai **só dentro do zip**, que segue por canal privado. Ela nunca entra no git (o
`.gitignore` barra e o montador confere antes do primeiro commit). O Claude do kit não é impedido
de ler o arquivo, porque o computador e a conta são do cliente; o CLAUDE.md do kit pede que ele não
mostre a chave na tela.

## 2. Liga o kit à Root

As atualizações do kit (`montador/atualizar.py`), as respostas aos pedidos de ajuda
(`acompanhador/responder.py`) e o acompanhamento chegam por esse repositório. Um kit copiado para
outra pessoa continua apontando para o repositório do dono original: não recebe nada novo, e o que
a outra pessoa fizer aparece no acompanhamento do cliente.

## 3. Identifica o kit

`.root/cliente.json` traz `kit_id`, nome, data de emissão e um **selo** (HMAC-SHA256 com o segredo
da Root em `~/.config/root/kit.env`). O `kit_id` também vai no rodapé do README, do COMECE-AQUI e em
cada skill. O acompanhador confere se o `kit_id` do repositório é o que a Root emitiu.

## Revogar

No fim do contrato: `montador/acesso.py encerrar`. Se só a chave vazar: apagar a deploy key do
repositório (Settings > Deploy keys, ou `DELETE /repos/operacaoroot/kit-<slug>/keys/<id>`). O kit continua
funcionando na máquina do cliente com o que já tem, mas para de enviar e de receber. Para trocar a
chave, gerar uma nova com `ssh-keygen`, cadastrar e mandar ao cliente.

## O que a chave não faz

Texto pode ser copiado. A chave e o selo não impedem ninguém de copiar as skills de um kit; eles
tornam a cópia menos útil (sem atualização, sem acompanhamento, com os dados de outra pessoa
dentro) e rastreável. A proteção de verdade é a parte que fica na Root.
