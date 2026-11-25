#!/usr/bin/env python3
"""Testes do roteiro de revisão dos sistemas (ferramentas/revisar_sistemas.py, skill revisar-sistemas)
e do kit de revisão para quem já tem o Claude instalado (montador/revisao.py).

Uso (na raiz do kit-cliente):
    KIT_SELO_SEGREDO=teste-local-descartavel python3 testes/testar_revisao.py -v

Não usa rede e não instala nada: HOME e CLAUDE_CONFIG_DIR apontam para uma pasta temporária, o
`uv` e o `claude` são programas de mentira postos no PATH, e o plugin é um script que devolve o
que o teste mandar. Só biblioteca padrão, compatível com Python 3.9. Roda em Mac e Linux.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "montador"))
sys.path.insert(0, str(RAIZ / "testes"))
import montar  # noqa: E402
import testar_sistemas as base  # noqa: E402

MODELO = RAIZ / "modelo"
SEGREDO = "S3gredo-de-teste-9"

ERROS = [
    {"id": "login", "sinais": ["Invalid login credentials"], "significa": "O sistema recusou o e-mail ou a senha gravados.",
     "resolve": "Grave a senha de novo pela janela do kit.", "quem_resolve": "voce"},
    {"id": "escrita-nao-liberada", "sinais": ["forbidden_write_admin_only"],
     "significa": "Esta empresa não aceita gravação feita por operador.",
     "resolve": "Só o responsável liga a gravação por operador nesta empresa.", "quem_resolve": "responsavel"},
]


def sistemas_com_revisao():
    s = json.loads(json.dumps(base.SISTEMAS))
    s["plugins"][0]["versao_minima"] = "1.5.0"
    s["erros"] = json.loads(json.dumps(ERROS))
    return s


class Portao(unittest.TestCase):
    def faltas(self, mexer):
        s = sistemas_com_revisao()
        mexer(s)
        return montar.conferir_sistemas(s)

    def test_bloco_com_erros_e_versao_minima_passa(self):
        self.assertEqual(montar.conferir_sistemas(sistemas_com_revisao()), [])

    def test_erro_precisa_de_sinal_significado_e_solucao(self):
        self.assertTrue(self.faltas(lambda s: s["erros"][0].update(sinais=[])))
        self.assertTrue(self.faltas(lambda s: s["erros"][0].pop("significa")))
        self.assertTrue(self.faltas(lambda s: s["erros"][0].pop("resolve")))

    def test_quem_resolve_so_voce_ou_responsavel(self):
        self.assertTrue(self.faltas(lambda s: s["erros"][0].update(quem_resolve="ninguem")))

    def test_versao_minima_e_numero_com_pontos(self):
        self.assertTrue(self.faltas(lambda s: s["plugins"][0].update(versao_minima="a mais nova")))

    def test_pecas_sao_so_do_claude(self):
        import atualizar
        self.assertIn("revisar_sistemas.py", montar.SO_DO_CLAUDE)
        self.assertIn("revisar-sistemas", montar.SKILLS_SO_DO_CLAUDE)
        self.assertIn(("ferramentas/revisar_sistemas.py", "ferramentas/revisar_sistemas.py"), atualizar.SO_CLAUDE)


class Ambiente:
    """Um computador de mentira: HOME, registro de plugins do Claude, uv, claude e o plugin."""

    def __init__(self, kit, uv=True, claude=True, plugin="1.5.0", credencial=True):
        self.kit = kit
        self.home = Path(tempfile.mkdtemp(prefix="revisao-home-"))
        self.bin = self.home / "bin"
        self.bin.mkdir()
        if uv:
            self.programa("uv", '#!/bin/sh\nif [ "$1" = "--version" ]; then echo "uv 0.9.9"; exit 0; fi\nshift 2\nexec "{}" "$@"\n'.format(sys.executable))
        if claude:
            self.programa("claude", '#!/bin/sh\necho "2.1.314 (Claude Code)"\n')
        if plugin:
            caminho = self.home / "plugins-cache" / "exemplo"
            (caminho / "mcp").mkdir(parents=True)
            (caminho / "mcp" / "servidor.py").write_text(
                "import os, sys\nprint(os.environ.get('FAKE_SAIDA', 'selftest OK'))\nsys.exit(int(os.environ.get('FAKE_CODIGO', '0')))\n",
                encoding="utf-8")
            registro = self.home / ".claude" / "plugins"
            registro.mkdir(parents=True)
            (registro / "installed_plugins.json").write_text(json.dumps(
                {"version": 2, "plugins": {"exemplo@exemplo": [{"scope": "user", "installPath": str(caminho), "version": plugin}]}}),
                encoding="utf-8")
        if credencial:
            self.gravar_env("ERP_EMAIL='pessoa@exemplo.com'\nERP_ANON_KEY='chave-publica'\nERP_PASSWORD='{}'\n".format(SEGREDO))
        for sobra in (".root/sistemas-estado.json", "relatorio-revisao.txt"):
            if (kit / sobra).exists():
                (kit / sobra).unlink()

    def programa(self, nome, texto):
        p = self.bin / nome
        p.write_text(texto, encoding="utf-8")
        p.chmod(p.stat().st_mode | stat.S_IXUSR)

    def gravar_env(self, texto):
        arq = self.home / ".exemplo" / "credenciais.env"
        arq.parent.mkdir(exist_ok=True)
        arq.write_text(texto, encoding="utf-8")
        arq.chmod(0o600)

    def rodar(self, *args, **extra):
        env = {"HOME": str(self.home), "USERPROFILE": str(self.home), "CLAUDE_CONFIG_DIR": str(self.home / ".claude"),
               "PATH": "{}:/usr/bin:/bin".format(self.bin), "KIT_MODO_TESTE": "1", "LANG": "C.UTF-8", "PYTHONIOENCODING": "utf-8"}
        env.update(extra)
        return subprocess.run([sys.executable, "ferramentas/revisar_sistemas.py"] + list(args), cwd=str(self.kit), env=env,
                              capture_output=True, text=True)

    def limpar(self):
        shutil.rmtree(self.home, ignore_errors=True)


class Kits:
    pasta = None
    kit = None

    @classmethod
    def preparar(cls):
        if cls.pasta:
            return
        cls.pasta = Path(tempfile.mkdtemp(prefix="kit-revisao-"))
        montar.SAIDA = cls.pasta / "saida"
        m = base.manifesto_base("teste-revisao-mac", "mac")
        m["sistemas"] = sistemas_com_revisao()
        m["combinado"]["responsavel_root"] = "Renata Lima"
        cls.kit = base.montar_kit(cls.pasta, m)
        mw = base.manifesto_base("teste-revisao-win", "windows")
        mw["sistemas"] = sistemas_com_revisao()
        cls.kit_win = base.montar_kit(cls.pasta, mw)


def setUpModule():
    Kits.preparar()


def tearDownModule():
    base.Kits.limpar()
    if Kits.pasta:
        shutil.rmtree(Kits.pasta, ignore_errors=True)


class KitMontado(unittest.TestCase):
    def test_kit_claude_leva_o_roteiro_e_a_skill(self):
        self.assertTrue((Kits.kit / "ferramentas" / "revisar_sistemas.py").exists())
        skill = (Kits.kit / ".claude" / "skills" / "revisar-sistemas" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("revisar_sistemas.py", skill)
        self.assertIn("relatorio-revisao.txt", skill)

    def test_skill_sem_travessao_e_windows_sem_python3(self):
        self.assertNotIn("—", (MODELO / ".claude" / "skills" / "revisar-sistemas" / "SKILL.md").read_text(encoding="utf-8"))
        skill = (Kits.kit_win / ".claude" / "skills" / "revisar-sistemas" / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("python3 ", skill)

    def test_sistemas_json_leva_erros_e_responsavel(self):
        s = json.loads((Kits.kit / ".root" / "sistemas.json").read_text(encoding="utf-8"))
        self.assertEqual(len(s["erros"]), 2)
        self.assertTrue(s["_responsavel"])


class Roteiro(unittest.TestCase):
    def ambiente(self, **kw):
        a = Ambiente(Kits.kit, **kw)
        self.addCleanup(a.limpar)
        return a

    def test_tudo_certo(self):
        a = self.ambiente()
        r = a.rodar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Tudo certo", r.stdout)
        relatorio = (Kits.kit / "relatorio-revisao.txt").read_text(encoding="utf-8")
        for trecho in ("Claude Code", "2.1.314", "uv", "0.9.9", "plugin Exemplo", "1.5.0", "Login do ERP"):
            self.assertIn(trecho, relatorio)
        self.assertLessEqual(len(relatorio.splitlines()), 40, "o relatório é curto")

    def test_nunca_mostra_segredo_nem_valor_de_credencial(self):
        a = self.ambiente()
        r = a.rodar(FAKE_SAIDA="login de pessoa@exemplo.com falhou", FAKE_CODIGO="1")
        relatorio = (Kits.kit / "relatorio-revisao.txt").read_text(encoding="utf-8")
        for texto in (r.stdout, r.stderr, relatorio):
            self.assertNotIn(SEGREDO, texto)
            self.assertNotIn("chave-publica", texto)
            self.assertNotIn("pessoa@exemplo.com", texto)

    def test_uv_ausente(self):
        r = self.ambiente(uv=False).rodar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("[falta] uv", r.stdout)
        self.assertIn("docs.astral.sh/uv", r.stdout)

    def test_claude_de_terminal_ausente_e_aviso_e_nao_falha(self):
        r = self.ambiente(claude=False).rodar()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("[aviso] Claude Code", r.stdout)

    def test_plugin_ausente_diz_os_comandos(self):
        r = self.ambiente(plugin=None).rodar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("[falta] plugin Exemplo", r.stdout)
        self.assertIn("/plugin marketplace add exemplo/plugin-exemplo", r.stdout)
        self.assertIn("/plugin install exemplo@exemplo", r.stdout)
        self.assertIn("conversa nova", r.stdout)

    def test_plugin_desatualizado(self):
        r = self.ambiente(plugin="1.3.0").rodar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("1.3.0", r.stdout)
        self.assertIn("1.5.0", r.stdout)
        self.assertIn("/plugin marketplace update exemplo", r.stdout)

    def test_versao_compara_como_numero(self):
        r = self.ambiente(plugin="1.10.0").rodar()
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_credencial_ausente_diz_so_o_nome_do_campo(self):
        r = self.ambiente(credencial=False).rodar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("[falta] Login do ERP", r.stdout)
        self.assertIn("ERP_PASSWORD", r.stdout)
        self.assertIn("--gravar-credencial erp", r.stdout)

    def test_linha_grudada_na_credencial(self):
        a = self.ambiente()
        a.gravar_env("ERP_EMAIL='pessoa@exemplo.com'\nERP_PASSWORD={}ERP_ANON_KEY=chave-publica\n".format(SEGREDO))
        r = a.rodar()
        self.assertEqual(r.returncode, 1)
        self.assertIn("grudad", r.stdout)
        self.assertNotIn(SEGREDO, r.stdout)

    def test_teste_do_plugin_falha_com_erro_conhecido(self):
        r = self.ambiente().rodar(FAKE_SAIDA="AuthApiError: Invalid login credentials", FAKE_CODIGO="1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("[falta] teste do plugin Exemplo", r.stdout)
        self.assertIn("O sistema recusou o e-mail ou a senha gravados.", r.stdout)
        self.assertIn("Grave a senha de novo pela janela do kit.", r.stdout)

    def test_teste_do_plugin_falha_com_erro_desconhecido(self):
        r = self.ambiente().rodar(FAKE_SAIDA="KeyError: 'x'", FAKE_CODIGO="1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("KeyError", (Kits.kit / "relatorio-revisao.txt").read_text(encoding="utf-8"))

    def test_sem_teste_nao_roda_o_plugin(self):
        r = self.ambiente().rodar("--sem-teste", FAKE_CODIGO="1")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("[aviso] teste do plugin Exemplo", r.stdout)

    def test_conector_sem_prova_e_aviso_para_a_conversa(self):
        r = self.ambiente().rodar()
        self.assertIn("[aviso] conector ERP Exemplo", r.stdout)
        self.assertIn("erp_listar", r.stdout)

    def test_json(self):
        r = self.ambiente(plugin=None).rodar("--json")
        d = json.loads(r.stdout)
        self.assertFalse(d["tudo_certo"])
        self.assertEqual({i["situacao"] for i in d["itens"]} - {"ok", "aviso", "falta"}, set())
        self.assertTrue(any(i["id"] == "plugin:exemplo" and i["situacao"] == "falta" for i in d["itens"]))

    def test_explicar_erro_do_manifesto(self):
        r = self.ambiente().rodar("--explicar", "HTTP 403 forbidden_write_admin_only request_id=abc")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Esta empresa não aceita gravação feita por operador.", r.stdout)
        self.assertIn("Quem resolve:", r.stdout)
        self.assertIn("Renata Lima", r.stdout)

    def test_explicar_erro_desconhecido(self):
        r = self.ambiente().rodar("--explicar", "erro que ninguém catalogou")
        self.assertEqual(r.returncode, 1)
        self.assertIn("não está na lista", r.stdout)

    def test_relatorio_separa_o_que_e_do_responsavel(self):
        r = self.ambiente().rodar(FAKE_SAIDA="403 forbidden_write_admin_only", FAKE_CODIGO="1")
        relatorio = (Kits.kit / "relatorio-revisao.txt").read_text(encoding="utf-8")
        self.assertIn("Para Renata Lima decidir", relatorio)
        self.assertEqual(r.returncode, 1)


MANIFESTO_REVISAO = {
    "nome": "exemplo", "empresa": "Empresa Exemplo", "responsavel": "Renata Lima", "canal": "WhatsApp com a Renata",
    "pessoas": [
        {"slug": "caio-prates", "nome": "Caio Prates", "primeiro_nome": "Caio", "email": "caio@exemplo.com", "sistema": "windows"},
        {"slug": "lia-souto", "nome": "Lia Souto", "primeiro_nome": "Lia", "email": "lia@exemplo.com", "sistema": "mac"},
    ],
}


class KitDeRevisao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import revisao
        cls.revisao = revisao
        cls.pasta = Path(tempfile.mkdtemp(prefix="kit-de-revisao-"))
        revisao.SAIDA = cls.pasta / "saida"
        m = json.loads(json.dumps(MANIFESTO_REVISAO))
        m["sistemas"] = sistemas_com_revisao()
        m["sistemas"]["credenciais"][0]["campos"][0]["valor"] = "{email}"
        cls.manifesto = cls.pasta / "revisao-exemplo.json"
        cls.manifesto.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        with open(os.devnull, "w") as nulo:
            saida, sys.stdout = sys.stdout, nulo
            try:
                cls.kits = revisao.montar_revisao(str(cls.manifesto), {"--zip"})
            finally:
                sys.stdout = saida

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.pasta, ignore_errors=True)

    def test_um_kit_por_pessoa_com_as_pecas(self):
        self.assertEqual([k.name for k in self.kits], ["revisao-caio-prates", "revisao-lia-souto"])
        for kit in self.kits:
            for rel in ("LEIA-ME.md", "CLAUDE.md", ".claude/settings.json", ".claude/skills/revisar-sistemas/SKILL.md",
                        "ferramentas/revisar_sistemas.py", "ferramentas/sistemas.py", "instalar/pedir-segredo.ps1", ".root/sistemas.json"):
                self.assertTrue((kit / rel).exists(), "{}: {}".format(kit.name, rel))
            self.assertTrue(kit.with_suffix(".zip").exists())

    def test_sem_chave_sem_git_sem_dado_de_outra_pessoa(self):
        caio = self.kits[0]
        nomes = [str(p.relative_to(caio)) for p in caio.rglob("*")]
        self.assertFalse([n for n in nomes if ".git" in n.split(os.sep) or "chave" in n.lower() or n.endswith(".pem")], nomes)
        texto = "\n".join(p.read_text(encoding="utf-8") for p in caio.rglob("*") if p.is_file())
        self.assertIn("caio@exemplo.com", texto)
        self.assertNotIn("lia@exemplo.com", texto)
        self.assertNotIn("Lia", texto)
        self.assertNotIn("{email}", texto)

    def test_zip_tem_a_pasta_da_pessoa(self):
        with zipfile.ZipFile(self.kits[1].with_suffix(".zip")) as z:
            nomes = z.namelist()
        self.assertIn("revisao-lia-souto/LEIA-ME.md", nomes)
        self.assertIn("revisao-lia-souto/ferramentas/revisar_sistemas.py", nomes)

    def test_trava_de_gravacao_vai_junto(self):
        cfg = json.loads((self.kits[0] / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("mcp__plugin_exemplo_exemplo-erp__incluir_conta", cfg["permissions"]["ask"])
        self.assertIn("mcp__*__erp_executar", cfg["permissions"]["ask"])

    def test_texto_para_a_pessoa(self):
        for kit in self.kits:
            for rel in ("LEIA-ME.md", "CLAUDE.md"):
                texto = (kit / rel).read_text(encoding="utf-8")
                self.assertNotIn("—", texto)
                self.assertNotIn("{{", texto)
                self.assertIn("Renata Lima", texto)
        win = "\n".join((self.kits[0] / rel).read_text(encoding="utf-8") for rel in
                        ("LEIA-ME.md", "CLAUDE.md", ".claude/skills/revisar-sistemas/SKILL.md"))
        self.assertNotIn("python3 ", win)
        self.assertNotIn(".venv", win)
        self.assertIn("python3 ", (self.kits[1] / ".claude" / "skills" / "revisar-sistemas" / "SKILL.md").read_text(encoding="utf-8"))

    def test_roteiro_roda_dentro_do_kit_de_revisao(self):
        a = Ambiente(self.kits[1])
        self.addCleanup(a.limpar)
        r = a.rodar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Renata Lima", (self.kits[1] / "relatorio-revisao.txt").read_text(encoding="utf-8"))

    def recusa(self, mexer):
        m = json.loads(self.manifesto.read_text(encoding="utf-8"))
        mexer(m)
        arq = self.pasta / "ruim.json"
        arq.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        with self.assertRaises(montar.Recusa):
            self.revisao.montar_revisao(str(arq), set())

    def test_portoes(self):
        self.recusa(lambda m: m["sistemas"]["credenciais"][0]["campos"][2].update(valor="123"))
        self.recusa(lambda m: m.pop("responsavel"))
        self.recusa(lambda m: m["pessoas"][0].update(sistema="amiga"))
        self.recusa(lambda m: m["pessoas"][0].update(email="sem-arroba"))
        self.recusa(lambda m: m.update(pessoas=[]))
        self.recusa(lambda m: m["pessoas"].append(dict(m["pessoas"][0])))


if __name__ == "__main__":
    unittest.main()
