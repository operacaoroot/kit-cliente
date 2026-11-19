#!/bin/bash
# Validação REAL da versão Codex do kit, neste Mac, sem mock (critérios C11 e C12 de docs/KIT-CODEX.md).
#
# O que acontece, numa pasta descartável com HOME próprio (nada entra no HOME de quem roda):
#   1. sobe um servidor MCP de verdade: o servidor.py do módulo mcp do kit-instalacao-vps (FastMCP,
#      Bearer por pessoa, perfil leitura), com um token de teste e uma base de 1 nota;
#   2. monta o kit a partir de um manifesto FICTÍCIO (manifestos/exemplo-codex-helena-prado.json),
#      apontando o mcp.url para esse servidor, com --zip;
#   3. prova initialize do MCP: sem token 401; com token, resposta MCP válida;
#   4. roda o instalador do kit (instalar/instalar.sh) com HOME vazio: instala de verdade o Codex CLI
#      e o resto do catálogo nesse HOME, registra o servidor por `codex mcp add` e cria o atalho;
#   5. confere no HOME descartável: `codex mcp get`, o config.toml só com o NOME da variável,
#      `ferramentas/mcp.py --conferir` e `--testar`;
#   6. (opcional, usa a conta do Codex de quem roda) `codex exec` faz uma chamada de leitura ao
#      servidor pelo MCP; o rastro logs/mcp/uso.jsonl tem de mostrar o rótulo da pessoa. O registro
#      fica só no HOME de teste. Uma cópia temporária da autenticação existente é apagada ao sair.
#
# Uso:  bash testes/validar_codex_real.sh [--sem-instalador] [--sem-exec] [--manter] [--aprovar-leituras-laboratorio]
# Pré-requisitos: uv, curl, git, rede; para a etapa 6, o codex logado no HOME de quem roda.
# Variáveis: KIT_VPS (padrão ~/dev/kit-instalacao-vps), PORTA_MCP (8765), INSTALAR_SO (ids do catálogo).
# KIT_REPO_TESTE=operacaoroot/kit-exemplo-marina-duarte usa uma chave temporária somente leitura, removida ao sair.
set -u
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
KIT_VPS="${KIT_VPS:-$HOME/dev/kit-instalacao-vps}"
PORTA="${PORTA_MCP:-8765}"
SEM_INSTALADOR=0; SEM_EXEC=0; MANTER=0; APROVAR_LEITURAS=0
for a in "$@"; do case "$a" in --sem-instalador) SEM_INSTALADOR=1;; --sem-exec) SEM_EXEC=1;; --manter) MANTER=1;; --aprovar-leituras-laboratorio) APROVAR_LEITURAS=1;; esac; done

T="$(mktemp -d /tmp/validacao-codex-XXXXXX)"
EVID="$T/evidencia.md"
HOME_TESTE="$T/home"
TOKEN="tk-$(openssl rand -hex 16)"
ROTULO="helena-teste"
NOME_REAL="validacao-kit-$(openssl rand -hex 3)"
PID_MCP=""
CHAVE_GITHUB_ID=""
REPO_TESTE="${KIT_REPO_TESTE:-}"
case "$REPO_TESTE" in ""|operacaoroot/kit-exemplo-marina-duarte) ;; *) echo "KIT_REPO_TESTE deve ser o repositório fictício autorizado"; exit 2;; esac
CODEX_ORIGINAL="$(command -v codex || true)"
passo() { printf '\n== %s\n' "$1"; printf '\n## %s\n\n' "$1" >> "$EVID"; }
ev() { printf '%s\n' "$1"; printf -- '- %s\n' "$1" >> "$EVID"; }
limpar() {
  RC_FINAL=$?
  [ -n "$PID_MCP" ] && kill "$PID_MCP" 2>/dev/null
  if ! rm -f "$HOME_TESTE/.codex/auth.json" || [ -f "$HOME_TESTE/.codex/auth.json" ]; then
    ev "FALHOU: remoção da autenticação temporária"
    RC_FINAL=1
  fi
  if [ -n "$CHAVE_GITHUB_ID" ]; then
    if gh api --method DELETE "repos/$REPO_TESTE/keys/$CHAVE_GITHUB_ID" >/dev/null 2>&1; then
      ev "chave de deploy temporária removida do repositório fictício"
    else
      ev "FALHOU: remoção da chave temporária $CHAVE_GITHUB_ID pendente em $REPO_TESTE"
      RC_FINAL=1
    fi
  fi
  if [ "$MANTER" = 1 ]; then echo "pasta mantida: $T"; else echo "evidência em $EVID; remova a pasta de laboratório após arquivar o relatório"; fi
  exit "$RC_FINAL"
}
trap limpar EXIT
trap 'exit 130' INT TERM
falhar() { ev "FALHOU: $1"; exit 1; }
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
if [ -n "$REPO_TESTE" ]; then
  [ "$(gh api user --jq .login)" = operacaoroot ] || falhar "GitHub precisa da conta operacaoroot"
  python3 - "$KIT" "$REPO_TESTE" "$T" <<'PYREPO'
import json, shutil, sys
from pathlib import Path
kit, repo, t = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
c = kit / ".root/cliente.json"
d = json.loads(c.read_text()); d["repo"] = repo; c.write_text(json.dumps(d, ensure_ascii=False, indent=2))
(t / "deploy-key.json").write_text(json.dumps({"title": "validacao-codex-descartavel-" + t.name,
    "key": (kit / ".root/chave.pub").read_text(), "read_only": True}))
shutil.make_archive(str(t / "saida/validacao-codex"), "zip", root_dir=str(t / "saida"), base_dir="validacao-codex")
PYREPO
  CHAVE_GITHUB_ID="$(gh api --method POST "repos/$REPO_TESTE/keys" --input "$T/deploy-key.json" --jq .id)" || falhar "cadastro da chave de leitura falhou"
  ev "repositório fictício $REPO_TESTE, chave de deploy temporária somente leitura"
fi
ev "kit montado em $KIT; zip: $(du -h "$T/saida/validacao-codex.zip" | cut -f1)"
ev "agente no cliente.json: $(python3 -c "import json;c=json.load(open('$KIT/.root/cliente.json'));print(c['agente'], '· mcp:', c['mcp']['nome'], c['mcp']['url'], c['mcp']['perfil'], c['mcp']['variavel'])")"
ev "nada do Claude no kit: $(find "$KIT" -path "$KIT/.git" -prune -o \( -name 'CLAUDE.md' -o -name '.claude' -o -name 'autonomia.py' \) -print | wc -l | tr -d ' ') arquivo(s) achado(s) (esperado 0)"
ev "skills em .agents/skills: $(ls "$KIT/.agents/skills" | tr '\n' ' ')"

passo "3. Contrato MCP initialize"
# Só token de laboratório. A rotina do kit exige initialize válido, não apenas HTTP diferente de 401.
KIT_MCP_TOKEN="$TOKEN" python3 - "$KIT" <<'PYMCP'
import os, sys
sys.path.insert(0, sys.argv[1] + "/ferramentas")
import mcp
mcp.gravar_token(mcp.configuracao()["variavel"], os.environ["KIT_MCP_TOKEN"])
PYMCP
python3 "$KIT/ferramentas/mcp.py" --testar >> "$EVID" 2>&1 || falhar "contrato MCP não passou"
ev "initialize válido; sem token, HTTP 401"
ERRADO="$(curl --max-time 10 -s -o /dev/null -w '%{http_code}' -H 'Authorization: Bearer nao-e-o-token' "http://127.0.0.1:$PORTA/mcp")"
[ "$ERRADO" = 401 ] || falhar "token errado não foi recusado"
ev "token errado: HTTP 401"

if [ "$SEM_INSTALADOR" = 0 ]; then
  passo "4. Instalador com HOME vazio (instala o Codex CLI de verdade nesse HOME)"
  INICIO=$(date +%s)
  env -i HOME="$HOME_TESTE" PATH=/usr/bin:/bin:/usr/sbin:/sbin TERM=xterm LANG=pt_BR.UTF-8 KIT_MCP_TOKEN="$TOKEN" \
    bash "$KIT/instalar/instalar.sh" ${INSTALAR_SO:+--so "$INSTALAR_SO"} > "$T/instalador.log" 2>&1
  RC=$?
  [ "$RC" = 0 ] || falhar "instalador terminou com código $RC; veja instalador.log"
  ev "instalar.sh terminou com código $RC em $(( $(date +%s) - INICIO )) s (log: instalador.log, $(wc -l < "$T/instalador.log" | tr -d ' ') linhas)"
  grep -E '^\s*(ok|!!)\s' "$T/instalador.log" | sed 's/^ *//' | while read -r l; do ev "instalador: $l"; done
  [ -x "$HOME_TESTE/.local/bin/codex" ] || falhar "Codex não foi instalado"
  ev "codex no HOME de teste: $("$HOME_TESTE/.local/bin/codex" --version 2>/dev/null || echo 'NÃO instalado')"
  ev "atalho: $(ls "$HOME_TESTE/Desktop/" 2>/dev/null | tr '\n' ' ')"
  ev "conteúdo do atalho: $(tr '\n' ' | ' < "$HOME_TESTE/Desktop/Codex do kit.command" 2>/dev/null)"

  passo "5. No HOME de teste: o Codex enxerga o servidor"
  ev "codex mcp get: $(env -i HOME="$HOME_TESTE" PATH="$HOME_TESTE/.local/bin:/usr/bin:/bin" "$HOME_TESTE/.local/bin/codex" mcp get exemplo-os 2>&1 | tr '\n' ' ')"
  ev "config.toml do HOME de teste: $(grep -A4 'mcp_servers.exemplo-os' "$HOME_TESTE/.codex/config.toml" 2>/dev/null | tr '\n' ' ')"
  if grep -q "$TOKEN" "$HOME_TESTE/.codex/config.toml" 2>/dev/null; then falhar "TOKEN VAZOU no config.toml"; else ev "token NÃO está no config.toml (só o nome da variável)"; fi
  ev "mcp.env: permissão $(stat -f '%Lp' "$KIT/.root/mcp.env") · git ls-files: $(cd "$KIT" && git add -A >/dev/null 2>&1; git ls-files | grep -c 'mcp.env' || true) arquivo(s) mcp.env versionado(s) (esperado 0)"
  env -i HOME="$HOME_TESTE" PATH="$HOME_TESTE/.local/bin:/usr/bin:/bin" /usr/bin/python3 "$KIT/ferramentas/mcp.py" --conferir --json >/dev/null || falhar "MCP não está registrado corretamente"
  ev "mcp.py --conferir: $(env -i HOME="$HOME_TESTE" PATH=/usr/bin:/bin /usr/bin/python3 "$KIT/ferramentas/mcp.py" --conferir --json | tr -d '\n ' )"
  ev "mcp.py --testar: $(env -i HOME="$HOME_TESTE" PATH=/usr/bin:/bin /usr/bin/python3 "$KIT/ferramentas/mcp.py" --testar | tr '\n' ' ')"
  ev "verificar.py --sem-rede: $(env -i HOME="$HOME_TESTE" PATH="$HOME_TESTE/.local/bin:/usr/bin:/bin" /usr/bin/python3 "$KIT/ferramentas/verificar.py" --sem-rede | grep -E 'instalar|Passo atual' | tr '\n' ' ')"
fi

if [ "$SEM_EXEC" = 0 ]; then
  passo "6. Primeiro uso pelo Codex real, com configuração isolada"
  [ -n "$CODEX_ORIGINAL" ] || falhar "Codex não está disponível para executar C12"
  [ -f "$HOME/.codex/auth.json" ] || falhar "não há autenticação local do Codex para C12"
  mkdir -p "$HOME_TESTE/.codex"
  chmod 700 "$HOME_TESTE/.codex"
  cp "$HOME/.codex/auth.json" "$HOME_TESTE/.codex/auth.json"
  chmod 600 "$HOME_TESTE/.codex/auth.json"
  CODEX_TESTE="$HOME_TESTE/.local/bin/codex"
  [ -x "$CODEX_TESTE" ] || CODEX_TESTE="$CODEX_ORIGINAL"
  env -i HOME="$HOME_TESTE" PATH="$HOME_TESTE/.local/bin:/usr/bin:/bin" "$CODEX_TESTE" mcp add "$NOME_REAL" --url "http://127.0.0.1:$PORTA/mcp" --bearer-token-env-var EXEMPLO_OS_MCP_TOKEN >/dev/null || falhar "registro isolado falhou"
  [ "$APROVAR_LEITURAS" = 0 ] || ev "aprovação específica de laboratório: somente base_buscar e status; sandbox read-only"
  # Python aplica prazo de 180 s e não deixa codex exec indefinidamente em segundo plano.
  EXEMPLO_OS_MCP_TOKEN="$TOKEN" python3 - "$HOME_TESTE" "$CODEX_TESTE" "$KIT" "$NOME_REAL" "$T/codex-exec.log" "$APROVAR_LEITURAS" <<'PYEXEC'
import os, subprocess, sys
casa, codex, kit, nome, log, aprovar = sys.argv[1:]
resposta_final = log + ".resposta.json"
env = {"HOME": casa, "PATH": casa + "/.local/bin:/usr/bin:/bin", "LANG": "pt_BR.UTF-8",
       "EXEMPLO_OS_MCP_TOKEN": os.environ["EXEMPLO_OS_MCP_TOKEN"]}
pedido = "Chame base_buscar do MCP " + nome + " com termo=ABACAXI e depois status do mesmo servidor. Não use outras ferramentas. Responda somente um objeto JSON sem bloco Markdown com chaves base_buscar e status e seus resultados completos."
opcoes = []
if aprovar == "1":
    # Autorização só para estas duas leituras da base fictícia local. Sandbox permanece read-only.
    opcoes = ["-c", 'mcp_servers.' + nome + '.enabled_tools=["base_buscar","status"]',
              "-c", 'mcp_servers.' + nome + '.tools.base_buscar.approval_mode="approve"',
              "-c", 'mcp_servers.' + nome + '.tools.status.approval_mode="approve"']
try:
    with open(log, "w") as f:
        r = subprocess.run([codex, "--no-daemon", "exec", "-C", kit, "--sandbox", "read-only",
                            "--skip-git-repo-check", "--output-last-message", resposta_final] + opcoes + [pedido], env=env, stdin=subprocess.DEVNULL, stdout=f, stderr=subprocess.STDOUT, timeout=180)
    sys.exit(r.returncode)
except subprocess.TimeoutExpired:
    sys.exit(124)
PYEXEC
  RC=$?
  [ "$RC" = 0 ] || falhar "codex exec terminou com código $RC (C12 não validado)"
  python3 - "$T/mcp/logs/uso.jsonl" "$ROTULO" "$T/codex-exec.log.resposta.json" <<'PYLOG'
import json, sys
from pathlib import Path
p = Path(sys.argv[1]); rotulo = sys.argv[2]
linhas = [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
ferramentas = {r.get("tool") for r in linhas if r.get("quem") == rotulo and r.get("ok") is True and r.get("perfil") == "leitura"}
resposta = json.loads(Path(sys.argv[3]).read_text())
def resultado(nome):
    valor = resposta.get(nome, {})
    if not isinstance(valor, dict) or valor.get("isError") is True:
        return {}
    return valor.get("structuredContent", valor)
busca = resultado("base_buscar")
status = resultado("status")
conteudo_ok = (busca.get("total") == 1 and any("ABACAXI-TESTE" in r.get("trecho", "") for r in busca.get("achados", []))
               and status.get("perfil") == "leitura" and status.get("base", {}).get("notas") == 1)
sys.exit(0 if {"base_buscar", "status"} <= ferramentas and conteudo_ok else 1)
PYLOG
  [ "$?" = 0 ] || falhar "faltam chamadas válidas ou o conteúdo esperado na resposta"
  ev "codex exec terminou com código 0; base_buscar e status registrados com perfil leitura e rótulo $ROTULO"
  ev "resposta conferida: ABACAXI-TESTE encontrado, total=1 e status.base.notas=1"
  ev "configuração pessoal não foi alterada; autenticação temporária removida ao sair"
else
  ev "C12 não executado (--sem-exec); resultado parcial"
fi
[ "$SEM_INSTALADOR" = 0 ] || ev "C11 não executado (--sem-instalador); resultado parcial"
echo; cat "$EVID"
