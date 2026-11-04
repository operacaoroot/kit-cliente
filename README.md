<p align="center">
  <img src="modelo/marca/root-logo.png" alt="OPERAÇÃO ROOT" width="300">
</p>

<h1 align="center">Kit do cliente</h1>

<p align="center">
  Onboarding, contexto de trabalho e ferramentas para usar o Claude com uma base própria no Obsidian.
</p>

<p align="center">
  <a href="#começar-como-cliente">Começar</a> ·
  <a href="#o-que-o-kit-entrega">O que vem no kit</a> ·
  <a href="#preparar-uma-entrega-na-root">Preparar uma entrega</a> ·
  <a href="docs/ONBOARDING-GUIADO.md">Guia do onboarding</a>
</p>

---

Este repositório é a **fábrica dos kits da ROOT**. A partir das informações conferidas no kickoff, ela gera um pacote próprio para cada cliente: instruções, configuração do Claude, notas no Obsidian e ferramentas para as primeiras tarefas.

O cliente recebe um **ZIP instalável e um repositório privado**. Depois da configuração, trabalha na área **Code do aplicativo Claude**, com a pasta do kit aberta, e consulta ou edita suas notas no Obsidian.

> **Para usar as skills, a conta precisa ter acesso ao Claude Code.** Abrir o chat comum do aplicativo não carrega a pasta nem as ferramentas do kit.

## Começar como cliente

O caminho no macOS começa pelo ZIP. Git será instalado pelo pacote; não é preciso executar um clone antes.

1. Entre no GitHub com a conta convidada pela ROOT e abra o **repositório privado do seu kit**.
2. Abra **Releases** e baixe o ZIP do kit em **Assets**. Os arquivos chamados **Source code** não incluem o acesso preparado pela ROOT.
3. Extraia o ZIP e mantenha a pasta completa. Abra `instalar/instalar.command` com dois cliques.
4. Se forem solicitadas ferramentas da Apple, termine a instalação e abra o mesmo arquivo novamente.
5. Continue pela página ROOT que abre no navegador. Ela orienta o cadastro, a instalação e o primeiro uso.

Se o macOS bloquear o instalador, confirme a origem do arquivo com a ROOT e siga a liberação em **Ajustes do Sistema → Privacidade e Segurança → Abrir Mesmo Assim**.

| Na página | O que você faz |
|---|---|
| **Seus dados** | Confirma nome, atividade, empresa, responsabilidades, primeira tarefa e preferências. Pode informar sites e redes pessoais e da empresa. |
| **Primeira carga** | Se autorizar a coleta pública, revisa e escolhe os trechos que vão para o Obsidian. Pode acrescentar texto manualmente. |
| **Programas** | Instala as ferramentas do kit, baixa o aplicativo Claude pelo site oficial e confere o ambiente. |
| **Primeiro uso** | Abre o Claude na pasta do kit, envia a mensagem de teste e confere a nota no Obsidian. |
| **Conferência final** | Revisa o envio ao GitHub com o Claude e confirma que a carga e a nota de teste estão sincronizadas. |

Para retomar, use **Continuar onboarding** na Mesa. Para trabalhar depois, use **Claude do kit**. Na primeira abertura do Obsidian, a página explica como registrar a pasta `vault` como cofre.

**Windows:** abra `instalar\instalar.cmd` e siga `COMECE-AQUI.md`. O Windows mantém o fluxo anterior, sem a nova página guiada. Consulte [Ambiente do cliente](docs/AMBIENTE.md).

<details>
<summary><strong>Pacote de homologação usado no ROOT Studio</strong></summary>


[Baixar o ZIP pelo GitHub](https://github.com/operacaoroot/kit-homologacao-root-brand-v4/releases/tag/onboarding-root-studio-2026-09-30), com uma conta que tenha acesso ao repositório privado.

Esse pacote usa **Marina Duarte / Distribuidora Exemplo**, dados fictícios. É material de teste; cada cliente recebe um pacote gerado para ele.

</details>

## O que o kit entrega

| Parte | Para que serve |
|---|---|
| **Claude com contexto** | `CLAUDE.md`, perfil de interação, skills e agente de auditoria orientam o trabalho dentro da pasta do kit. |
| **Base no Obsidian** | Notas de identidade, organização, operação, projetos, decisões, dados e metas, com indicação do que precisa ser revisado. |
| **Ambiente de trabalho** | Git, GitHub CLI, Python, Node, Java, Claude Code e Obsidian, conforme o catálogo. O kit também cria seu ambiente Python `.venv`. |
| **Ferramentas da primeira frente** | Skills escolhidas a partir do trabalho combinado no kickoff e registradas em `catalogo.json`. |
| **Oficina** | Processo para criar, testar e registrar ferramentas próprias à medida que surgem tarefas recorrentes. |
| **Acompanhamento** | Progresso e catálogo no GitHub; a ROOT gera relatórios e sugestões de resposta, revisadas por um sócio antes do envio. |

As skills de base cobrem preparar o ambiente, ajustar o perfil, cuidar do cofre, extrair contexto, escolher o próximo passo, pedir ajuda, criar skills, fechar o dia e validar o onboarding. O agente `auditor-de-contexto` confere a extração de contexto.

A coleta inicial consulta apenas os endereços públicos informados, respeita `robots.txt` e exige revisão antes de gravar trechos no cofre. O material bruto fica fora do Git. O Claude processa o contexto necessário pela conta do cliente.

## Estado da validação

| Verificação | Resultado registrado em 30/09/2026 |
|---|---|
| Testes automatizados | 14 de onboarding e 28 da base passaram. Um teste de sintaxe PowerShell foi ignorado por ausência de `pwsh`. |
| Instalação no ROOT Studio / UTM | ZIP recebido, instalador executado, ferramentas Apple instaladas e página ROOT aberta. Cadastro e carga inicial salvos; programas detectados; Claude e Obsidian abertos. |
| Uso das skills e sincronização | **Pendente.** A conta gratuita disponível não liberou Claude Code. A nota de teste e a sincronização da carga nova não foram validadas nessa rodada. |
| Coleta pública na VM | **Pendente.** Não exercitada nessa rodada; há testes automatizados e uma conferência anterior no navegador. |
| Windows real | **Pendente.** Não homologado nesta rodada. |

A página só marca o ambiente como pronto quando encontra a carga revisada, os programas, a prova funcional e os arquivos sincronizados no repositório esperado. Abrir os aplicativos não basta para essa conclusão. [Critérios e roteiro de homologação](docs/ONBOARDING-GUIADO.md#critérios-de-conclusão).

## Preparar uma entrega na ROOT

Na máquina de montagem, use Python 3.9 ou superior, Git e `ssh-keygen`. A publicação exige o token da conta `operacaoroot`, configurado em `~/.config/root/github.env`. O segredo do selo fica em `~/.config/root/kit.env`. Esses arquivos não entram no repositório.

### 1. Conferir o kickoff e definir o perfil

Copie o manifesto e preencha as informações do cliente, as fontes das conversas e a frente combinada:

```bash
cp manifestos/_modelo.json manifestos/novo-cliente.json
python3 perfis/pontuar.py manifestos/novo-cliente.json --gravar
```

A pontuação propõe um perfil; um sócio confere e assina `perfil.escolhido` e `perfil.conferido_por`. As reuniões também precisam estar conferidas. O montador recusa a entrega sem esses campos. Informe a conta do cliente em `cliente.github` para convidá-lo como colaborador.

Consulte o [roteiro de kickoff](docs/KICKOFF.md), os [perfis](docs/PERFIS.md) e o [manifesto de exemplo](manifestos/exemplo-marina-duarte.json).

Se o agente do computador da pessoa for o **Codex do ChatGPT** em vez do Claude, ponha `"agente": "codex"` no manifesto (e o bloco `mcp` quando a empresa tiver servidor MCP). O kit sai com o Codex CLI, `AGENTS.md`, as skills em `.agents/skills` e o registro do servidor por `codex mcp add` na instalação. Critérios, testes e validação real em [Kit em versão Codex](docs/KIT-CODEX.md); exemplo fictício em `manifestos/exemplo-codex-helena-prado.json`.

### 2. Gerar o kit e o repositório privado

```bash
python3 montador/montar.py manifestos/novo-cliente.json --github --zip
```

O montador cria o kit em `saida/`, publica o repositório privado, prepara a chave exclusiva, convida o cliente quando informado e gera o ZIP. Use o nome e o caminho exibidos ao final do comando na publicação abaixo.

### 3. Publicar o download

Com GitHub CLI autenticado na conta ROOT, confirme que o destino é **PRIVATE** antes de enviar:

```bash
gh repo view operacaoroot/kit-novo-cliente --json visibility
```

Neste exemplo, `novo-cliente` é o slug do manifesto. Confira sempre o nome exibido pelo montador.

Publique no repositório privado conferido, substituindo os valores pelo resultado da montagem:

```bash
gh release create entrega-inicial saida/novo-cliente.zip \
  --repo operacaoroot/kit-novo-cliente \
  --title "Kit inicial" \
  --notes "Baixe o ZIP em Assets, extraia e siga COMECE-AQUI.md."
```

O ZIP contém dados do cliente e uma chave de acesso. Entregue o link da Release apenas a quem tem acesso ao kit. Não use uma Release pública nem os arquivos automáticos **Source code** como pacote de instalação.

### 4. Acompanhar e manter

```bash
python3 acompanhador/acompanhar.py
python3 montador/acesso.py estado novo-cliente
python3 montador/acesso.py convidar novo-cliente --usuario LOGIN-DO-CLIENTE
```

O agendamento de três execuções diárias é configurado separadamente; executar `acompanhar.py` uma vez não cria esse agendamento. Veja [Acompanhamento](docs/ACOMPANHAMENTO.md), [Acesso e encerramento](docs/CHAVE.md) e [Atualizar kits entregues](docs/ARQUITETURA.md#atualizar-kits-entregues).

## Documentação e código

| Quando precisar… | Abra |
|---|---|
| Entender etapas, responsabilidades e estrutura do kit | [Arquitetura](docs/ARQUITETURA.md) |
| Conferir a página guiada, a coleta e os critérios de conclusão | [Onboarding no macOS](docs/ONBOARDING-GUIADO.md) |
| Montar o kit com o Codex no lugar do Claude | [Kit em versão Codex](docs/KIT-CODEX.md) |
| Ver programas, instalação por sistema e links oficiais | [Ambiente](docs/AMBIENTE.md) |
| Criar ferramentas com o cliente | [Desenvolvimento](docs/DESENVOLVIMENTO.md) |
| Alterar textos, página, cofre ou skills de base | [`modelo/`](modelo/) |
| Alterar as ferramentas de uma frente | [`receitas/`](receitas/) |
| Gerar, atualizar ou administrar kits | [`montador/`](montador/) |
| Alterar pontuação e sinais de perfil | [`perfis/`](perfis/) |
| Conferir progresso e preparar respostas a pedidos de ajuda | [`acompanhador/`](acompanhador/) |

<details>
<summary><strong>Verificação local</strong></summary>


Os testes de API do onboarding precisam poder abrir uma porta local. Para os testes da base, use um segredo temporário, evitando criar ou utilizar a configuração pessoal de selo:

```bash
python3 testes/testar_onboarding.py -v
KIT_SELO_SEGREDO=teste-local-descartavel python3 testes/testar_base.py -v
KIT_SELO_SEGREDO=teste-local-descartavel python3 testes/testar_codex.py -v
python3 -m compileall -q modelo/ferramentas montador
bash -n modelo/instalar/instalar.command
```

O teste de sintaxe Windows requer `pwsh`. Testes automatizados não substituem a instalação e o uso em uma máquina limpa.

</details>

<details>
<summary><strong>Regras de manutenção</strong></summary>


- A fábrica usa apenas a biblioteca padrão do Python, compatível com 3.9. O cliente recebe um ambiente Python 3.12 próprio do kit.
- Repositórios, entrega e acompanhamento ficam no GitHub `operacaoroot` e na VPS da ROOT. O kit também usa a conta Claude do cliente para o processamento pelo modelo.
- `saida/` contém dados e chaves dos clientes e nunca é versionada nesta fábrica. Tokens, segredo do selo, chave privada e estado privado também ficam fora do Git.
- O montador não chama modelos de IA. `--rascunho` permite demonstração no kickoff, mas bloqueia publicação e geração do ZIP de entrega.
- Atualizações preservam as ferramentas e notas do cliente. Textos do kit não citam outros clientes e passam pela revisão de texto da receita `kit-de-contexto-e-conteudo`.
- A regra de integração combinada pelos sócios em 29/09/2026 prevê homologação local e revisão na reunião de quinta; consertos de defeitos podem entrar na hora. Uma autorização explícita dos sócios pode definir outra entrega, como nesta homologação.

</details>
