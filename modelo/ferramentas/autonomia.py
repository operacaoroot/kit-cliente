#!/usr/bin/env python3
"""Deixa o Claude deste computador trabalhar sem pedir permissão a cada passo.

Uso:
    python3 ferramentas/autonomia.py              # aplica
    python3 ferramentas/autonomia.py --conferir   # só mostra como está (sai 1 se falta algo)

O computador, a conta do Claude e o servidor são da pessoa. Este passo grava nas configurações
do Claude dela (~/.claude/settings.json):
- modo padrão sem pedido de permissão (bypassPermissions), sem o aviso de confirmação;
- nenhuma regra de bloqueio (deny, ask) nem trava que desliga esse modo.
Tudo o mais que estiver no arquivo fica como está. A versão anterior fica copiada ao lado,
como settings.json.antes-do-kit-AAAAMMDD-HHMMSS.

Política de máquina (managed-settings) vence o arquivo da pessoa. Se houver uma, o script
mostra onde está: tirar exige administrador do computador. Só biblioteca padrão.
"""
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path

TRAVAS = ("disableBypassPermissionsMode", "disableAutoMode")
POLITICAS = {
    "darwin": ["/Library/Application Support/ClaudeCode"],
    "linux": ["/etc/claude-code"],
    "win32": [os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "ClaudeCode"),
              os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "ClaudeCode")],
}


def arquivo_do_claude():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude")) / "settings.json"


def ler(arq):
    if not arq.exists():
        return {}
    texto = arq.read_text(encoding="utf-8-sig").strip()
    return json.loads(texto) if texto else {}


def liberado(cfg):
    """Devolve uma cópia de cfg com o Claude liberado. Não altera cfg."""
    novo = json.loads(json.dumps(cfg))
    perm = {k: v for k, v in (novo.get("permissions") or {}).items() if k not in TRAVAS + ("ask",)}
    perm["deny"] = []
    perm["defaultMode"] = "bypassPermissions"
    novo["permissions"] = perm
    novo["skipDangerousModePermissionPrompt"] = True
    for t in TRAVAS:
        novo.pop(t, None)
    return novo


def falta(cfg):
    perm = cfg.get("permissions") or {}
    itens = []
    if perm.get("defaultMode") != "bypassPermissions":
        itens.append("modo sem pedido de permissão")
    if perm.get("deny") or perm.get("ask"):
        itens.append("regras de bloqueio")
    if any(t in perm or t in cfg for t in TRAVAS):
        itens.append("trava do modo sem permissão")
    if not cfg.get("skipDangerousModePermissionPrompt"):
        itens.append("aviso de confirmação ainda ligado")
    return itens


def politicas_de_maquina():
    achadas = []
    for pasta in POLITICAS.get(sys.platform, []):
        for nome in ("managed-settings.json", "managed-settings.d"):
            p = Path(pasta) / nome
            if p.exists():
                achadas.append(str(p))
    return achadas


def gravar(arq, cfg):
    arq.parent.mkdir(parents=True, exist_ok=True)
    if arq.exists():
        copia = arq.with_name("settings.json.antes-do-kit-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
        shutil.copy2(arq, copia)
    tmp = arq.with_name(arq.name + ".tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, arq)


def avisar_politicas():
    achadas = politicas_de_maquina()
    if achadas:
        print("[atenção] este computador tem política de máquina do Claude, que vence a configuração da pessoa:")
        for p in achadas:
            print("  " + p)
        print("  Para liberar de vez, apague esses arquivos como administrador e abra o Claude de novo.")
    return achadas


def main(argv):
    arq = arquivo_do_claude()
    try:
        cfg = ler(arq)
    except (ValueError, OSError) as erro:
        print("[atenção] não consegui ler {}: {}. Nada foi alterado.".format(arq, erro))
        return 1
    if "--conferir" in argv:
        itens = falta(cfg)
        print("Claude liberado" if not itens else "Falta liberar: " + ", ".join(itens))
        achadas = avisar_politicas()
        return 1 if itens or achadas else 0
    novo = liberado(cfg)
    if novo != cfg:
        gravar(arq, novo)
        print("Claude liberado: trabalha sem pedir permissão. Feche e abra o Claude para valer.")
    else:
        print("Claude já estava liberado.")
    avisar_politicas()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
