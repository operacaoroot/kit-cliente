# Painel do kit

A página que o cliente vê enquanto o kit se instala e logo depois. Nasceu em 2026-11-24 de duas
queixas da instalação dos clientes: a pessoa não sabia o que estava acontecendo no computador dela
e, quando a instalação terminava, não tinha o que fazer em seguida.

## O que a página mostra

- **Etapas da instalação**, com a situação de cada uma (a fazer, em andamento, feito, com
  pendência, não deu certo): ferramentas básicas, programas do kit, Python do kit, Claude liberado,
  kit ligado à Root pela chave, atalhos na Mesa e conferência final.
- **O que está acontecendo no seu computador**: cada linha que o instalador escreve (conferindo,
  baixando, instalando, instalado, falhou), com a hora, o mais recente em cima.
- **O que já foi feito** e **o que falta**: durante a instalação, pelas etapas; no fim, pela
  conferência (`painel.py concluir`), em frases para a pessoa, sem saída de comando.
- **Próximos passos**, cada um com o porquê, o texto pronto para o Claude e os botões *Abrir no
  Claude* (`claude://code/new?folder=<kit>&q=<texto>`) e *Copiar texto*: abrir o Claude na pasta
  do kit, configurar o perfil, abrir o cofre no Obsidian, primeira carga do Obsidian, descobrir
  quais conectores a pessoa precisa, ligar os conectores um por vez, fechar o dia e pedir ajuda.

## Como funciona

| Peça | Papel |
|---|---|
| `modelo/ferramentas/painel.py` | grava o estado em `_privado/painel/estado.json` e o mesmo conteúdo em `estado.js` (`window.KIT_PAINEL = {...}`). Comandos: `iniciar`, `etapa <id> <estado> [texto]`, `evento <texto> [--tipo ok\|aviso\|info]`, `concluir [--sem-rede]`, `abrir`, `caminho`. |
| `modelo/painel/index.html`, `painel.js`, `painel.css` | página estática. Abre **direto do disco** (`file://`), sem servidor e sem porta: lê o `estado.js` por `<script>` a cada 2 s durante a instalação e a cada 15 s depois. |
| `modelo/painel/primeiros-passos.js` | os próximos passos e os textos para o Claude. Texto para o cliente: sem travessão, na voz da Root. `{pasta}` e `{vault}` viram os caminhos deste computador. |
| `modelo/ferramentas/ambiente.py` | `passo`, `ok`, `aviso` e `contar` repetem cada linha no painel, se o instalador abriu um. Sem painel aberto (o Claude rodando a conferência semanas depois), nada é criado. |
| instaladores | `instalar.sh` (Mac e Linux) abre o painel logo depois de conferir git e Python; `instalar.ps1` (Windows) instala uv e o Python do kit primeiro e abre o painel em seguida. Cada passo marca a etapa; no fim, `concluir` fecha a conferência e a página aberta mostra o que falta (sem abrir outra aba). Em falha que encerra o instalador depois do painel aberto, ele também chama `concluir`, para a página não ficar parada em "instalando". |
| `modelo/ferramentas/onboarding.py` (Mac, página guiada) | serve o mesmo painel em `/painel/index.html`, marca as etapas ao clicar em *Instalar programas* e mostra a atividade ao vivo na etapa de instalação. |
| atalhos | Mac: `Painel do kit.command` na Mesa. Windows: `Painel do kit.url` na Área de Trabalho. Linux: `painel/index.html` dentro do kit. |

Por que `estado.js` e não `estado.json`: aberto do disco, o navegador não deixa a página ler JSON
com `fetch`, mas deixa carregar um `<script>` da mesma pasta. O texto que vai para o JS troca `</`
por `<\/`, para nenhuma linha fechar a tag do script.

Depois de concluída, a instalação fica congelada no painel: `ambiente.py` rodado de novo (o Claude
conferindo o computador semanas depois) não reescreve a página. Uma instalação nova começa com
`iniciar`. Se o estado parar de mudar por mais de 45 minutos com a fase em "instalando", a página
avisa a pessoa (download grande ou instalador fechado).

O painel é só vitrine: se der erro ao gravar, a instalação segue igual (`painel.py` nunca devolve
erro para o instalador, e o `ambiente.py` ignora a falta dele). O estado fica em `_privado/`, que
nunca vai para o git.

## Testes

`python3 testes/testar_painel.py` monta kits de teste e confere: as peças vão para o kit, o estado
fica fora do git, etapas e eventos, erro de uso sem estrago, escape do `</script>`, as linhas do
`ambiente.py` no painel, a conferência sem rede, a ligação só pela chave (com um `gh` falso que
acusa se for chamado), nenhum texto do kit mandando digitar código, a página guiada do Mac servindo
o painel e a sintaxe do JavaScript (se houver `node`).

Ver o painel sem instalar nada: monte o exemplo, rode no kit gerado `python3 ferramentas/painel.py
iniciar`, algumas `etapa` e `evento`, `concluir --sem-rede` e abra `painel/index.html`.
