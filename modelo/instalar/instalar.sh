#!/bin/bash
# Instalador do kit (Mac e Linux). Prepara o computador a partir de ambiente/apps.json,
# cria o Python do kit, liga o kit à Root pela chave que vem nele (sem conta nem código do
# GitHub) e roda a conferência. O Painel do kit abre no navegador e mostra cada passo.
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

passo "Conferindo as ferramentas básicas"
if [ "$SISTEMA" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1; then
  falha "O Mac precisa das ferramentas de linha de comando da Apple (elas trazem o git). Uma janela vai abrir: clique em Instalar, espere terminar e rode este instalador de novo."
  xcode-select --install
  exit 0
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
  painel etapa programas atencao "algum programa não ficou instalado; veja a lista do que falta"
fi
export PATH="$HOME/.local/bin:$PATH"

painel etapa python andamento
if python3 ferramentas/ambiente.py --venv; then
  painel etapa python ok "Python do kit pronto"
else
  painel etapa python falhou "não consegui criar o Python do kit; rode o instalador de novo"
fi

passo "Liberando o Claude para trabalhar sem pedir permissão"
painel etapa autonomia andamento
if python3 ferramentas/autonomia.py; then
  painel etapa autonomia ok "o Claude trabalha sem pedir permissão a cada passo"
else
  painel etapa autonomia atencao "não consegui gravar a liberação do Claude"
fi

passo "Ligando o kit à Root"
# Sempre pela chave que veio no kit: sem conta, sem login e sem código do GitHub.
painel etapa chave andamento "pela chave que veio no kit"
if python3 ferramentas/conectar.py --usar-chave; then
  painel etapa chave ok "kit ligado pela chave; sem conta nem código do GitHub"
else
  painel etapa chave falhou "a chave do kit não veio no ZIP; extraia o ZIP inteiro de novo"
fi

passo "Criando os atalhos"
painel etapa atalho andamento
if [ "$SISTEMA" = "Darwin" ]; then
  mkdir -p "$HOME/Desktop"
  ATALHO="$HOME/Desktop/Claude do kit.command"
  ATALHO_PAINEL="$HOME/Desktop/Painel do kit.command"
  printf '#!/bin/bash\nexport PATH="$HOME/.local/bin:$PATH"\ncd "%s" && exec claude\n' "$KIT" > "$ATALHO" && chmod +x "$ATALHO"
  printf '#!/bin/bash\nopen "%s/painel/index.html"\n' "$KIT" > "$ATALHO_PAINEL" && chmod +x "$ATALHO_PAINEL"
  if [ -x "$ATALHO" ] && [ -x "$ATALHO_PAINEL" ]; then
    echo "atalhos criados na Mesa: Claude do kit e Painel do kit"
    painel etapa atalho ok "Claude do kit e Painel do kit na Mesa"
  else
    falha "não consegui criar os atalhos na Mesa; abra o Terminal na pasta do kit e digite claude"
    painel etapa atalho atencao "não consegui criar os atalhos na Mesa"
  fi
else
  echo "Painel do kit: $KIT/painel/index.html"
  painel etapa atalho ok "no Linux o painel fica em painel/index.html, dentro do kit"
fi

passo "Conferência"
python3 ferramentas/ambiente.py --conferir
python3 ferramentas/verificar.py
painel concluir
echo
echo "O Painel do kit (no navegador e no atalho Painel do kit) mostra o que ficou pronto, o que falta"
echo "e os próximos passos com o texto para o Claude."
