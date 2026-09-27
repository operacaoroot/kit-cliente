# A chave do kit

Cada kit sai com uma chave própria, gerada pelo montador. Ela faz três coisas ao mesmo tempo.

## 1. Deixa o cliente enviar e receber sem conta no GitHub

A chave é um par SSH ed25519 (`.root/chave` e `.root/chave.pub`). A parte pública é cadastrada
como **deploy key com escrita** no repositório privado `operacaoroot/kit-<slug>`, e só nele. O
instalador liga a chave ao git local (`core.sshCommand`). Com isso o `fechar-o-dia` faz commit,
pull e push sem o cliente ter conta no GitHub, senha ou token.

A chave privada vai **só dentro do zip**, que segue por canal privado. Ela nunca entra no git (o
`.gitignore` barra e o montador confere antes do primeiro commit), e o Claude do kit tem permissão
negada para ler o arquivo.

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

No fim do contrato, ou se a chave vazar: apagar a deploy key do repositório
(Settings > Deploy keys, ou `DELETE /repos/operacaoroot/kit-<slug>/keys/<id>`). O kit continua
funcionando na máquina do cliente com o que já tem, mas para de enviar e de receber. Para trocar a
chave, gerar uma nova com `ssh-keygen`, cadastrar e mandar ao cliente.

## O que a chave não faz

Texto pode ser copiado. A chave e o selo não impedem ninguém de copiar as skills de um kit; eles
tornam a cópia menos útil (sem atualização, sem acompanhamento, com os dados de outra pessoa
dentro) e rastreável. A proteção de verdade é a parte que fica na Root.
