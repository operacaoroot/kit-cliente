#!/bin/bash
# Entrada do onboarding no macOS. As ferramentas Apple são o único pré-requisito.
DIR="$(cd "$(dirname "$0")" && pwd)"
if ! xcode-select -p >/dev/null 2>&1; then
  echo "O Mac precisa instalar as ferramentas da Apple. Confirme a instalação na janela que vai abrir."
  xcode-select --install
  echo "Quando terminar, abra este arquivo novamente para continuar. A configuração ainda não terminou."
  read -r -p "Tecle Enter para fechar esta janela." _
  exit 2
fi
if ! /usr/bin/python3 --version >/dev/null 2>&1; then
  echo "O Python da Apple ainda não está disponível. Termine a instalação e tente novamente."
  read -r -p "Tecle Enter para fechar esta janela." _
  exit 1
fi
# O agente do kit (agente em .root/cliente.json) decide a entrada: com a página guiada
# (ferramentas/onboarding.py, só no kit com agente claude) ou direto pelo instalador de terminal.
AGENTE="$(KIT_DIR="$DIR/.." /usr/bin/python3 -c "import json,os;print(json.load(open(os.path.join(os.environ['KIT_DIR'],'.root','cliente.json'))).get('agente') or 'claude')" 2>/dev/null || echo claude)"
if [ "$AGENTE" = "claude" ] && [ -f "$DIR/../ferramentas/onboarding.py" ]; then
  exec /usr/bin/python3 "$DIR/../ferramentas/onboarding.py"
fi
bash "$DIR/instalar.sh"
read -r -p "Tecle Enter para fechar esta janela." _
