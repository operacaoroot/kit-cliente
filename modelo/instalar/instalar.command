#!/bin/bash
# Clique duas vezes neste arquivo para instalar o kit no Mac.
DIR="$(cd "$(dirname "$0")" && pwd)"
bash "$DIR/instalar.sh"
echo
read -r -p "Pronto. Tecle Enter para fechar esta janela." _
