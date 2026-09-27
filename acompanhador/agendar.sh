#!/bin/bash
# Agenda o acompanhador no Mac às 08:30, 13:00 e 18:00 (launchd).
# Uso: bash acompanhador/agendar.sh         (liga)
#      bash acompanhador/agendar.sh --tirar (desliga)
# Se o Mac estiver dormindo no horário, o launchd roda quando ele acordar.
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
ROTULO="com.operacaoroot.kit-acompanhador"
PLIST="$HOME/Library/LaunchAgents/$ROTULO.plist"
if [ "${1:-}" = "--tirar" ]; then
  launchctl bootout "gui/$(id -u)/$ROTULO" 2>/dev/null || true
  rm -f "$PLIST"; echo "acompanhador desligado"; exit 0
fi
mkdir -p "$HOME/Library/LaunchAgents" "$RAIZ/acompanhador/saida"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$ROTULO</string>
  <key>ProgramArguments</key><array>
    <string>/usr/bin/python3</string><string>$RAIZ/acompanhador/acompanhar.py</string>
  </array>
  <key>WorkingDirectory</key><string>$RAIZ</string>
  <key>StartCalendarInterval</key><array>
    <dict><key>Hour</key><integer>8</integer><key>Minute</key><integer>30</integer></dict>
    <dict><key>Hour</key><integer>13</integer><key>Minute</key><integer>0</integer></dict>
    <dict><key>Hour</key><integer>18</integer><key>Minute</key><integer>0</integer></dict>
  </array>
  <key>StandardOutPath</key><string>$RAIZ/acompanhador/saida/launchd.log</string>
  <key>StandardErrorPath</key><string>$RAIZ/acompanhador/saida/launchd.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$ROTULO" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "acompanhador agendado (08:30, 13:00, 18:00). Relatórios em $RAIZ/acompanhador/saida/"
