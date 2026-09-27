#!/usr/bin/env python3
"""Responde um pedido de ajuda direto no repositório do kit do cliente.

Uso:
    python3 acompanhador/responder.py <slug> ajuda/AAAA-MM-DD-HHMM.md "texto da resposta" --por "Nome do sócio"

Grava a resposta no fim do arquivo do pedido, troca `estado: aberto` por
`estado: respondido` e faz o commit pelo GitHub. O cliente vê a resposta quando
fechar o dia (o Claude do kit mostra antes de qualquer outra coisa). A resposta
também deve ir pelo canal combinado: esta ferramenta registra, não avisa.
"""
import base64
import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
from montar import api  # noqa: E402


def main(argv):
    if len(argv) < 4 or "--por" not in argv:
        print(__doc__)
        return 2
    slug, caminho, texto = argv[1], argv[2], argv[3]
    por = argv[argv.index("--por") + 1]
    m = json.loads((RAIZ / "manifestos" / "{}.json".format(slug)).read_text(encoding="utf-8"))
    if not m.get("entrega", {}).get("publicado"):
        print("Kit não publicado no GitHub; responda no arquivo local:", m.get("entrega", {}).get("local"))
        return 1
    dono, repo = m["entrega"]["repo"].split("/")
    status, f = api("GET", "/repos/{}/{}/contents/{}".format(dono, repo, caminho))
    if status != 200:
        print("Pedido não encontrado:", status)
        return 1
    atual = base64.b64decode(f["content"]).decode()
    if "estado: aberto" not in atual:
        print("Esse pedido não está aberto.")
        return 1
    quando = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    novo = atual.replace("estado: aberto", "estado: respondido", 1).rstrip() + \
        "\n\n## Resposta da Root ({}, {})\n\n{}\n".format(por, quando, texto)
    status, corpo = api("PUT", "/repos/{}/{}/contents/{}".format(dono, repo, caminho), {
        "message": "Root respondeu: {}".format(caminho), "content": base64.b64encode(novo.encode()).decode(), "sha": f["sha"]})
    print("Resposta gravada." if status in (200, 201) else "Falhou: {} {}".format(status, corpo.get("message")))
    return 0 if status in (200, 201) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
