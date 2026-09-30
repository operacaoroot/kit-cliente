# Rotina do vault

Três vezes por dia o kit do cliente transforma o que aconteceu em diário e notas do vault e envia o
reporte para o repositório do kit. É o agente de rotina combinado na mesa de 2026-09-29 ("o agente
commita reportes três vezes ao dia").

## O que roda, e onde

| Peça | Onde | O que faz |
|---|---|---|
| `ferramentas/rotina.py` | no kit, sem IA | agenda, coleta, chama o Claude, envia |
| skill `alimentar-vault` | no kit, com o Claude do cliente | escreve o diário e as notas |
| `acompanhador/acompanhar.py` | na Root | mostra a rotina de cada kit e alerta se ela parou |

Horários padrão: **08:00, 12:30 e 17:30**, meia hora antes das leituras do acompanhador (08:30,
13:00, 18:00). O cliente muda com "muda o horário da rotina".

| Sistema | Agendador | Detalhe |
|---|---|---|
| Mac | launchd (`~/Library/LaunchAgents/com.operacaoroot.kit-<slug>.vault.plist`) | roda o horário perdido quando o Mac acorda |
| Windows | Agendador de Tarefas ("Root kit <slug> - rotina do vault") | `pythonw.exe` e `CREATE_NO_WINDOW`: nenhuma janela abre; `StartWhenAvailable` roda o horário perdido |
| Linux | crontab, uma linha por horário, marcada com o rótulo do kit | |

## Uma rodada

1. **Coleta, sem IA.** Desde a última alimentação: as conversas do Claude Code feitas **dentro da
   pasta do kit** (`~/.claude/projects/<caminho do kit>`, achadas pelo nome ou pela `cwd` gravada),
   os commits, os arquivos novos em `entregas/`, `ajuda/` e `entrada/`. Ruído de comando e conversa
   de subagente ficam fora. Senha, token, chave, cartão, CPF, CNPJ e chave privada saem mascarados.
   O resumo vai para `_privado/rotina/` (fora do git) e fica pendente em `.root/rotina.json`.
2. **Sem novidade, sem IA:** a rodada só atualiza o progresso e envia.
3. **Com novidade:** `claude -p` com a skill `alimentar-vault`, `--permission-mode acceptEdits`,
   `--no-session-persistence` (a rodada não vira conversa nova para a próxima coleta) e
   `--allowedTools` restrito a ler e escrever arquivos e a rodar a própria rotina. O Claude escreve
   `vault/_diario/AAAA-MM-DD.md` e até 8 notas permanentes com `origem: rotina` e `revisar: sim`,
   e termina com `rotina.py --concluir`. Tempo máximo: 20 minutos.
4. **Envio:** conferência (`verificar.py`), commit `Rotina: vault e progresso (DD/MM HH:MM)`,
   `pull --rebase` das atualizações da Root e `push`. Conflito ou rede fora: fica para a próxima.
   Com `--sem-envio`, nada sai até a pessoa fechar o dia.

O envio da rotina **não** conta como "fechar o dia" na conferência: aquele passo continua sendo gesto
da pessoa. Notas com `origem: rotina` e o `_diario/` não travam o passo "vault".

## Ligar

Combinado no kickoff, em `combinado.rotina_do_vault` do manifesto (`ligar`, `horas`, `enviar`). O
montador leva para `.root/cliente.json` e o instalador liga sozinho. Sem autorização, fica
desligada, e o cliente liga depois com "liga a rotina do vault". Antes de ligar, dizer ao cliente o
que a rotina lê (só o que é da pasta do kit) e o que envia (vault e progresso).

## Armadilhas conhecidas

- **Pasta "não confiável":** numa pasta onde o Claude Code nunca foi aberto de forma interativa,
  ele ignora o `permissions.allow` do `.claude/settings.json` do kit. A rotina não depende disso,
  porque passa `--allowedTools` na linha de comando. Abrir o Claude do kit uma vez (a instalação faz
  isso) deixa a pasta confiável.
- **Mac, `/var` e `/private/var`:** a mesma pasta aparece com os dois caminhos; a busca das
  conversas compara o caminho resolvido.
- **Horário da conversa:** o registro do Claude Code grava em UTC; a coleta converte para o fuso da
  máquina, que é o horário que a pessoa reconhece.
- **Computador desligado nos três horários:** a rodada seguinte pega tudo desde a última
  alimentação; nada se perde. O acompanhador alerta depois de 36 horas sem rodada.

## Testes

```bash
python3 testes/testar_rotina.py -v      # 15 testes: coleta, máscara, agendadores, conferência, rodada com Claude de teste
```

| Data | Onde | Resultado |
|---|---|---|
| 2026-09-30 | Mac M1, launchd real, Claude Code 2.1.285 real, conversa fictícia | agendamento com os 3 horários aceito; rodada disparada pelo launchd em 1 min; 3 notas criadas e 3 alteradas, com fonte; senha da conversa em nenhum arquivo; horário em UTC corrigido para o local depois do teste |
| 2026-09-30 | PowerShell 7.6.6 (Mac) | comando da tarefa agendada e `instalar.ps1` sem erro de sintaxe |
| pendente | Windows real | sócios |
