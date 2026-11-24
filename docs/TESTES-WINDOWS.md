# Testes do kit sem um PC Windows

O workflow `Windows` executa o instalador em uma maquina temporaria Windows Server
2022 do GitHub Actions, uma vez no PowerShell 5.1 e outra no PowerShell 7. Ele roda
nos pull requests. O job tem limite de 15 minutos e permissao somente de leitura
do repositorio. Nao recebe credenciais nem manifestos de clientes.

## O que o teste confere

- Todos os scripts `.ps1` passam pelo interpretador de cada versao do PowerShell.
- O `instalar.ps1` e as partes Claude/Codex reais executam em Windows.
- Python, Git local, ajuste de acesso ao arquivo da chave, estado do painel e
  arquivos de atalho sao reais; o caminho do kit inclui espacos.
- Os dois agentes concluem a instalacao sem exigir perfil ou carga de contexto
  ja completos. O painel abre uma vez e identifica o agente correto.
- Falhas no Python, programas, preparacao do agente, chave e conferencia saem com
  erro. Depois de aberto, o painel termina com pendencias, sem anunciar sucesso.
- Nenhum caminho testado chama o GitHub CLI para autenticar o cliente.

Downloads, instalacao dos aplicativos, registro MCP e resposta de rede sao
simulados. A chave e apenas texto ficticio, sem acesso a qualquer repositorio.
Os artefatos `windows-powershell` e `windows-pwsh` guardam somente relatorios JSON
e saida dos testes por sete dias. Nao publicar o kit temporario nem chaves nos
artefatos.

## O que ainda exige uma maquina virtual Windows 11

O runner vem com programas pre-instalados, usa Windows Server e nao reproduz o
primeiro uso de uma pessoa. O resultado verde nao homologa estes pontos:

1. Extrair o ZIP completo e abrir `instalar\instalar.cmd` com dois cliques.
2. Instalar uv/Python, Git, Obsidian e o agente numa conta limpa, inclusive as
   confirmacoes do Windows e o comportamento quando falta winget.
3. Ver o navegador abrir, acompanhar o painel e testar Copiar texto e os atalhos.
4. Autenticar no agente com uma conta de teste; abrir o cofre, criar uma nota e
   reler a edicao pelo agente.
5. Com um kit ficticio provisionado em repositorio privado, confirmar envio e
   recebimento pela chave, sem conta/codigo GitHub do cliente.
6. Repetir a instalacao preservando as notas e conferir uma falha de conexao.

Essa rodada pode ser feita numa VM Windows 11 no Mac ou numa VM remota temporaria.
Registrar versao do Windows, commit da fabrica, versao do kit, resultado e
evidencias antes de liberar aos clientes.

## Como repetir

No Windows, com Python 3.12 e Git instalados:

```powershell
$env:KIT_TEST_SHELL = 'powershell'
python testes/testar_instalador_windows.py -v
$env:KIT_TEST_SHELL = 'pwsh'
python testes/testar_instalador_windows.py -v
```

O teste preserva e restaura os tres atalhos do kit na Area de Trabalho. Em Linux
ou macOS o comando termina com erro, sem apresentar testes ignorados como prova
de validacao Windows.

Os testes estao preparados sobre a linha do PR #8. A fabrica 1.6.0 precisa ser
recuperada e receber as mudancas antes de gerar uma entrega. Nao executar
`montador/atualizar.py --todos` a partir desta linha anterior.

A versao 1.4.3 identifica apenas a correcao do painel nesta linha de homologacao:
uma interrupcao nao pode aparecer como sucesso quando programas e chave ja estao
prontos. Ela nao substitui a fabrica 1.6.0 nem autoriza atualizar kits entregues.
