# Roteiro do kickoff

O kickoff é uma conversa de 60 minutos, gravada, em que a Root descobre o perfil do cliente e
alinha com ele o kit que vai receber. Os sócios conduzem em rodízio. O roteiro tem um **mínimo
obrigatório** e o resto se adapta ao cliente. Toda adaptação vai para
`kickoff.desvios_do_roteiro` no manifesto, porque é assim que o roteiro melhora.

## Antes (quem conduz, até a véspera)

1. **Conferir as reuniões.** Ler as atas de todas as conversas com o cliente e preencher o
   manifesto com o que já foi dito: dores com minuto, fontes citadas, notas iniciais com fonte.
   Tudo o que for dedução fica fora ou vai como pergunta para o kickoff.
2. **Marcar os sinais de perfil** que as conversas anteriores já mostraram (`perfil.sinais`, cada
   um com minuto e trecho) e rodar `python3 perfis/pontuar.py manifestos/<slug>.json`.
3. **Montar o rascunho do kit** com `python3 montador/montar.py manifestos/<slug>.json --rascunho`.
   É esse rascunho que aparece na tela durante a conversa.
4. **Confirmar o Granola** gravando e avisar o cliente que a conversa será gravada.

## Durante (60 minutos)

| Bloco | Tempo | Obrigatório | O que sai no manifesto |
|---|---|---|---|
| Abertura | 5 min | mostrar o rascunho na tela e dizer que hoje ele corrige | nada |
| Como você trabalha e usa IA | 15 min | perguntar sobre o dia a dia e as ferramentas, **nunca** "qual tom você prefere" | `perfil.sinais`, `perfil.ajustes` |
| Onde mora o trabalho | 15 min | o cliente compartilha a tela e mostra de onde vêm as coisas | `fontes` (3 prioritárias) e `dores` |
| O kit | 20 min | mostrar os passos, a frente escolhida e as notas; ele corrige em voz alta | `frente`, `notas_iniciais`, ajuste de perfil |
| Instalação | dentro do bloco anterior | nos primeiros clientes e em todo perfil guiado: instalar o passo 1 ao vivo | `desvios_do_roteiro` se não deu |
| Combinado | 5 min | horário do acompanhamento, canal de ajuda, assinatura do Claude e a rotina do vault (autoriza? horários? envia o reporte?) | `combinado` (inclusive `rotina_do_vault`), `claude` |

### Perguntas que costumam render sinais de perfil

- "Me conta o que você fez ontem, do começo ao fim." (tempo, ferramentas, onde trava)
- "Quando você usa o ChatGPT ou o Claude, para quê?" (uso de IA, frequência, prompt salvo)
- "Já montou alguma automação, planilha com fórmula, integração?" (construtor)
- "Se eu te mandar um passo a passo, você prefere fazer sozinho ou que eu faça junto na primeira?"
  (guiado ou chat)
- "Que horas do dia sobram para mexer nisso?" (ritmo e horário)

Anote o minuto de cada frase que servir de sinal. Frase sem minuto não entra na pontuação.

### A rotina do vault, no combinado

Dizer em duas frases: "Três vezes ao dia o kit olha só o que aconteceu dentro desta pasta, as
conversas com o Claude e os arquivos do kit, escreve o diário e as notas no seu vault e manda para o
repositório do kit o reporte que a gente acompanha. Senha e documento saem mascarados e nada de
`entrada/` é copiado." Perguntar se autoriza e em que horários (padrão 08:00, 12:30 e 17:30).
Sem autorização: `ligar: false`. Detalhes em `docs/ROTINA-DO-VAULT.md`.

### O que não fazer

- Não transformar a conversa num questionário lido em voz alta. Foi o que não funcionou.
- Não prometer frente que não está inteira no cardápio (`receitas/`).
- Não instalar nada na máquina do cliente sem ele estar olhando.

## Depois (até 24 horas)

1. Passar os sinais novos para o manifesto e rodar `pontuar.py --gravar`.
2. **Um sócio assina o perfil** (`perfil.escolhido`, `perfil.conferido_por`, `perfil.conferido_em`).
   Se a pontuação disser "sócio decide", a escolha vem com uma linha de justificativa em
   `desvios_do_roteiro`.
3. **Conferência das reuniões assinada** (`conferencia_das_reunioes.feita_por`), sem divergência em aberto.
4. Montar e publicar: `python3 montador/montar.py manifestos/<slug>.json --refazer --github --zip`.
5. Mandar o zip por canal privado (ele leva a chave do kit) com a mensagem de boas-vindas no tom do
   perfil e a instrução do Claude: assinar o plano individual no nome dele e mandar o comprovante
   para o reembolso do primeiro mês.
6. Commitar o manifesto neste repositório.
