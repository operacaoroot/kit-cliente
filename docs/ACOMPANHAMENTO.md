# Acompanhamento

## Como funciona

`acompanhador/acompanhar.py` roda às 08:30, 13:00 e 18:00. Para cada kit publicado ele lê pela API
do GitHub o `.root/progresso.json`, os últimos commits e os pedidos em `ajuda/`, compara com a
rodada anterior (`acompanhador/estado.json`) e grava o relatório em `acompanhador/saida/`.

**Nenhum modelo de IA é chamado.** O que ele entrega:

- tabela com passos feitos, passo atual, dias sem avanço, pedidos abertos e último envio;
- o que mudou desde a rodada anterior (passo concluído, pedido novo);
- alertas: parado além do limite do perfil (guiado 2 dias, chat 3, construtor 5), pedido de ajuda
  aberto além do prazo combinado, `kit_id` diferente do emitido;
- uma mensagem sugerida no tom do perfil, montada a partir dos modelos de `perfis/perfis.json`.

Nada vai para o cliente sozinho. O sócio responsável lê, ajusta e manda pelo canal combinado.
Quando precisar de ajuda para escrever uma resposta difícil, aí sim abre o Claude e pede, sobre o
relatório. É o único momento que custa modelo.

## Ligar e desligar

```bash
bash acompanhador/agendar.sh          # liga no Mac (launchd)
bash acompanhador/agendar.sh --tirar  # desliga
python3 acompanhador/acompanhar.py    # rodar agora, na mão
python3 acompanhador/acompanhar.py --json   # formato para o ROOT OS ler depois
```

Com o Mac dormindo no horário, o launchd roda quando ele acordar. Quando a bancada `/onboarding`
do OS passar a ler o `--json`, o agendamento migra para a VPS da Root.

## Responder um pedido de ajuda

```bash
python3 acompanhador/responder.py <slug> ajuda/<arquivo>.md "resposta" --por "Nome do sócio"
```

Grava a resposta no arquivo do pedido e marca `estado: respondido`. O Claude do kit mostra a
resposta ao cliente antes de qualquer outra coisa. Mande também pelo canal combinado: a ferramenta
registra, não avisa.
