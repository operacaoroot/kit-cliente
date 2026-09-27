#!/usr/bin/env python3
"""Pontua os sinais marcados na ata do kickoff e propõe um dos três perfis.

Uso:
    python3 perfis/pontuar.py manifestos/<cliente>.json
    python3 perfis/pontuar.py manifestos/<cliente>.json --gravar

Os sinais vêm do manifesto, em `perfil.sinais`: uma lista de objetos
{"id": "...", "minuto": "00:12:40", "trecho": "..."}. Quem marca é o leitor de
ata ou o sócio que conduziu o kickoff. Todo sinal precisa de minuto e trecho:
sinal sem prova é descartado com aviso.

Com --gravar, o resultado entra em `perfil.proposto` do manifesto. A escolha
final continua sendo do sócio, em `perfil.escolhido` e `perfil.conferido_por`.
Só biblioteca padrão, compatível com Python 3.9.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def carregar_perfis():
    return json.loads((RAIZ / "perfis" / "perfis.json").read_text(encoding="utf-8"))


def pontuar(sinais_marcados, perfis):
    catalogo = {s["id"]: s for s in perfis["sinais"]}
    nomes = list(perfis["perfis"].keys())
    soma = {p: 0 for p in nomes}
    aceitos, descartados = [], []
    vistos = set()
    for s in sinais_marcados:
        sid = s.get("id")
        if sid not in catalogo:
            descartados.append((sid, "sinal fora do catálogo de perfis.json"))
            continue
        if not s.get("minuto") or not s.get("trecho"):
            descartados.append((sid, "sem minuto ou trecho da ata"))
            continue
        if sid in vistos:
            descartados.append((sid, "repetido (cada sinal conta uma vez)"))
            continue
        vistos.add(sid)
        aceitos.append(s)
        for p in nomes:
            soma[p] += catalogo[sid]["pesos"].get(p, 0)

    total = sum(soma.values())
    if total == 0:
        porcentagem = {p: 0 for p in nomes}
    else:
        porcentagem = {p: round(100 * soma[p] / total) for p in nomes}
    ordem = sorted(nomes, key=lambda p: porcentagem[p], reverse=True)
    primeiro, segundo = ordem[0], ordem[1]
    lim = perfis["limiares"]
    distancia = porcentagem[primeiro] - porcentagem[segundo]
    if total == 0 or porcentagem[primeiro] < lim["confianca_minima"] or distancia < lim["distancia_minima"]:
        decisao = "socio-decide"
    else:
        decisao = "socio-confere"
    return {
        "perfil": primeiro if total else None,
        "porcentagem": porcentagem,
        "distancia": distancia,
        "decisao": decisao,
        "sinais_aceitos": [s["id"] for s in aceitos],
        "sinais_descartados": [{"id": d[0], "motivo": d[1]} for d in descartados],
        "versao_dos_pesos": perfis["versao"],
    }


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    caminho = Path(argv[1])
    manifesto = json.loads(caminho.read_text(encoding="utf-8"))
    perfis = carregar_perfis()
    resultado = pontuar(manifesto.get("perfil", {}).get("sinais", []), perfis)

    print("Pontuação do perfil de", manifesto.get("cliente", {}).get("nome", "?"))
    for p, v in sorted(resultado["porcentagem"].items(), key=lambda x: -x[1]):
        print("  {:<12} {:>3}%".format(perfis["perfis"][p]["nome"], v))
    if resultado["perfil"]:
        print("Proposta:", perfis["perfis"][resultado["perfil"]]["nome"])
    print("Distância para o segundo:", resultado["distancia"], "pontos")
    if resultado["decisao"] == "socio-decide":
        print("RESULTADO: sócio decide (pontuação sem confiança suficiente).")
    else:
        print("RESULTADO: sócio confere e assina.")
    for d in resultado["sinais_descartados"]:
        print("  aviso: sinal '{}' descartado: {}".format(d["id"], d["motivo"]))

    if "--gravar" in argv:
        manifesto.setdefault("perfil", {})["proposto"] = resultado
        caminho.write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("Gravado em perfil.proposto de", caminho)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
