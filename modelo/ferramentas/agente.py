#!/usr/bin/env python3
"""Qual agente trabalha neste kit (Claude ou Codex) e o que muda por causa disso.

Lido de .root/cliente.json (campo `agente`; ausente vale `claude`). As outras ferramentas
importam daqui o nome, o comando e a pasta das skills em vez de fixar ".claude".
Só biblioteca padrão, compatível com Python 3.9.
"""
import json
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent

AGENTES = {
    "claude": {"nome": "Claude", "comando": "claude", "raiz_skills": ".claude"},
    "codex": {"nome": "Codex", "comando": "codex", "raiz_skills": ".agents"},
}


def id_do_kit(kit=KIT):
    arq = Path(kit) / ".root" / "cliente.json"
    try:
        valor = json.loads(arq.read_text(encoding="utf-8")).get("agente")
    except (OSError, ValueError):
        valor = None
    return valor if valor in AGENTES else "claude"


ID = id_do_kit()
NOME = AGENTES[ID]["nome"]
COMANDO = AGENTES[ID]["comando"]
RAIZ_SKILLS = AGENTES[ID]["raiz_skills"]
PASTA_SKILLS = KIT / RAIZ_SKILLS / "skills"
