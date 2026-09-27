# Perfis

Três perfis de partida, definidos em `perfis/perfis.json`. O perfil escolhe o nível do texto do
kit, o tom do Claude, o ritmo, o jeito de entregar e o limite de dias parado antes do alerta.
Tom, formato, iniciativa, ritmo e horário continuam ajustáveis por pessoa.

| | Guiado | Usuário de chat | Construtor |
|---|---|---|---|
| Quem é | nunca usou IA ou usou pouco | usa ChatGPT ou Claude toda semana | já automatiza |
| Texto | explica cada clique | passo com o porquê | comando direto |
| Tom | explicado | direto, com contexto | direto |
| Iniciativa do Claude | sempre sugere | sugere o que for importante | só quando pedido |
| Ritmo | 1 passo por dia | 2 por dia | 3 por dia |
| Instalação | sempre ao vivo | ao vivo nos primeiros clientes | sozinho |
| Alerta de parado | 2 dias | 3 dias | 5 dias |

## Como o perfil é proposto

1. Quem conduz o kickoff (ou o leitor de ata) marca os **sinais** que apareceram na conversa, cada
   um com minuto e trecho, em `perfil.sinais` do manifesto. O catálogo de sinais e os pesos estão em
   `perfis.json`.
2. `python3 perfis/pontuar.py manifestos/<slug>.json --gravar` soma os pesos, converte em
   porcentagem e grava a proposta em `perfil.proposto`.
3. Se o primeiro perfil passa de 60% e está 15 pontos à frente do segundo, o resultado é
   **sócio confere**. Senão, **sócio decide**.
4. Em qualquer caso, um sócio assina `perfil.escolhido` e `perfil.conferido_por`. O montador recusa
   kit sem assinatura.

## Calibrar

Os pesos de hoje são julgamento da Root (2026-09-27). Depois de 10 a 15 clientes, comparar o perfil
previsto com o que o acompanhador mediu (passos por dia, pedidos de ajuda, dias parado) e ajustar os
pesos. Toda mudança de peso sobe a `versao` do arquivo, e a proposta gravada em cada manifesto
guarda a versão usada.
