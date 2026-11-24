#!/usr/bin/env python3
"""Testes do Painel do kit e da ligação só pela chave (sem código do GitHub).

Uso (na raiz do kit-cliente):
    python3 testes/testar_painel.py [-v]

Monta kits de teste numa pasta temporária a partir de uma cópia do manifesto de exemplo. Não usa
rede, não instala nada e não abre navegador. O JavaScript só é conferido se houver `node` no PATH.
Só biblioteca padrão, compatível com Python 3.9.
"""
import http.client
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
import montar  # noqa: E402

PECAS = ("painel/index.html", "painel/painel.css", "painel/painel.js", "painel/primeiros-passos.js", "ferramentas/painel.py")


def py(kit, *args, env=None):
    return subprocess.run([sys.executable] + list(args), cwd=str(kit), capture_output=True, text=True, env=env)


def ler_estado(kit):
    return json.loads((kit / "_privado/painel/estado.json").read_text(encoding="utf-8"))


def ler_estado_js(kit):
    texto = (kit / "_privado/painel/estado.js").read_text(encoding="utf-8")
    prefixo = "window.KIT_PAINEL = "
    assert texto.startswith(prefixo) and texto.rstrip().endswith(";"), texto[:80]
    return json.loads(texto[len(prefixo):].rstrip().rstrip(";").replace("<\\/", "</"))


class Kits:
    pasta = None
    kits = {}

    @classmethod
    def preparar(cls):
        cls.pasta = Path(tempfile.mkdtemp(prefix="kit-painel-"))
        montar.SAIDA = cls.pasta / "saida"
        base = json.loads((RAIZ / "manifestos" / "exemplo-marina-duarte.json").read_text(encoding="utf-8"))
        for sistema in ("mac", "windows"):
            m = json.loads(json.dumps(base))
            m["cliente"]["slug"] = "teste-painel-" + sistema
            m["cliente"]["sistema"] = sistema
            m.pop("entrega", None)
            arq = cls.pasta / ("manifesto-" + sistema + ".json")
            arq.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            with open(os.devnull, "w") as nulo:
                saida, sys.stdout = sys.stdout, nulo
                try:
                    cls.kits[sistema] = montar.montar(str(arq), {"--rascunho", "--permitir-semente"})
                finally:
                    sys.stdout = saida


def setUpModule():
    Kits.preparar()


def tearDownModule():
    shutil.rmtree(Kits.pasta, ignore_errors=True)


class Painel(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["mac"]
        shutil.rmtree(self.kit / "_privado" / "painel", ignore_errors=True)

    def test_pecas_vao_para_o_kit_e_ficam_fora_do_git(self):
        for sistema, kit in Kits.kits.items():
            for rel in PECAS:
                self.assertTrue((kit / rel).is_file(), "{}: falta {}".format(sistema, rel))
        py(self.kit, "ferramentas/painel.py", "iniciar")
        r = subprocess.run(["git", "status", "--porcelain", "--", "_privado"], cwd=str(self.kit), capture_output=True, text=True)
        self.assertEqual(r.stdout.strip(), "", "o estado do painel não pode entrar no git")

    def test_iniciar_cria_estado_com_as_etapas(self):
        r = py(self.kit, "ferramentas/painel.py", "iniciar")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        e = ler_estado(self.kit)
        self.assertEqual(e["fase"], "instalando")
        self.assertEqual([x["id"] for x in e["etapas"]], ["basico", "programas", "python", "autonomia", "chave", "atalho", "conferencia"])
        self.assertTrue(all(x["estado"] == "pendente" for x in e["etapas"]))
        self.assertEqual(ler_estado_js(self.kit)["etapas"], e["etapas"])
        self.assertTrue(e["links"]["claude"].startswith("claude://code/new?"))

    def test_etapa_e_evento_registram(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        py(self.kit, "ferramentas/painel.py", "etapa", "programas", "andamento", "instalando", "o", "Obsidian")
        py(self.kit, "ferramentas/painel.py", "evento", "Clique em Sim na janela do Windows", "--tipo", "aviso")
        py(self.kit, "ferramentas/painel.py", "etapa", "programas", "ok")
        e = ler_estado(self.kit)
        programas = next(x for x in e["etapas"] if x["id"] == "programas")
        self.assertEqual(programas["estado"], "ok")
        self.assertEqual(programas["detalhe"], "instalando o Obsidian")
        textos = [ev["texto"] for ev in e["eventos"]]
        self.assertIn("Clique em Sim na janela do Windows", textos)
        self.assertIn("aviso", [ev["tipo"] for ev in e["eventos"]])

    def test_erro_de_uso_nao_derruba_e_nao_mexe(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        antes = ler_estado(self.kit)["etapas"]
        self.assertEqual(py(self.kit, "ferramentas/painel.py", "etapa", "nao-existe", "ok").returncode, 2)
        self.assertEqual(py(self.kit, "ferramentas/painel.py", "etapa", "chave", "talvez").returncode, 2)
        self.assertEqual(ler_estado(self.kit)["etapas"], antes)

    def test_texto_nao_fecha_a_tag_script(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        py(self.kit, "ferramentas/painel.py", "evento", "</script><script>alert(1)</script>")
        js = (self.kit / "_privado/painel/estado.js").read_text(encoding="utf-8")
        self.assertNotIn("</script>", js)
        self.assertIn("</script><script>alert(1)</script>", [ev["texto"] for ev in ler_estado_js(self.kit)["eventos"]])

    def test_ambiente_repete_as_linhas_no_painel(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        codigo = ("import sys; sys.path.insert(0, 'ferramentas'); import ambiente; "
                  "ambiente.ok('Obsidian instalado'); ambiente.aviso('Java falhou'); ambiente.contar('..  instalando Node.js: rodar ferramentas')")
        r = py(self.kit, "-c", codigo)
        self.assertEqual(r.returncode, 0, r.stderr)
        eventos = {ev["texto"]: ev["tipo"] for ev in ler_estado(self.kit)["eventos"]}
        self.assertEqual(eventos.get("Obsidian instalado"), "ok")
        self.assertEqual(eventos.get("Java falhou"), "aviso")
        self.assertIn("instalando Node.js: rodar ferramentas", eventos)

    def test_sem_instalador_o_ambiente_nao_cria_painel(self):
        r = py(self.kit, "-c", "import sys; sys.path.insert(0, 'ferramentas'); import ambiente; ambiente.ok('x')")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.kit / "_privado/painel/estado.json").exists())

    def test_depois_de_concluir_execucao_avulsa_nao_reescreve(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        py(self.kit, "ferramentas/painel.py", "concluir", "--sem-rede")
        antes = ler_estado(self.kit)
        r = py(self.kit, "-c", "import sys; sys.path.insert(0, 'ferramentas'); import ambiente, painel; "
                               "ambiente.ok('conferência avulsa'); painel.etapa('chave', 'falhou', 'x')")
        self.assertEqual(r.returncode, 0, r.stderr)
        depois = ler_estado(self.kit)
        self.assertEqual(depois["eventos"], antes["eventos"])
        self.assertEqual(depois["etapas"], antes["etapas"])
        self.assertEqual(depois["agora"], antes["agora"])

    def test_conferencia_quebrada_nao_deixa_a_pagina_parada(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        catalogo = self.kit / "ambiente" / "apps.json"
        guardado = catalogo.read_bytes()
        catalogo.write_text("{ quebrado", encoding="utf-8")
        try:
            r = py(self.kit, "ferramentas/painel.py", "concluir", "--sem-rede")
        finally:
            catalogo.write_bytes(guardado)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        e = ler_estado(self.kit)
        self.assertEqual(e["fase"], "atencao")
        self.assertTrue(any("Não consegui conferir" in f for f in e["conferencia"]["falta"]), e["conferencia"])
        self.assertEqual(next(x for x in e["etapas"] if x["id"] == "conferencia")["estado"], "atencao")

    def test_concluir_sem_ligacao_lista_o_que_falta(self):
        py(self.kit, "ferramentas/painel.py", "iniciar")
        r = py(self.kit, "ferramentas/painel.py", "concluir", "--sem-rede")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        e = ler_estado(self.kit)
        self.assertEqual(e["fase"], "atencao")  # o kit de teste não tem o Python do kit (.venv)
        self.assertTrue(any(".venv" in f for f in e["conferencia"]["falta"]), e["conferencia"])
        self.assertTrue(any("pela chave do kit" in f for f in e["conferencia"]["feito"]), e["conferencia"])
        conferencia = next(x for x in e["etapas"] if x["id"] == "conferencia")
        self.assertEqual(conferencia["estado"], "atencao")


class SoPelaChave(unittest.TestCase):
    """O kit nunca mais pede login nem código do GitHub."""

    def test_concluir_sem_chave_diz_que_falta_ligar(self):
        kit = Kits.kits["windows"]
        chave = kit / ".root" / "chave"
        guardada = chave.read_bytes()
        chave.unlink()
        try:
            py(kit, "ferramentas/painel.py", "iniciar")
            py(kit, "ferramentas/painel.py", "concluir", "--sem-rede")
            falta = ler_estado(kit)["conferencia"]["falta"]
            self.assertTrue(any("ainda não está ligado à Root" in f for f in falta), falta)
        finally:
            chave.write_bytes(guardada)

    def test_conectar_antigo_liga_pela_chave_sem_chamar_o_gh(self):
        kit = Kits.kits["mac"]
        falso = Kits.pasta / "bin-falso"
        falso.mkdir(exist_ok=True)
        marca = Kits.pasta / "gh-foi-chamado"
        gh = falso / "gh"
        gh.write_text("#!/bin/sh\ntouch '{}'\nexit 0\n".format(marca), encoding="utf-8")
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        env = dict(os.environ, PATH=str(falso) + os.pathsep + os.environ.get("PATH", ""))
        r = py(kit, "ferramentas/conectar.py", "--conectar", env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("pela chave", r.stdout)
        self.assertFalse(marca.exists(), "o conectar chamou o gh")
        remoto = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(kit), capture_output=True, text=True).stdout.strip()
        self.assertEqual(remoto, "git@github.com:operacaoroot/kit-teste-painel-mac.git")
        estado = json.loads(py(kit, "ferramentas/conectar.py", "--conferir", "--json").stdout)
        self.assertEqual(estado["modo"], "chave")

    def test_instaladores_sem_login_e_com_painel(self):
        for sistema, kit in Kits.kits.items():
            for rel in ("instalar/instalar.sh", "instalar/instalar.ps1", "ferramentas/onboarding.py"):
                texto = (kit / rel).read_text(encoding="utf-8")
                self.assertNotIn("--conectar", texto, "{}: {}".format(sistema, rel))
                self.assertNotIn("auth login", texto, "{}: {}".format(sistema, rel))
                self.assertIn("painel", texto.lower(), "{}: {}".format(sistema, rel))
                self.assertIn("--usar-chave", texto, "{}: {}".format(sistema, rel))

    def test_nenhum_texto_manda_digitar_codigo(self):
        for sistema, kit in Kits.kits.items():
            for arq in list(kit.rglob("*.md")) + [kit / "ferramentas/passos.json", kit / "onboarding/index.html"]:
                if ".git" in arq.parts:
                    continue
                texto = arq.read_text(encoding="utf-8")
                rel = arq.relative_to(kit).as_posix()
                for proibido in ("código de 8 letras", "Authorize", "conectar.py --conectar", "auth login"):
                    self.assertNotIn(proibido, texto, "{}: {} em {}".format(sistema, proibido, rel))

    def test_gh_deixou_de_ser_obrigatorio(self):
        apps = json.loads((RAIZ / "modelo/ambiente/apps.json").read_text(encoding="utf-8"))["apps"]
        gh = next(a for a in apps if a["id"] == "gh")
        self.assertEqual(set(gh["perfis"].values()), {"opcional"})


class PaginaDoPainel(unittest.TestCase):
    def test_primeiros_passos_cobrem_obsidian_e_conectores(self):
        texto = (RAIZ / "modelo/painel/primeiros-passos.js").read_text(encoding="utf-8")
        for palavra in ("Obsidian", "extrair-contexto", "cuidar-do-vault", "Conectores", "vamos configurar o meu perfil".capitalize(), "fechar o dia"):
            self.assertIn(palavra, texto)
        for rel in ("painel/primeiros-passos.js", "painel/index.html", "painel/painel.js"):
            self.assertNotIn("—", (RAIZ / "modelo" / rel).read_text(encoding="utf-8"), rel)

    def test_pagina_nao_usa_html_injetado(self):
        js = (RAIZ / "modelo/painel/painel.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", js)
        self.assertNotIn("eval(", js)

    @unittest.skipUnless(shutil.which("node"), "sem node no PATH")
    def test_javascript_tem_sintaxe_valida(self):
        for rel in ("painel/painel.js", "painel/primeiros-passos.js", "onboarding/app.js"):
            r = subprocess.run(["node", "--check", str(RAIZ / "modelo" / rel)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, rel + ": " + r.stderr)


class PainelNoOnboardingDoMac(unittest.TestCase):
    """A página guiada do Mac serve o mesmo painel e mostra a atividade da instalação."""

    def setUp(self):
        sys.path.insert(0, str(RAIZ / "modelo/ferramentas"))
        import onboarding
        self.o = onboarding
        self.temp = tempfile.TemporaryDirectory()
        self.kit = Path(self.temp.name)
        for pasta in ("onboarding", "painel", "marca"):
            shutil.copytree(RAIZ / "modelo" / pasta, self.kit / pasta)
        (self.kit / ".root").mkdir()
        onboarding.salvar_json(self.kit / ".root/cliente.json", {"nome": "Exemplo", "repo": "operacaoroot/kit-teste"})
        self.server = onboarding.Servidor(("127.0.0.1", 0), onboarding.API)
        self.server.app = onboarding.Onboarding(self.kit)
        self.server.endereco = "127.0.0.1:" + str(self.server.server_port)
        self.server.token = "teste-token"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join(); self.temp.cleanup()

    def get(self, caminho):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        conn.request("GET", caminho)
        r = conn.getresponse(); corpo = r.read(); conn.close()
        return r.status, corpo

    def test_serve_o_painel_e_o_estado(self):
        for caminho in ("/painel/index.html", "/painel/painel.js", "/painel/painel.css", "/painel/primeiros-passos.js",
                        "/marca/root-logo.png", "/onboarding/assets/SpaceGrotesk-Regular.ttf"):
            self.assertEqual(self.get(caminho)[0], 200, caminho)
        self.assertEqual(self.get("/_privado/painel/estado.js?t=1")[0], 404)  # ainda não começou
        self.o.painel.iniciar()
        self.o.painel.evento("Obsidian instalado", "ok")
        status, corpo = self.get("/_privado/painel/estado.js?t=123")
        self.assertEqual(status, 200)
        self.assertIn("Obsidian instalado", corpo.decode("utf-8"))
        self.assertTrue((self.kit / "_privado/painel/estado.json").exists(), "o painel tem de gravar no kit do onboarding")

    def test_continua_fechado_para_o_resto(self):
        self.assertEqual(self.get("/_privado/onboarding/estado.json")[0], 404)
        self.assertEqual(self.get("/_privado/painel/estado.json")[0], 404)
        self.assertEqual(self.get("/painel/../.root/cliente.json")[0], 404)

    def test_snapshot_traz_a_atividade(self):
        self.o.painel.iniciar()
        self.o.painel.evento("baixando Node.js v24", "info")
        s = self.server.app.snapshot()
        self.assertEqual(s["painel_url"], "/painel/index.html")
        self.assertEqual(s["atividade"][0]["texto"], "baixando Node.js v24")


if __name__ == "__main__":
    unittest.main()
