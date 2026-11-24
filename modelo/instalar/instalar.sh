#!/bin/bash
# Instalador do kit (Mac e Linux). Prepara o computador a partir de ambiente/apps.json,
# cria o Python do kit, liga o kit à Root pela chave que vem nele (sem conta nem código do
# GitHub), faz o que o agente do kit pede (instalar/agente.sh: liberação, servidor da empresa,
# atalho) e roda a conferência. O Painel do kit abre no navegador e mostra cada passo.
# Pode rodar quantas vezes quiser: o que já está instalado é pulado.
# Opcionais do catálogo: bash instalar/instalar.sh --com vscode,docker
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$KIT" || exit 1
SISTEMA="$(uname -s)"

passo() { printf '\n== %s\n' "$1"; }
falha() { printf '\n[atenção] %s\n' "$1"; }
# O painel é só vitrine: se falhar, a instalação segue.
painel() { python3 ferramentas/painel.py "$@" >/dev/null 2>&1 || true; }
# Depois que o painel abriu: fecha a conferência nele antes de sair, para a página não ficar parada.
parar() { painel concluir; exit "${1:-1}"; }
# A parte que muda com o agente do kit (claude ou codex) mora em instalar/agente.sh:
# agente_preparar, agente_ligar e agente_atalho. O montador põe ali só a versão do agente deste kit.
. "$KIT/instalar/agente.sh"

passo "Conferindo as ferramentas básicas"
if [ "$SISTEMA" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
  falha "O Mac precisa das ferramentas de linha de comando da Apple (elas trazem o git). Uma janela vai abrir: clique em Instalar, espere terminar e rode este instalador de novo."
  xcode-select --install
  exit 2
fi
command -v git >/dev/null 2>&1 || { falha "git não encontrado. No Linux: sudo apt install git"; exit 1; }
command -v python3 >/dev/null 2>&1 || { falha "python3 não encontrado. No Linux: sudo apt install python3"; exit 1; }
echo "git e Python do sistema ok"

painel iniciar --abrir
painel etapa basico ok "git e Python do sistema prontos"
echo "O Painel do kit abriu no navegador: ele mostra o que está acontecendo e o que falta."

painel etapa programas andamento "instalando o que falta"
if python3 ferramentas/ambiente.py --instalar "$@"; then
  painel etapa programas ok "programas do kit instalados"
else
  falha "Faltam programas obrigatórios. Corrija o aviso acima e rode o instalador de novo."
  painel etapa programas falhou "faltam programas obrigatórios; veja a lista do que falta"
  parar 1
fi
export PATH="$HOME/.local/bin:$PATH"

painel etapa python andamento
if python3 ferramentas/ambiente.py --venv; then
  painel etapa python ok "Python do kit pronto"
else
  falha "O Python do kit não ficou pronto."
  painel etapa python falhou "não consegui criar o Python do kit; rode o instalador de novo"
  parar 1
fi

painel etapa autonomia andamento
if agente_preparar; then
  painel etapa autonomia ok "o agente do kit está pronto para trabalhar"
else
  falha "A preparação do agente não terminou."
  painel etapa autonomia falhou "a preparação do agente não terminou"
  parar 1
fi

passo "Ligando o kit à Root"
# Sempre pela chave que veio no kit: sem conta, sem login e sem código do GitHub.
painel etapa chave andamento "pela chave que veio no kit"
if python3 ferramentas/conectar.py --usar-chave; then
  painel etapa chave ok "kit ligado pela chave; sem conta nem código do GitHub"
else
  painel etapa chave falhou "a chave do kit não veio no ZIP; extraia o ZIP inteiro de novo"
  parar 1
fi

agente_ligar

painel etapa atalho andamento
if [ "$SISTEMA" = "Darwin" ]; then
  mkdir -p "$HOME/Desktop"
  agente_atalho
  ATALHO_PAINEL="$HOME/Desktop/Painel do kit.command"
  printf '#!/bin/bash\nopen "%s/painel/index.html"\n' "$KIT" > "$ATALHO_PAINEL" && chmod +x "$ATALHO_PAINEL"
  if [ -x "$ATALHO_PAINEL" ]; then
    echo "atalho criado na Mesa: Painel do kit"
    painel etapa atalho ok "atalho do agente e Painel do kit na Mesa"
  else
    falha "não consegui criar o atalho Painel do kit na Mesa"
    painel etapa atalho atencao "não consegui criar o atalho Painel do kit na Mesa"
  fi
else
  echo "Painel do kit: $KIT/painel/index.html"
  painel etapa atalho ok "no Linux o painel fica em painel/index.html, dentro do kit"
fi

passo "Conferência"
python3 ferramentas/ambiente.py --conferir || parar 1
python3 ferramentas/verificar.py || parar 1
# Os demais passos do onboarding podem ficar pendentes; a instalação precisa estar pronta.
python3 -c 'import json,sys; p=json.load(open(".root/progresso.json")); sys.exit(0 if any(x.get("id")=="instalar" and x.get("feito") is True for x in p.get("passos",[])) else 1)' || {
  falha "A instalação ainda tem pendências. Corrija o que a conferência indicou e rode de novo."
  parar 1
}
painel concluir
echo
echo "O Painel do kit (no navegador e no atalho Painel do kit) mostra o que ficou pronto, o que falta"
echo "e os próximos passos com o texto para o agente do kit."
