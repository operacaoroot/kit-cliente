#!/bin/bash
# Validação REAL da versão Codex do kit, neste Mac, sem mock (critérios C11 e C12 de docs/KIT-CODEX.md).
#
# O que acontece, numa pasta descartável com HOME próprio (nada entra no HOME de quem roda):
#   1. sobe um servidor MCP de verdade: o servidor.py do módulo mcp do kit-instalacao-vps (FastMCP,
#      Bearer por pessoa, perfil leitura), com um token de teste e uma base de 1 nota;
#   2. monta o kit a partir de um manifesto FICTÍCIO (manifestos/exemplo-codex-helena-prado.json),
#      apontando o mcp.url para esse servidor, com --zip;
#   3. prova o contrato HTTP com curl: sem token 401; com token, aceito;
#   4. roda o instalador do kit (instalar/instalar.sh) com HOME vazio: instala de verdade o Codex CLI
#      e o resto do catálogo nesse HOME, registra o servidor por `codex mcp add` e cria o atalho;
#   5. confere no HOME descartável: `codex mcp get`, o config.toml só com o NOME da variável,
#      `ferramentas/mcp.py --conferir` e `--testar`;
#   6. (opcional, usa a conta do Codex de quem roda) `codex exec` faz uma chamada de leitura ao
#      servidor pelo MCP; o rastro logs/mcp/uso.jsonl tem de mostrar o rótulo da pessoa. O registro
#      é temporário: `codex mcp remove` e o ~/.codex/config.toml volta do backup, byte a byte.
#
# Uso:  bash testes/validar_codex_real.sh [--sem-instalador] [--sem-exec] [--manter]
# Pré-requisitos: uv, curl, git, rede; para a etapa 6, o codex logado no HOME de quem roda.
# Variáveis: KIT_VPS (padrão ~/dev/kit-instalacao-vps), PORTA_MCP (padrão 8765).
set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
KIT_VPS="${KIT_VPS:-$HOME/dev/kit-instalacao-vps}"
PORTA="${PORTA_MCP:-8765}"
SEM_INSTALADOR=0; SEM_EXEC=0; MANTER=0
for a in "$@"; do case "$a" in --sem-instalador) SEM_INSTALADOR=1;; --sem-exec) SEM_EXEC=1;; --manter) MANTER=1;; esac; done

T="$(mktemp -d /tmp/validacao-codex-XXXXXX)"
EVID="$T/evidencia.md"
HOME_TESTE="$T/home"
TOKEN="tk-$(openssl rand -hex 16)"
ROTULO="helena-teste"
NOME_REAL="validacao-kit-$(openssl rand -hex 3)"
PID_MCP=""
BACKUP_CFG=""
passo() { printf '\n== %s\n' "$1"; printf '\n## %s\n\n' "$1" >> "$EVID"; }
ev() { printf '%s\n' "$1"; printf -- '- %s\n' "$1" >> "$EVID"; }
limpar() {
  [ -n "$PID_MCP" ] && kill "$PID_MCP" 2>/dev/null
  if [ -n "$BACKUP_CFG" ] && [ -f "$BACKUP_CFG" ]; then
    codex mcp remove "$NOME_REAL" >/dev/null 2>&1 || true
    cp "$BACKUP_CFG" "$HOME/.codex/config.toml"
    if cmp -s "$BACKUP_CFG" "$HOME/.codex/config.toml"; then ev "config.toml de quem roda restaurado do backup (igual byte a byte)"; fi
  fi
  if [ "$MANTER" = 1 ]; then echo "pasta mantida: $T"; else echo "evidência em $EVID (a pasta some ao fechar; copie antes)"; fi
}
trap limpar EXIT
printf '# Validação real do kit Codex\n\nData: %s · máquina: %s · codex de quem roda: %s\n' "$(date '+%Y-%m-%d %H:%M %z')" "$(uname -sm)" "$(codex --version 2>/dev/null || echo 'não instalado')" > "$EVID"

passo "1. Servidor MCP real (módulo mcp do kit-instalacao-vps)"
[ -f "$KIT_VPS/modulos/mcp/servidor.py" ] || { echo "não achei $KIT_VPS/modulos/mcp/servidor.py (defina KIT_VPS)"; exit 1; }
mkdir -p "$T/mcp/base/40-Operacao" "$T/mcp/logs" "$T/mcp/trabalho" "$HOME_TESTE"
cp "$KIT_VPS"/modulos/mcp/{servidor.py,perfis.py,tools_casa.py,requirements.txt} "$T/mcp/"
printf -- '---\nkind: fato\n---\n\n# Nota de teste da base\n\nConsultoria ambiental fictícia. Palavra-chave: ABACAXI-TESTE.\n' > "$T/mcp/base/40-Operacao/Nota de teste.md"
( cd "$T/mcp" && uv venv -q --python 3.12 .venv && uv pip install -q --python .venv/bin/python -r requirements.txt ) || { echo "não consegui preparar o servidor"; exit 1; }
( cd "$T/mcp" && MCP_PERFIL=leitura MCP_HOST=127.0.0.1 MCP_PORT="$PORTA" BASE_DIR="$T/mcp/base" LOG_DIR="$T/mcp/logs" TRABALHO_DIR="$T/mcp/trabalho" \
  MCP_TOKENS="$ROTULO:$TOKEN" MCP_NOME=exemplo-os .venv/bin/python servidor.py --http > "$T/mcp/servidor.log" 2>&1 ) &
PID_MCP=$!
for i in $(seq 1 30); do curl -s -o /dev/null "http://127.0.0.1:$PORTA/mcp" && break; sleep 1; done
ev "servidor.py --http no ar em 127.0.0.1:$PORTA, perfil leitura, 1 token (rótulo $ROTULO), mcp==$(grep -o 'mcp==[0-9.]*' "$T/mcp/requirements.txt" | cut -d= -f3)"

passo "2. Montar o kit do manifesto fictício, com --zip"
python3 - "$RAIZ" "$T" "$PORTA" <<'PY'
import json, sys
from pathlib import Path
raiz, t, porta = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.path.insert(0, str(raiz / "montador"))
import montar
m = json.loads((raiz / "manifestos" / "exemplo-codex-helena-prado.json").read_text(encoding="utf-8"))
m["cliente"]["slug"] = "validacao-codex"
m["mcp"]["url"] = "http://127.0.0.1:{}/mcp".format(porta)
m.pop("entrega", None)
(t / "manifesto.json").write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
montar.SAIDA = t / "saida"
montar.montar(str(t / "manifesto.json"), {"--zip", "--permitir-semente"})
PY
KIT="$T/saida/validacao-codex"
[ -d "$KIT" ] || { echo "o kit não foi montado"; exit 1; }
ev "kit montado em $KIT; zip: $(du -h "$T/saida/validacao-codex.zip" | cut -f1)"
ev "agente no cliente.json: $(python3 -c "import json;c=json.load(open('$KIT/.root/cliente.json'));print(c['agente'], '· mcp:', c['mcp']['nome'], c['mcp']['url'], c['mcp']['perfil'], c['mcp']['variavel'])")"
ev "nada do Claude no kit: $(find "$KIT" -path "$KIT/.git" -prune -o \( -name 'CLAUDE.md' -o -name '.claude' -o -name 'autonomia.py' \) -print | wc -l | tr -d ' ') arquivo(s) achado(s) (esperado 0)"
ev "skills em .agents/skills: $(ls "$KIT/.agents/skills" | tr '\n' ' ')"

passo "3. Contrato HTTP com curl"
SEM="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORTA/mcp")"
COM="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $TOKEN" -H 'Accept: application/json, text/event-stream' "http://127.0.0.1:$PORTA/mcp")"
ERRADO="$(curl -s -o /dev/null -w '%{http_code}' -H "Authorization: Bearer nao-e-o-token" "http://127.0.0.1:$PORTA/mcp")"
ev "sem token: HTTP $SEM (esperado 401) · com token: HTTP $COM (esperado diferente de 401/403) · token errado: HTTP $ERRADO (esperado 401)"
[ "$SEM" = 401 ] && [ "$ERRADO" = 401 ] && [ "$COM" != 401 ] && [ "$COM" != 403 ] && ev "contrato: OK" || ev "contrato: FALHOU"

if [ "$SEM_INSTALADOR" = 0 ]; then
  passo "4. Instalador com HOME vazio (instala o Codex CLI de verdade nesse HOME)"
  INICIO=$(date +%s)
  env -i HOME="$HOME_TESTE" PATH=/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm LANG=pt_BR.UTF-8 KIT_MCP_TOKEN="$TOKEN" \
    bash "$KIT/instalar/instalar.sh" > "$T/instalador.log" 2>&1
  RC=$?
  ev "instalar.sh terminou com código $RC em $(( $(date +%s) - INICIO )) s (log: instalador.log, $(wc -l < "$T/instalador.log" | tr -d ' ') linhas)"
  grep -E '^\s*(ok|!!)\s' "$T/instalador.log" | sed 's/^ *//' | while read -r l; do ev "instalador: $l"; done
  ev "codex no HOME de teste: $("$HOME_TESTE/.local/bin/codex" --version 2>/dev/null || echo 'NÃO instalado')"
  ev "atalho: $(ls "$HOME_TESTE/Desktop/" 2>/dev/null | tr '\n' ' ')"
  ev "conteúdo do atalho: $(tr '\n' ' | ' < "$HOME_TESTE/Desktop/Codex do kit.command" 2>/dev/null)"

  passo "5. No HOME de teste: o Codex enxerga o servidor"
  ev "codex mcp get: $(env HOME="$HOME_TESTE" PATH="$HOME_TESTE/.local/bin:/usr/bin:/bin" "$HOME_TESTE/.local/bin/codex" mcp get exemplo-os 2>&1 | tr '\n' ' ')"
  ev "config.toml do HOME de teste: $(grep -A4 'mcp_servers.exemplo-os' "$HOME_TESTE/.codex/config.toml" 2>/dev/null | tr '\n' ' ')"
  if grep -q "$TOKEN" "$HOME_TESTE/.codex/config.toml" 2>/dev/null; then ev "TOKEN VAZOU no config.toml"; else ev "token NÃO está no config.toml (só o nome da variável)"; fi
  ev "mcp.env: permissão $(stat -f '%Lp' "$KIT/.root/mcp.env") · git ls-files: $(cd "$KIT" && git add -A >/dev/null 2>&1; git ls-files | grep -c 'mcp.env' || true) arquivo(s) mcp.env versionado(s) (esperado 0)"
  ev "mcp.py --conferir: $(env HOME="$HOME_TESTE" PATH=/usr/bin:/bin /usr/bin/python3 "$KIT/ferramentas/mcp.py" --conferir --json | tr -d '\n ' )"
  ev "mcp.py --testar: $(env HOME="$HOME_TESTE" PATH=/usr/bin:/bin /usr/bin/python3 "$KIT/ferramentas/mcp.py" --testar | tr '\n' ' ')"
  ev "verificar.py --sem-rede: $(env HOME="$HOME_TESTE" PATH="$HOME_TESTE/.local/bin:/usr/bin:/bin" /usr/bin/python3 "$KIT/ferramentas/verificar.py" --sem-rede | grep -E 'instalar|Passo atual' | tr '\n' ' ')"
fi

if [ "$SEM_EXEC" = 0 ]; then
  passo "6. Chamada de leitura pelo Codex de quem roda (codex exec), registro temporário"
  command -v codex >/dev/null 2>&1 || { ev "codex não está no PATH de quem roda; etapa pulada"; exit 0; }
  BACKUP_CFG="$T/config.toml.antes"
  cp "$HOME/.codex/config.toml" "$BACKUP_CFG"
  codex mcp add "$NOME_REAL" --url "http://127.0.0.1:$PORTA/mcp" --bearer-token-env-var EXEMPLO_OS_MCP_TOKEN >/dev/null 2>&1
  ev "registrado como $NOME_REAL: $(codex mcp get "$NOME_REAL" 2>&1 | tr '\n' ' ')"
  INICIO=$(date +%s)
  EXEMPLO_OS_MCP_TOKEN="$TOKEN" codex exec -C "$KIT" --sandbox read-only --skip-git-repo-check \
    "Chame a ferramenta base_buscar do servidor MCP $NOME_REAL com termo=ABACAXI e depois a ferramenta status do mesmo servidor. Responda somente com os dois JSON devolvidos, sem comentário." \
    > "$T/codex-exec.log" 2>&1
  RC=$?
  ev "codex exec terminou com código $RC em $(( $(date +%s) - INICIO )) s"
  ev "resposta: $(tail -c 1200 "$T/codex-exec.log" | tr '\n' ' ')"
  ev "rastro uso.jsonl: $(cat "$T/mcp/logs/uso.jsonl" 2>/dev/null | tr '\n' ' ')"
  if grep -q "\"quem\": \"$ROTULO\"" "$T/mcp/logs/uso.jsonl" 2>/dev/null; then ev "rastro com o rótulo da pessoa ($ROTULO): OK"; else ev "rastro SEM o rótulo da pessoa: FALHOU"; fi
fi
echo; echo "===== evidência ====="; cat "$EVID"
