#!/usr/bin/env python3
"""A oficina das ferramentas (skills) que a pessoa cria no próprio kit.

Uma ferramenta nova nasce em oficina/<nome>/, é testada com um caso real e só então é
promovida para a pasta de skills do agente do kit (.claude/skills no Claude, .agents/skills no
Codex), onde ele passa a usá-la sozinho. O catálogo
(catalogo.json, na raiz do kit) diz de onde veio cada ferramenta e em que estado está.

Uso (na pasta do kit; no Windows troque `python3` por `.venv/Scripts/python`):
    python3 ferramentas/skills.py listar
    python3 ferramentas/skills.py nova <nome> "<para que serve, em uma frase>"
    python3 ferramentas/skills.py nova <nome> "<para que serve>" --a-partir-de <outra>
    python3 ferramentas/skills.py melhorar <nome>      # traz uma ferramenta SUA de volta para a oficina
    python3 ferramentas/skills.py conferir <nome>      # o que falta para poder promover
    python3 ferramentas/skills.py promover <nome>
    python3 ferramentas/skills.py aposentar <nome>

As ferramentas da Root (origem root e frente) não se editam: a Root as atualiza e a
atualização sobrescreve. Para mudar o jeito de uma delas, crie a sua com --a-partir-de.
Nada é apagado: versão substituída ou aposentada vai para oficina/_aposentadas/.
Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agente  # noqa: E402  (mesma pasta; qual agente trabalha neste kit)

KIT = Path(__file__).resolve().parent.parent
CATALOGO = KIT / "catalogo.json"
OFICINA = KIT / "oficina"
ATIVAS = agente.PASTA_SKILLS
PASTA_ATIVAS = agente.RAIZ_SKILLS + "/skills"
APOSENTADAS = OFICINA / "_aposentadas"
NOME_VALIDO = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

SEGREDOS = [
    (re.compile(r"sk-[A-Za-z0-9_-]{16,}"), "chave de API"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._-]{16,}"), "token de acesso"),
    (re.compile(r"(?i)\b(senha|password|token|api[_-]?key)\b\s*[:=]\s*\S{6,}"), "senha ou token escrito"),
    (re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"), "CPF"),
    (re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b"), "CNPJ"),
]
CAMINHO_DA_MAQUINA = re.compile(r"(/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\\\?Users\\\\?[^\\\s]+)")

MODELO_SKILL = """---
name: {nome}
description: {resumo} Use quando a pessoa pedir <escreva aqui as frases que ela usa para pedir isso>.
---

# {titulo}

<!-- Escreva como você explicaria a tarefa para alguém novo na equipe. Apague os comentários no fim. -->

## Quando usar

<!-- Em que situação a ferramenta entra e em qual ela NÃO deve entrar. -->

## O que preciso receber

<!-- Os arquivos ou informações de entrada, e onde ficam (ex.: um PDF em entrada/). -->

## Como fazer

1. <!-- passo -->
2. <!-- passo -->
3. <!-- passo -->

## Como entregar

<!-- O formato do resultado e onde salvar (ex.: entregas/AAAA-MM-DD - nome.docx). Sempre rascunho. -->

## Regras

- Nunca invente número, nome, data ou valor: sem fonte, escreva [a confirmar].
- Tudo o que sai daqui é rascunho: a pessoa revisa antes de mandar para alguém.
- Não copie senha, token ou dado bancário para nenhum arquivo.
"""

MODELO_TESTES = """# Testes de {nome}

Cada teste usa um caso real, descrito sem dado sensível. A ferramenta só é promovida
quando o último teste diz `Resultado: aprovado`.

## Teste 1 · {hoje}

- Caso: <!-- o que foi testado, sem nome de cliente nem valor -->
- Pedido: <!-- a frase usada para chamar a ferramenta -->
- Resultado: <!-- aprovado ou reprovado -->
- O que ajustou: <!-- o que mudou no SKILL.md depois do teste -->
"""


class Erro(Exception):
    pass


def hoje():
    return dt.date.today().isoformat()


def ler_catalogo():
    if not CATALOGO.exists():
        return {"versao_catalogo": 1, "skills": []}
    return json.loads(CATALOGO.read_text(encoding="utf-8"))


def gravar_catalogo(cat):
    cat["skills"].sort(key=lambda s: ({"root": 0, "frente": 1, "cliente": 2}.get(s.get("origem"), 3), s["nome"]))
    CATALOGO.write_text(json.dumps(cat, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def entrada(cat, nome):
    return next((s for s in cat["skills"] if s["nome"] == nome), None)


def conferir_nome(nome):
    if not NOME_VALIDO.match(nome or ""):
        raise Erro("nome inválido: use minúsculas, números e hífen (ex.: resumo-de-reuniao)")


def cabecalho(texto):
    if not texto.startswith("---"):
        return {}
    fim = texto.find("\n---", 3)
    campos = {}
    for linha in texto[3:fim].splitlines():
        if ":" in linha:
            k, v = linha.split(":", 1)
            campos[k.strip()] = v.strip()
    return campos


def subir_versao(versao):
    partes = [int(x) for x in (versao or "0.0.0").split(".")]
    while len(partes) < 3:
        partes.append(0)
    return "{}.{}.0".format(partes[0], partes[1] + 1)


def guardar_aposentada(origem, nome, versao):
    APOSENTADAS.mkdir(parents=True, exist_ok=True)
    destino = APOSENTADAS / "{}-v{}-{}".format(nome, versao or "0", hoje())
    n = 2
    while destino.exists():
        destino = APOSENTADAS / "{}-v{}-{}-{}".format(nome, versao or "0", hoje(), n)
        n += 1
    shutil.move(str(origem), str(destino))
    return destino


# ---------------------------------------------------------------- comandos

def nova(nome, resumo, a_partir_de=None):
    conferir_nome(nome)
    if not resumo or len(resumo) < 20:
        raise Erro("descreva para que serve a ferramenta em uma frase (pelo menos 20 letras)")
    cat = ler_catalogo()
    if entrada(cat, nome) or (OFICINA / nome).exists() or (ATIVAS / nome).exists():
        raise Erro("já existe uma ferramenta chamada {}; escolha outro nome ou use melhorar".format(nome))
    pasta = OFICINA / nome
    pasta.mkdir(parents=True)
    if a_partir_de:
        base = ATIVAS / a_partir_de / "SKILL.md"
        if not base.exists():
            shutil.rmtree(pasta)
            raise Erro("não achei a ferramenta {} para usar de base".format(a_partir_de))
        texto = base.read_text(encoding="utf-8")
        texto = re.sub(r"(?m)^name:.*$", "name: " + nome, texto, count=1)
        texto = re.sub(r"(?m)^description:.*$", "description: " + resumo + " Use quando a pessoa pedir <frases>.", texto, count=1)
        texto = re.sub(r"\n*<!-- kit-[0-9a-f]+ -->\s*$", "\n", texto)
        (pasta / "SKILL.md").write_text(texto, encoding="utf-8")
    else:
        titulo = nome.replace("-", " ").capitalize()
        (pasta / "SKILL.md").write_text(MODELO_SKILL.format(nome=nome, resumo=resumo, titulo=titulo), encoding="utf-8")
    (pasta / "TESTES.md").write_text(MODELO_TESTES.format(nome=nome, hoje=hoje()), encoding="utf-8")
    cat["skills"].append({"nome": nome, "origem": "cliente", "estado": "homologacao", "versao": "0.1.0",
                          "resumo": resumo, "desde": hoje(), "base": a_partir_de})
    gravar_catalogo(cat)
    print("Criada na oficina: oficina/{}/ (SKILL.md e TESTES.md).".format(nome))
    print("Escreva o SKILL.md, teste com um caso real, registre no TESTES.md e rode: skills.py conferir {}".format(nome))


def melhorar(nome):
    cat = ler_catalogo()
    e = entrada(cat, nome)
    if not e or e.get("estado") != "ativa":
        raise Erro("{} não é uma ferramenta ativa".format(nome))
    if e.get("origem") != "cliente":
        raise Erro("{} é uma ferramenta da Root e a atualização da Root sobrescreve mudanças. "
                   "Crie a sua a partir dela: skills.py nova <nome> \"<para que>\" --a-partir-de {}".format(nome, nome))
    if (OFICINA / nome).exists():
        raise Erro("já existe um rascunho de {} na oficina".format(nome))
    shutil.copytree(str(ATIVAS / nome), str(OFICINA / nome))
    e["rascunho_na_oficina"] = True
    gravar_catalogo(cat)
    print("Cópia de trabalho em oficina/{}/. A versão ativa continua valendo até a promoção.".format(nome))


def problemas(nome):
    pasta = OFICINA / nome
    faltas = []
    skill = pasta / "SKILL.md"
    if not skill.exists():
        return ["não existe oficina/{}/SKILL.md".format(nome)]
    texto = skill.read_text(encoding="utf-8")
    cab = cabecalho(texto)
    if cab.get("name") != nome:
        faltas.append("o cabeçalho do SKILL.md precisa de name: {}".format(nome))
    desc = cab.get("description", "")
    if len(desc) < 40:
        faltas.append("a description do cabeçalho está curta demais para o {} saber quando usar".format(agente.NOME))
    if "<" in desc and ">" in desc:
        faltas.append("a description ainda tem texto de exemplo entre < >")
    if "<!--" in texto:
        faltas.append("o SKILL.md ainda tem comentários do modelo (<!-- ... -->) para preencher")
    corpo = texto.split("\n---", 2)[-1]
    if len(corpo.strip()) < 200:
        faltas.append("o SKILL.md tem pouco conteúdo: descreva os passos")
    todos = [skill] + [p for p in pasta.rglob("*") if p.is_file() and p != skill and p.suffix in (".md", ".py", ".txt", ".json")]
    for arq in todos:
        conteudo = arq.read_text(encoding="utf-8", errors="ignore")
        for padrao, tipo in SEGREDOS:
            if padrao.search(conteudo):
                faltas.append("{}: parece ter {} escrito; tire antes de promover".format(arq.relative_to(KIT).as_posix(), tipo))
        if CAMINHO_DA_MAQUINA.search(conteudo):
            faltas.append("{}: tem caminho desta máquina (pasta do usuário); use caminho relativo à pasta do kit".format(arq.relative_to(KIT).as_posix()))
    testes = pasta / "TESTES.md"
    if not testes.exists():
        faltas.append("falta o TESTES.md")
    else:
        resultados = re.findall(r"(?im)^\s*-\s*Resultado:\s*(aprovado|reprovado)\b", testes.read_text(encoding="utf-8"))
        if not resultados:
            faltas.append("nenhum teste registrado com Resultado: aprovado")
        elif resultados[-1].lower() != "aprovado":
            faltas.append("o último teste foi reprovado; ajuste e teste de novo")
    return faltas


def conferir(nome):
    conferir_nome(nome)
    faltas = problemas(nome)
    if faltas:
        print("Ainda não dá para promover {}:".format(nome))
        for f in faltas:
            print("  - " + f)
        return 1
    print("{} está pronta para promover.".format(nome))
    return 0


def promover(nome):
    conferir_nome(nome)
    faltas = problemas(nome)
    if faltas:
        raise Erro("não promovi {}:\n  - {}".format(nome, "\n  - ".join(faltas)))
    cat = ler_catalogo()
    e = entrada(cat, nome)
    if e and e.get("origem") != "cliente":
        raise Erro("{} é uma ferramenta da Root; não se promove por cima dela".format(nome))
    ativa = ATIVAS / nome
    if ativa.exists():
        guardar_aposentada(ativa, nome, (e or {}).get("versao"))
        versao = subir_versao((e or {}).get("versao"))
    else:
        versao = "1.0.0"
    ATIVAS.mkdir(parents=True, exist_ok=True)
    shutil.move(str(OFICINA / nome), str(ativa))
    if not e:
        e = {"nome": nome, "origem": "cliente", "resumo": cabecalho((ativa / "SKILL.md").read_text(encoding="utf-8")).get("description", ""), "desde": hoje()}
        cat["skills"].append(e)
    e.update({"estado": "ativa", "versao": versao, "promovida_em": hoje()})
    e.pop("rascunho_na_oficina", None)
    gravar_catalogo(cat)
    print("{} promovida (versão {}). O {} passa a usá-la na próxima conversa.".format(nome, versao, agente.NOME))
    print("Para a Root acompanhar, feche o dia.")


def aposentar(nome):
    conferir_nome(nome)
    cat = ler_catalogo()
    e = entrada(cat, nome)
    if not e:
        raise Erro("{} não está no catálogo".format(nome))
    if e.get("origem") != "cliente":
        raise Erro("{} é uma ferramenta da Root; para tirá-la, peça à Root".format(nome))
    for pasta in (ATIVAS / nome, OFICINA / nome):
        if pasta.exists():
            guardar_aposentada(pasta, nome, e.get("versao"))
    e.update({"estado": "aposentada", "aposentada_em": hoje()})
    e.pop("rascunho_na_oficina", None)
    gravar_catalogo(cat)
    print("{} aposentada. Ela fica guardada em oficina/_aposentadas/.".format(nome))


def inconsistencias(cat=None):
    cat = cat or ler_catalogo()
    achados = []
    nomes = {s["nome"]: s for s in cat["skills"]}
    if ATIVAS.exists():
        for pasta in sorted(p for p in ATIVAS.iterdir() if p.is_dir()):
            s = nomes.get(pasta.name)
            if not s:
                achados.append("{} está em {} e não está no catálogo".format(pasta.name, PASTA_ATIVAS))
            elif s.get("estado") != "ativa":
                achados.append("{} está em {} mas o catálogo diz {}".format(pasta.name, PASTA_ATIVAS, s.get("estado")))
    for s in cat["skills"]:
        if s.get("estado") == "ativa" and not (ATIVAS / s["nome"] / "SKILL.md").exists():
            achados.append("{} está ativa no catálogo e não existe em {}".format(s["nome"], PASTA_ATIVAS))
        if s.get("estado") == "homologacao" and not (OFICINA / s["nome"]).exists():
            achados.append("{} está em homologação e não existe em oficina/".format(s["nome"]))
    return achados


def listar():
    cat = ler_catalogo()
    rotulo = {"root": "Root", "frente": "Root (frente)", "cliente": "sua"}
    print("{:<28} {:<14} {:<12} {}".format("Ferramenta", "De quem", "Estado", "Versão"))
    for s in cat["skills"]:
        estado = s.get("estado", "?") + (" + rascunho" if s.get("rascunho_na_oficina") else "")
        print("{:<28} {:<14} {:<12} {}".format(s["nome"], rotulo.get(s.get("origem"), "?"), estado, s.get("versao", "")))
    achados = inconsistencias(cat)
    if achados:
        print("\nPara arrumar:")
        for a in achados:
            print("  - " + a)
        return 1
    return 0


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, resto = argv[1], argv[2:]
    try:
        if cmd == "listar":
            return listar()
        if cmd == "nova" and len(resto) >= 2:
            base = resto[resto.index("--a-partir-de") + 1] if "--a-partir-de" in resto else None
            nova(resto[0], resto[1], base)
            return 0
        if cmd == "melhorar" and resto:
            melhorar(resto[0])
            return 0
        if cmd == "conferir" and resto:
            return conferir(resto[0])
        if cmd == "promover" and resto:
            promover(resto[0])
            return 0
        if cmd == "aposentar" and resto:
            aposentar(resto[0])
            return 0
    except Erro as e:
        print("Não feito: {}".format(e))
        return 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
