---
name: ligar-sistemas
description: Liga o Claude do kit aos sistemas de trabalho da pessoa (plugins, conectores do aplicativo e credenciais locais) e prova que cada um funciona, conversando um item por vez. Use no passo "sistemas", e quando a pessoa disser "instala o plugin", "o plugin sumiu", "deu erro de login no sistema", "troquei a minha senha", "o conector não aparece", ou quando uma ferramenta de sistema falhar por acesso.
---

# Ligar os sistemas

O que este kit liga está em `.root/sistemas.json`, escrito pela Root na montagem. Quem faz o
trabalho é `ferramentas/sistemas.py`; você conversa, roda e confere. Um item por vez, no jeito
do `perfil.md`. Se o arquivo não existir, este kit não tem sistemas para ligar.

## O que não muda nunca

- **Senha e token a pessoa digita só na janela que o script abre** ou na tela do próprio sistema.
  Nunca peça no chat, nunca ponha na linha de comando, nunca abra o arquivo da credencial (nem
  para conferir). Se ela colar uma senha no chat, não use, peça para trocar a senha no sistema
  assim que puder e siga pela janela.
- **Para saber o que falta, use `--conferir`.** Ele diz só o nome do campo, nunca o valor.
- **Plugin e conector só aparecem numa conversa nova.** Instalou ou conectou: peça a conversa nova.

## A ordem

1. **Conferir.** `python3 ferramentas/sistemas.py --conferir`. Diga em uma linha o que está pronto
   e qual é o próximo item.
2. **Credenciais** (cada `id` em `credenciais`). Diga para que serve (campo `para`) e avise antes:
   "Vou abrir uma janelinha pedindo a sua senha. Digite lá e clique em Gravar. Eu não vejo o que
   você digita." Então rode `python3 ferramentas/sistemas.py --gravar-credencial <id>`.
   - Não lembra a senha: leia `como_recuperar` e espere ela trocar no sistema.
   - A janela não apareceu em um minuto: peça para olhar a barra de tarefas. Se não houver janela,
     peça que ela abra uma janela de terminal na pasta do kit (PowerShell no Windows) e rode o
     mesmo comando ali: o script pergunta sem mostrar o que se digita.
   - Trocou a senha depois: o mesmo comando com `--trocar`.
3. **Plugins.** `python3 ferramentas/sistemas.py --instalar-plugins` (de 1 a 3 minutos). Depois,
   `python3 ferramentas/sistemas.py --testar-plugin <plugin>`: o teste entra no sistema com a
   credencial gravada e mostra o resultado. Falhou por login: volte ao item 2 com `--trocar`.
4. **Conectores** (cada item em `conectores`). Estes a pessoa liga na conta dela do Claude, no
   aplicativo, e não há script. Guie um clique por mensagem: o nome dela no canto de baixo, à
   esquerda; Configurações (em algumas versões, Personalizar); Conectores; procurar o nome do
   conector; Conectar; entrar com o login do sistema; Autorizar. O `link` do conector abre direto
   a página dele no navegador. Se a conta for de empresa e o conector não aparecer, quem libera é
   o administrador da conta: registre o pedido de ajuda.
5. **Conversa nova.** Peça para abrir uma conversa nova nesta pasta (botão de nova sessão do
   aplicativo, escolhendo a pasta do kit, ou o atalho "Claude do kit" da Área de Trabalho) e
   escrever "continuar".
6. **Provar, na conversa nova.**
   - Plugin: chame uma ferramenta de `leitura` dele e mostre o resultado em uma linha.
   - Conector: chame a `ferramenta_de_teste`. Deu certo: `python3 ferramentas/sistemas.py
     --registrar <id> ok "<resumo curto, sem dado de cliente>"`. A ferramenta não existe na
     conversa: o conector não ficou ligado na conta; volte ao item 4.
7. **Fechar o passo.** `python3 ferramentas/verificar.py --silencioso` e diga que terminou.

## Pedidos de permissão do Claude

Neste kit o Claude pede permissão antes de cada ferramenta que grava em sistema (as de `escrita`
em `sistemas.json`), e isso é de propósito. Explique uma vez, antes do primeiro pedido: "Quando
aparecer o pedido para gravar, leia o que vai ser feito e só então clique em Permitir." Nas
ferramentas de conector do aplicativo, a leitura também pede permissão na primeira vez: para as
de `leitura`, ela pode escolher sempre permitir; para as de `escrita`, permitir só uma vez.
Nunca sugira desligar os pedidos nem o modo sem permissão neste kit.

## Gravar em sistema

Siga a seção "Sistemas de trabalho" do `CLAUDE.md`: prévia primeiro, "sim" dela para aquela
gravação, uma por vez, e leitura de volta para confirmar.

## O que costuma dar errado

| Aparece | O que fazer |
|---|---|
| `uv` ou `claude` não encontrado | O programa entrou, mas o aplicativo ainda não o enxerga. Peça para fechar o Claude por completo e abrir de novo. Se continuar, `preparar-ambiente`. |
| O teste do plugin avisa de uma pasta ou configuração que falta, mas termina em OK | O kit já cobre essa configuração pela credencial. O que vale é o resultado do fim do teste. |
| O teste do plugin diz login inválido | Senha errada ou trocada: item 2 com `--trocar`. Conta sem acesso: pedido de ajuda. |
| O teste do plugin mostra a lista vazia | O login entrou, mas não tem empresa liberada: pedido de ajuda para a Root conferir o acesso. |
| A ferramenta do conector pede para "Vincular" | Clique em Vincular, faça o login do sistema e autorize; depois chame de novo. |
| A ferramenta some numa conversa | Conversa aberta antes de instalar ou conectar: abra uma nova. |
