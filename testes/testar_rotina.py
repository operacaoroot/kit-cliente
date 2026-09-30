#!/usr/bin/env python3
"""Testes da rotina que alimenta o vault (ferramentas/rotina.py e a skill alimentar-vault).

Uso (na raiz do kit-cliente):
    python3 testes/testar_rotina.py -v

Monta um kit de teste numa pasta temporária (cópia do manifesto de exemplo, outro slug), finge o
histórico de conversas do Claude com KIT_CLAUDE_PROJECTS, troca o Claude por um roteiro de teste com
KIT_CLAUDE_BIN e o GitHub por um repositório local. Não agenda nada de verdade (só --simular), não
usa rede e não chama modelo de IA. Só biblioteca padrão, compatível com Python 3.9.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
import montar  # noqa: E402

PASTA = Path(tempfile.mkdtemp(prefix="kit-rotina-"))
PROJETOS = PASTA / "claude-projects"
KIT = None


def montar_kit(sistema="mac", slug="teste-rotina"):
    montar.SAIDA = PASTA / "saida"
    m = json.loads((RAIZ / "manifestos" / "exemplo-marina-duarte.json").read_text(encoding="utf-8"))
    m["cliente"].update({"slug": slug, "sistema": sistema})
    m.pop("entrega", None)
    m.setdefault("combinado", {})["rotina_do_vault"] = {"ligar": True, "horas": ["08:00", "12:30", "17:30"], "enviar": True}
    arq = PASTA / ("m-" + slug + ".json")
    arq.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    nulo = open(os.devnull, "w")
    antes, sys.stdout = sys.stdout, nulo
    try:
        return montar.montar(str(arq), {"--rascunho", "--permitir-semente"})
    finally:
        sys.stdout = antes
        nulo.close()


def env(**extra):
    e = dict(os.environ)
    e["KIT_CLAUDE_PROJECTS"] = str(PROJETOS)
    e.update({k: str(v) for k, v in extra.items()})
    return e


def rotina(*args, **extra):
    return subprocess.run([sys.executable, "ferramentas/rotina.py"] + list(args), cwd=str(KIT),
                          capture_output=True, text=True, env=env(**extra))


def conversa(pasta_do_projeto, linhas):
    pasta_do_projeto.mkdir(parents=True, exist_ok=True)
    arq = pasta_do_projeto / "abcd1234-0000-0000-0000-000000000000.jsonl"
    with open(arq, "a", encoding="utf-8") as f:
        for l in linhas:
            f.write(json.dumps(l, ensure_ascii=False) + "\n")
    return arq


def fala(tipo, conteudo, minutos_atras=1, **extra):
    quando = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=minutos_atras)).isoformat().replace("+00:00", "Z")
    o = {"type": tipo, "timestamp": quando, "cwd": str(KIT), "message": {"role": tipo, "content": conteudo}}
    o.update(extra)
    return o


def setUpModule():
    global KIT
    KIT = montar_kit()


def tearDownModule():
    shutil.rmtree(PASTA, ignore_errors=True)


class Montagem(unittest.TestCase):
    def test_pecas_e_combinado(self):
        self.assertTrue((KIT / "ferramentas" / "rotina.py").exists())
        self.assertTrue((KIT / ".claude" / "skills" / "alimentar-vault" / "SKILL.md").exists())
        cliente = json.loads((KIT / ".root" / "cliente.json").read_text(encoding="utf-8"))
        self.assertEqual(cliente["rotina_do_vault"], {"ligar": True, "horas": ["08:00", "12:30", "17:30"], "enviar": True})
        cat = {s["nome"]: s for s in json.loads((KIT / "catalogo.json").read_text(encoding="utf-8"))["skills"]}
        self.assertEqual(cat["alimentar-vault"]["origem"], "root")
        cfg = json.loads((KIT / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Bash(python3 ferramentas/rotina.py:*)", cfg["permissions"]["allow"])
        self.assertIn("Bash(.venv/Scripts/python ferramentas/rotina.py:*)", cfg["permissions"]["allow"])

    def test_kit_windows_sem_python3(self):
        kit = montar_kit("windows", "teste-rotina-win")
        texto = (kit / ".claude" / "skills" / "alimentar-vault" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("python3 ", texto)
        self.assertIn(".venv/Scripts/python ferramentas/rotina.py --coletar", texto)

    def test_horario_invalido_recusa_montagem(self):
        m = json.loads((RAIZ / "manifestos" / "exemplo-marina-duarte.json").read_text(encoding="utf-8"))
        m.setdefault("combinado", {})["rotina_do_vault"] = {"ligar": True, "horas": ["25:00"]}
        with self.assertRaises(montar.Recusa):
            montar.rotina_combinada(m)


class Coleta(unittest.TestCase):
    def setUp(self):
        shutil.rmtree(PROJETOS, ignore_errors=True)
        estado = KIT / ".root" / "rotina.json"
        if estado.exists():
            estado.unlink()
        shutil.rmtree(KIT / "_privado", ignore_errors=True)
        self.pasta = PROJETOS / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(KIT)))

    def test_coleta_mascara_segredos_e_ignora_ruido(self):
        conversa(self.pasta, [
            fala("user", "<command-name>/model</command-name>"),
            fala("user", "Fechei com o fornecedor novo. minha senha: abc123segredo e o CPF 123.456.789-09"),
            fala("assistant", [{"type": "text", "text": "Registrei a decisão."},
                               {"type": "tool_use", "name": "Write", "input": {"file_path": str(KIT / "vault" / "60-Decisoes" / "x.md")}}]),
            fala("user", "tarefa lateral", isSidechain=True),
        ])
        (KIT / "entregas" / "resumo.md").write_text("Resumo da semana com token=sk-ant-abcdefghijklmnopqrstu", encoding="utf-8")
        r = rotina("--coletar")
        self.assertEqual(r.returncode, 0, r.stderr)
        resumo = (KIT / r.stdout.strip()).read_text(encoding="utf-8")
        self.assertIn("Fechei com o fornecedor novo", resumo)
        self.assertNotIn("abc123segredo", resumo)
        self.assertNotIn("123.456.789-09", resumo)
        self.assertNotIn("sk-ant-abcdefghijklmnopqrstu", resumo)
        self.assertIn("[SEGREDO:cpf]", resumo)
        self.assertIn("`vault/60-Decisoes/x.md`", resumo)
        self.assertIn("entregas/resumo.md", resumo)
        self.assertNotIn("/model", resumo)
        self.assertNotIn("tarefa lateral", resumo)
        self.assertTrue(r.stdout.strip().startswith("_privado/rotina/"))
        ignorado = subprocess.run(["git", "check-ignore", "-q", r.stdout.strip()], cwd=str(KIT)).returncode
        self.assertEqual(ignorado, 0, "a coleta precisa ficar fora do git")
        (KIT / "entregas" / "resumo.md").unlink()

    def test_concluir_e_nada_novo_depois(self):
        conversa(self.pasta, [fala("user", "Revisei o plano de ação do cliente", minutos_atras=2)])
        caminho = rotina("--coletar").stdout.strip()
        r = rotina("--concluir", Path(caminho).name)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(rotina("--coletar").stdout.strip(), "nada novo")
        estado = json.loads((KIT / ".root" / "rotina.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["coletas_pendentes"], [])
        self.assertEqual(estado["alimentacoes"], 1)

    def test_acha_a_pasta_pela_cwd_quando_o_nome_muda(self):
        conversa(PROJETOS / "outro-nome-qualquer", [fala("user", "Conversa achada pela cwd")])
        caminho = rotina("--coletar").stdout.strip()
        self.assertIn("Conversa achada pela cwd", (KIT / caminho).read_text(encoding="utf-8"))

    def test_conversa_de_outra_pasta_nao_entra(self):
        outra = {"type": "user", "timestamp": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                 "cwd": "/outra/pasta", "message": {"role": "user", "content": "assunto de outra pasta"}}
        conversa(PROJETOS / "-outra-pasta", [outra])
        saida = rotina("--coletar").stdout.strip()
        if saida != "nada novo":
            self.assertNotIn("assunto de outra pasta", (KIT / saida).read_text(encoding="utf-8"))


class Agendadores(unittest.TestCase):
    def test_mac_tres_horarios(self):
        r = rotina("--ligar", "--simular", KIT_SISTEMA="mac")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(len(re.findall(r"<key>Hour</key>", r.stdout)), 3)
        for h, m in ((8, 0), (12, 30), (17, 30)):
            self.assertIn("<integer>{}</integer><key>Minute</key><integer>{}</integer>".format(h, m), r.stdout)
        self.assertIn("--rodar", r.stdout)

    def test_windows_tres_gatilhos_sem_janela(self):
        r = rotina("--ligar", "--simular", KIT_SISTEMA="windows")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(r.stdout.count("New-ScheduledTaskTrigger -Daily"), 3)
        self.assertIn("pythonw.exe", r.stdout)
        self.assertIn("-StartWhenAvailable", r.stdout)
        self.assertIn("-Force", r.stdout)

    def test_linux_uma_linha_por_horario(self):
        r = rotina("--ligar", "--horas", "07:15,13:00,19:45", "--simular", KIT_SISTEMA="linux")
        self.assertEqual(len([l for l in r.stdout.splitlines() if "--rodar" in l]), 3)
        self.assertIn("15 7 * * *", r.stdout)

    def test_horario_invalido(self):
        self.assertNotEqual(rotina("--ligar", "--horas", "25:00", "--simular").returncode, 0)

    def test_desligar_simulado(self):
        for s in ("mac", "windows", "linux"):
            self.assertEqual(rotina("--desligar", "--simular", KIT_SISTEMA=s).returncode, 0, s)


class Conferencia(unittest.TestCase):
    def test_notas_da_rotina_nao_travam_o_passo_do_vault(self):
        subprocess.run([sys.executable, "ferramentas/verificar.py", "--silencioso", "--sem-rede"], cwd=str(KIT), env=env())
        antes = {p["id"]: p for p in json.loads((KIT / ".root" / "progresso.json").read_text(encoding="utf-8"))["passos"]}
        (KIT / "vault" / "_diario").mkdir(exist_ok=True)
        (KIT / "vault" / "_diario" / "2026-10-01.md").write_text("---\nkind: nota\nrevisar: sim\n---\n# Diário\n", encoding="utf-8")
        (KIT / "vault" / "60-Decisoes" / "2026-10-01 - teste.md").write_text(
            "---\nkind: decisao\nrevisar: sim\norigem: rotina\n---\n# Teste\n", encoding="utf-8")
        subprocess.run([sys.executable, "ferramentas/verificar.py", "--silencioso", "--sem-rede"], cwd=str(KIT), env=env())
        prog = json.loads((KIT / ".root" / "progresso.json").read_text(encoding="utf-8"))
        depois = {p["id"]: p for p in prog["passos"]}
        self.assertEqual(antes["vault"]["detalhe"], depois["vault"]["detalhe"])
        self.assertEqual(prog["rotina_do_vault"]["notas_para_revisar"], 1)
        (KIT / "vault" / "_diario" / "2026-10-01.md").unlink()
        (KIT / "vault" / "60-Decisoes" / "2026-10-01 - teste.md").unlink()


CLAUDE_DE_TESTE = r'''#!/usr/bin/env python3
import re, subprocess, sys, datetime
pedido = sys.argv[sys.argv.index("-p") + 1]
assert "--no-session-persistence" in sys.argv and "acceptEdits" in sys.argv
coleta = re.search(r"(_privado/rotina/coleta-[0-9-]+\.md)", pedido).group(1)
hoje = datetime.date.today().isoformat()
open("vault/_diario/%s.md" % hoje, "a").write("---\nkind: nota\nrevisar: não\norigem: rotina\n---\n# Diário\n\n- teste\n")
subprocess.run([sys.executable, "ferramentas/rotina.py", "--concluir", coleta.split("/")[-1]], check=True)
print("1 nota criada")
'''


class RodadaCompleta(unittest.TestCase):
    def test_rodada_escreve_conclui_e_envia(self):
        shutil.rmtree(PROJETOS, ignore_errors=True)
        (KIT / ".root" / "rotina.json").write_text(json.dumps({"enviar": True}), encoding="utf-8")
        (KIT / "vault" / "_diario").mkdir(exist_ok=True)
        remoto = PASTA / "remoto.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remoto)], check=True)
        subprocess.run(["git", "remote", "set-url", "origin", str(remoto)], cwd=str(KIT), check=True)
        subprocess.run(["git", "add", "-A"], cwd=str(KIT))
        subprocess.run(["git", "commit", "-qm", "base do teste"], cwd=str(KIT))
        subprocess.run(["git", "push", "-q", "-u", "origin", "main"], cwd=str(KIT), check=True)
        falso = PASTA / "claude-de-teste"
        falso.write_text(CLAUDE_DE_TESTE, encoding="utf-8")
        falso.chmod(0o755)
        conversa(PROJETOS / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(KIT))),
                 [fala("user", "Decidi que a proposta sai sempre na sexta")])
        r = rotina("--rodar", KIT_CLAUDE_BIN=falso)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        estado = json.loads((KIT / ".root" / "rotina.json").read_text(encoding="utf-8"))
        self.assertEqual(estado["ultimo_resultado"], "vault alimentado")
        self.assertEqual(estado["ultimo_envio"], "enviado")
        self.assertEqual(estado["coletas_pendentes"], [])
        assunto = subprocess.run(["git", "--git-dir", str(remoto), "log", "-1", "--format=%s"], capture_output=True, text=True).stdout
        self.assertTrue(assunto.startswith("Rotina: vault e progresso"), assunto)
        arquivos = subprocess.run(["git", "--git-dir", str(remoto), "show", "--name-only", "--format=", "HEAD"],
                                  capture_output=True, text=True).stdout
        self.assertIn("vault/_diario/", arquivos)
        self.assertNotIn("_privado", arquivos)
        prog = json.loads((KIT / ".root" / "progresso.json").read_text(encoding="utf-8"))
        fechar = next(p for p in prog["passos"] if p["id"] == "fechar-o-dia")
        self.assertIn("ainda sem envio", fechar["detalhe"], "o envio da rotina não conta como a pessoa fechar o dia")
        self.assertEqual(rotina("--rodar", KIT_CLAUDE_BIN=falso).returncode, 0)
        self.assertEqual(json.loads((KIT / ".root" / "rotina.json").read_text(encoding="utf-8"))["ultimo_resultado"], "nada novo")

    def test_sem_claude_a_coleta_fica_pendente(self):
        shutil.rmtree(PROJETOS, ignore_errors=True)
        (KIT / ".root" / "rotina.json").write_text(json.dumps({"enviar": False}), encoding="utf-8")
        conversa(PROJETOS / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(KIT))), [fala("user", "Outra conversa")])
        e = env(KIT_CLAUDE_BIN=PASTA / "nao-existe", HOME=PASTA / "casa-vazia", PATH="/usr/bin:/bin")
        r = subprocess.run([sys.executable, "ferramentas/rotina.py", "--rodar"], cwd=str(KIT), capture_output=True, text=True, env=e)
        self.assertEqual(r.returncode, 1)
        estado = json.loads((KIT / ".root" / "rotina.json").read_text(encoding="utf-8"))
        self.assertEqual(len(estado["coletas_pendentes"]), 1)


if __name__ == "__main__":
    unittest.main()
