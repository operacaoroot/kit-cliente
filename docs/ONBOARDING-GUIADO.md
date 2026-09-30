# Onboarding guiado: macOS

Branch baseada no PR #1, sem alterar a branch do Rodrigo. O instalador macOS abre uma página
local para confirmar dados profissionais, revisar fontes públicas, preparar o computador e
iniciar uma sessão local de Claude Code na interface do aplicativo. O chat comum não carrega
as pastas do kit automaticamente.

## Fluxo entregue

1. Instalar as ferramentas Apple, se necessário, e reabrir o instalador. Não há mensagem de
   sucesso nesse ponto. Após o pré-requisito, a página abre no navegador.
2. Confirmar nome, cargo/atividade, empresa, setor, responsabilidades, público, primeira tarefa,
   preferência de explicação, sites e redes sociais pessoais e da empresa.
3. Opcionalmente autorizar a coleta dos endereços informados. Rever os dados e selecionar/editar
   os trechos que entrarão na base. Sites bloqueados permitem colar o texto manualmente.
4. Confirmar a carga inicial, instalar os programas e conferir o ambiente. A instalação do
   aplicativo Claude continua manual pelo download oficial; a página explica isso explicitamente.
5. Abrir Claude Code no aplicativo com a pasta local do kit, confirmar a pasta, entrar na própria
   conta e enviar a mensagem de teste. O link não envia a mensagem sozinho.
6. Na primeira abertura do Obsidian, registrar a pasta como cofre seguindo as instruções da página.
   Conferir a nota criada no Obsidian, revisar o envio com o Claude e sincronizar com o repositório.
   Voltar à página e conferir. Importação de histórico e criação de skills próprias permanecem
   como etapas de aprofundamento, fora dos critérios de configuração inicial.

## Dados e execução

- Servidor Python da biblioteca padrão, em `127.0.0.1`, porta efêmera. API exige token aleatório,
  Host e Origin corretos. Sem CORS, arquivos privados ou comandos arbitrários expostos.
- Estado, coleta bruta, desafio e prova ficam em `_privado/onboarding/`, fora do Git. O token
  fica no fragmento do link e na sessão do navegador; não aparece em logs HTTP.
- A confirmação cria uma nota datada em `vault/10-Identidade/` e atualiza `perfil-inicial.md`.
  Não sobrescreve notas anteriores nem muda a identidade assinada de `.root/cliente.json`.
- `CLAUDE.md` manda consultar a carga confirmada antes dos dados originais do kickoff. O
  `perfil.md` conserva as preferências existentes; confirmar dados profissionais não marca
  automaticamente todo o perfil de interação como aprovado.
- Coleta limitada aos links fornecidos (até 12.000 caracteres por fonte), sem login, cookies,
  navegador automático ou busca de perfis por nome. Respeita robots.txt e trata bloqueios como
  pendência manual. Valida IPs públicos, fixa o IP da conexão e revalida redirecionamentos.
- Trechos externos são citados como dados, nunca instruções do agente. Nenhuma IA é chamada
  pelo coletor. O uso posterior pelo Claude processa o contexto necessário pela conta do cliente;
  não prometer que o processamento do modelo ocorre inteiramente no computador.
- Uma instância por kit no macOS. Reabrir o atalho recupera a sessão ativa ou cria uma nova.
  Fechar o processo interrompe o serviço; os dados confirmados permanecem salvos.

## Critérios de conclusão

A página só indica ambiente pronto com carga inicial revisada, programas obrigatórios e venv
presentes, aplicativo Claude presente, leitura do remoto funcionando, prova local válida e carga
inicial/nota de teste versionadas e sem diferenças em relação ao HEAD publicado no remoto.

`validar-onboarding` instrui o Claude a ler os dados, usar `cuidar-do-vault`, criar uma nota com
nome, objetivo e nonce, e registrar o hash da skill lida. Essa prova é um teste funcional simples,
não uma atestação de segurança nem garantia de qualidade da resposta. A pessoa deve conferir a
nota na interface. O onboarding não envia arquivos por conta própria: a pessoa revisa o envio
com o Claude. O teste de sincronização pressupõe o fluxo padrão do kit na branch principal.

## Validação

- `python3 testes/testar_onboarding.py -v`: estado, revisão, preservação, fontes, URLs, robots,
  prova, sincronização e API local. Os testes de API precisam poder abrir uma porta loopback.
- `python3 testes/testar_base.py -v`: regressões do montador e do kit; definir um
  `KIT_SELO_SEGREDO` temporário para evitar usar/criar configuração pessoal durante os testes.
- Sintaxe: `python3 -m compileall -q modelo/ferramentas montador` e `bash -n modelo/instalar/instalar.command`.

## Roteiro de homologação na VM

1. Clonar a VM base limpa e entregar um ZIP novo, com cliente fictício e repositório privado de teste.
2. Seguir apenas COMECE-AQUI e as telas. Registrar qualquer intervenção não documentada.
3. Exercitar ausência de ferramentas Apple, bloqueio do macOS e retomada após instalação.
4. Preencher dados fictícios, coletar uma página pública permitida e testar uma página bloqueada.
5. Revisar/editar a coleta e verificar que apenas os trechos aceitos chegam ao vault.
6. Interromper/reabrir a página e conferir os dados salvos. Repetir a confirmação e verificar
   preservação das notas anteriores.
7. Instalar dependências e Claude; entrar na conta de teste. Confirmar abertura em Code local,
   pasta correta, leitura do perfil e execução da skill. Conferir a nota no Obsidian.
8. Testar ausência de rede e acesso GitHub negado: devem permanecer pendências.
9. Autorizar envio dos arquivos fictícios, confirmar no remoto e repetir a conferência.
10. Fechar/reabrir o Claude pelo atalho e pedir uma tarefa baseada no perfil.

Login, confirmações do macOS/Claude e envio ao repositório precisam de homologação real. Testes
unitários e prévia no navegador não substituem essa etapa. O instalador Windows permanece no
fluxo anterior e não está homologado para a interface nova.

## Decisões e referência

Reaproveitar scripts/skills existentes, manter instalação e dados locais, sem serviço central,
sem coletar páginas autenticadas. A Root mantém o modelo; as preferências e notas do cliente são
preservadas. A interface responde enquanto instalação e coleta executam em segundo plano.

Abertura oficial do app: https://support.claude.com/en/articles/14729294-open-claude-desktop-with-a-link

`claude://code/new?folder=<pasta>&q=<mensagem>` abre o compositor preenchido. O aplicativo exige
confirmação da pasta. Não presumir que abrir esse link prova login ou execução da skill.

## Identidade ROOT

Referência: documento-mestre **ROOT — Fundamentos da marca e guia de expressão**, versão 2.0,
28/09/2026, seções 03 e 04; acervo interno `Root/40-marca-e-conteudo/`.

- Escuro padrão: fundo #070A08, painel #0C120D, texto #DFFFE8, ação/seleção #9BDB1F.
- Estados separados: ciano #1FFFA8 para confirmação, âmbar #E8B90F para pendência,
  magenta #FF1F6B para falha. Sempre acompanhados de texto, sem depender apenas da cor.
- Temas Papel (#ECE7D8/#4D7208) e Mono mantêm hierarquia e conteúdo; preferência fica no navegador.
- Space Grotesk 400/700 e JetBrains Mono 400 distribuídas localmente, com licenças OFL.
- Cantos de 3 px, foco de teclado de 1 px, superfícies sólidas, sem neon, gradientes ou sombras.
- Logo de produção já presente em `modelo/marca/root-logo.png`, sem reconstrução tipográfica.
  O guia registra pendência entre os vetores anteriores (19,2°) e o tratamento v2 (10°);
  esta alteração não cria nem declara aprovado um novo wordmark.

Os arquivos tipográficos vêm do acervo de lançamento e do site ROOT v2. O tema mono remove
as cores do logo por apresentação CSS. No tema papel o logo original é preservado em uma
superfície escura, evitando uma adaptação não aprovada de seus canais.
