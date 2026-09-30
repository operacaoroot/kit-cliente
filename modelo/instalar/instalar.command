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
exec /usr/bin/python3 "$DIR/../ferramentas/onboarding.py"
