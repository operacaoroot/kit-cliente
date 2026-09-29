#!/usr/bin/env python3
"""Testes da base do kit: ambiente, instaladores, catálogo de ferramentas e oficina.

Uso (na raiz do kit-cliente):
    python3 testes/testar_base.py            # tudo
    python3 testes/testar_base.py -v         # com o nome de cada teste

Monta kits de teste numa pasta temporária a partir de uma CÓPIA do manifesto de exemplo,
com outro slug: nunca toca em saida/ nem no manifesto publicado. Não usa rede e não instala
nada. O PowerShell só é conferido se houver `pwsh` no PATH (ou em PWSH=<caminho>).
Só biblioteca padrão, compatível com Python 3.9.
"""
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

MODELO = RAIZ / "modelo"
PERFIS = ("guiado", "chat", "construtor")
SISTEMAS = ("mac", "windows", "linux")
NIVEIS = ("obrigatorio", "recomendado", "opcional")
TIPOS_MAC = {"xcode-clt", "script", "uv-python", "dmg-github", "zip-app", "pagina"}


def py(kit, *args, check=False):
    r = subprocess.run([sys.executable] + list(args), cwd=str(kit), capture_output=True, text=True)
    if check and r.returncode != 0:
        raise AssertionError("{} falhou:\n{}{}".format(" ".join(args), r.stdout, r.stderr))
    return r


class Kits:
    """Monta um kit de teste por sistema, uma vez para a suíte inteira."""
    pasta = None
    kits = {}

    @classmethod
    def preparar(cls):
        if cls.pasta:
            return
        cls.pasta = Path(tempfile.mkdtemp(prefix="kit-teste-"))
        montar.SAIDA = cls.pasta / "saida"
        base = json.loads((RAIZ / "manifestos" / "exemplo-marina-duarte.json").read_text(encoding="utf-8"))
        for sistema in ("mac", "windows"):
            m = json.loads(json.dumps(base))
            m["cliente"]["slug"] = "teste-base-" + sistema
            m["cliente"]["sistema"] = sistema
            m.pop("entrega", None)
            arq = cls.pasta / ("manifesto-" + sistema + ".json")
            arq.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
            with open(os.devnull, "w") as nulo:
                saida_padrao, sys.stdout = sys.stdout, nulo
                try:
                    cls.kits[sistema] = montar.montar(str(arq), {"--rascunho", "--permitir-semente"})
                finally:
                    sys.stdout = saida_padrao

    @classmethod
    def limpar(cls):
        if cls.pasta:
            shutil.rmtree(cls.pasta, ignore_errors=True)


def setUpModule():
    Kits.preparar()


def tearDownModule():
    Kits.limpar()


class CatalogoDeApps(unittest.TestCase):
    def setUp(self):
        self.apps = json.loads((MODELO / "ambiente" / "apps.json").read_text(encoding="utf-8"))["apps"]

    def test_campos_e_niveis(self):
        ids = [a["id"] for a in self.apps]
        self.assertEqual(len(ids), len(set(ids)), "id repetido no catálogo")
        for a in self.apps:
            for campo in ("id", "nome", "para_que", "perfis"):
                self.assertTrue(a.get(campo), "{} sem {}".format(a.get("id"), campo))
            self.assertEqual(set(a["perfis"]), set(PERFIS), a["id"])
            self.assertTrue(set(a["perfis"].values()) <= set(NIVEIS), a["id"])
            for s in SISTEMAS:
                self.assertIn("checar", a[s], "{} sem checar em {}".format(a["id"], s))
                self.assertIn("instalar", a[s], "{} sem instalar em {}".format(a["id"], s))

    def test_obrigatorios_sao_os_mesmos_em_todo_perfil(self):
        for a in self.apps:
            if "obrigatorio" in a["perfis"].values():
                self.assertEqual(set(a["perfis"].values()), {"obrigatorio"}, a["id"])
        obrig = {a["id"] for a in self.apps if a["perfis"]["chat"] == "obrigatorio"}
        self.assertEqual(obrig, {"git", "uv", "python", "claude-code", "obsidian"})

    def test_todo_app_se_instala_no_windows_e_no_mac(self):
        for a in self.apps:
            w = a["windows"]["instalar"]
            self.assertTrue(w.get("winget") or w.get("tipo") in ("script", "uv-python", "pagina"), a["id"])
            self.assertIn(a["mac"]["instalar"]["tipo"], TIPOS_MAC, a["id"])
            if a["mac"]["instalar"]["tipo"] in ("script", "zip-app", "pagina"):
                self.assertTrue(a["mac"]["instalar"]["url"].startswith("https://"), a["id"])


class Instaladores(unittest.TestCase):
    def test_powershell_e_cmd_sao_ascii(self):
        for nome in ("instalar.ps1", "instalar.cmd"):
            dados = (MODELO / "instalar" / nome).read_bytes()
            fora = [i for i, b in enumerate(dados) if b > 127]
            self.assertEqual(fora, [], "{} tem caractere fora do ASCII (PowerShell 5.1 quebra)".format(nome))

    def test_cmd_tem_fim_de_linha_do_windows(self):
        dados = (MODELO / "instalar" / "instalar.cmd").read_bytes()
        self.assertEqual(dados.count(b"\n"), dados.count(b"\r\n"))

    def test_sh_tem_sintaxe_valida(self):
        r = subprocess.run(["bash", "-n", str(MODELO / "instalar" / "instalar.sh")], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_powershell_tem_sintaxe_valida(self):
        pwsh = os.environ.get("PWSH") or shutil.which("pwsh")
        if not pwsh:
            self.skipTest("sem pwsh nesta máquina")
        script = ("$e=$null;$t=$null;[System.Management.Automation.Language.Parser]::ParseFile('{}',[ref]$t,[ref]$e)|Out-Null;"
                  "if($e.Count){{$e|%{{Write-Output $_.Message}};exit 1}}").format(MODELO / "instalar" / "instalar.ps1")
        r = subprocess.run([pwsh, "-NoProfile", "-Command", script], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class KitMontado(unittest.TestCase):
    def setUp(self):
        self.kit = Kits.kits["mac"]

    def test_pecas_da_base(self):
        for rel in ("catalogo.json", "ambiente/apps.json", "ambiente/requirements.txt", "ferramentas/ambiente.py",
                    "ferramentas/skills.py", "oficina/LEIA-ME.md", "instalar/instalar.cmd",
                    ".claude/skills/preparar-ambiente/SKILL.md", ".claude/skills/criar-skill/SKILL.md"):
            self.assertTrue((self.kit / rel).exists(), rel)

    def test_catalogo_bate_com_as_pastas(self):
        cat = json.loads((self.kit / "catalogo.json").read_text(encoding="utf-8"))
        nomes = {s["nome"] for s in cat["skills"] if s["estado"] == "ativa"}
        pastas = {p.name for p in (self.kit / ".claude" / "skills").iterdir() if p.is_dir()}
        self.assertEqual(nomes, pastas)
        self.assertEqual({s["origem"] for s in cat["skills"]}, {"root", "frente"})
        self.assertEqual(py(self.kit, "ferramentas/skills.py", "listar").returncode, 0)

    def test_comece_aqui_tem_os_sete_passos(self):
        texto = (self.kit / "COMECE-AQUI.md").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r"(?m)^## \d+\. ", texto)), 7)
        self.assertIn("Criar a sua primeira ferramenta", texto)

    def test_conferencia_roda_e_grava_progresso(self):
        py(self.kit, "ferramentas/verificar.py", "--silencioso", "--sem-rede", check=True)
        prog = json.loads((self.kit / ".root" / "progresso.json").read_text(encoding="utf-8"))
        self.assertEqual([p["id"] for p in prog["passos"]],
                         ["instalar", "perfil", "vault", "contexto", "primeira-frente", "primeira-skill", "fechar-o-dia"])

    def test_ambiente_conferir_em_json(self):
        r = py(self.kit, "ferramentas/ambiente.py", "--conferir", "--json")
        conf = json.loads(r.stdout)
        self.assertEqual(conf["perfil"], "chat")
        self.assertEqual(len(conf["apps"]), 10)

    def test_chave_e_venv_fora_do_git(self):
        ignorado = (self.kit / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".venv/", ignorado)
        r = subprocess.run(["git", "ls-files"], cwd=str(self.kit), capture_output=True, text=True)
        self.assertFalse([l for l in r.stdout.splitlines() if l.startswith((".root/chave", ".venv/"))])

    def test_texto_novo_sem_travessao(self):
        for rel in (".claude/skills/preparar-ambiente/SKILL.md", ".claude/skills/criar-skill/SKILL.md",
                    "oficina/LEIA-ME.md", "README.md", "CLAUDE.md", "COMECE-AQUI.md"):
            self.assertNotIn("—", (self.kit / rel).read_text(encoding="utf-8"), rel)


class KitWindows(unittest.TestCase):
    def test_nenhum_python3_nos_textos(self):
        kit = Kits.kits["windows"]
        for md in kit.rglob("*.md"):
            self.assertNotIn("python3 ", md.read_text(encoding="utf-8"), md.relative_to(kit).as_posix())
        skill = (kit / ".claude" / "skills" / "proximo-passo" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(".venv/Scripts/python ferramentas/verificar.py", skill)
        comece = (kit / "COMECE-AQUI.md").read_text(encoding="utf-8")
        self.assertIn("instalar\\instalar.cmd", comece)

    def test_permissoes_cobrem_o_python_do_windows(self):
        cfg = json.loads((Kits.kits["windows"] / ".claude" / "settings.json").read_text(encoding="utf-8"))
        for ferramenta in ("verificar", "ambiente", "skills"):
            self.assertIn("Bash(.venv/Scripts/python ferramentas/{}.py:*)".format(ferramenta), cfg["permissions"]["allow"])


class Oficina(unittest.TestCase):
    """O ciclo completo de uma ferramenta do cliente, num kit copiado."""

    @classmethod
    def setUpClass(cls):
        cls.kit = Kits.pasta / "oficina-mac"
        if cls.kit.exists():
            shutil.rmtree(cls.kit)
        shutil.copytree(Kits.kits["mac"], cls.kit)

    def escrever(self, nome, corpo_extra="", resultado="aprovado"):
        pasta = self.kit / "oficina" / nome
        (pasta / "SKILL.md").write_text(
            "---\nname: {n}\ndescription: Resume as reuniões da semana num quadro de decisões e pendências. "
            "Use quando a pessoa pedir o resumo da semana.\n---\n\n# Resumo da semana\n\n## Quando usar\n\n"
            "Na sexta, com as atas da semana em entrada/atas.\n\n## Como fazer\n\n1. Ler cada ata.\n"
            "2. Separar decisão de pendência.\n3. Montar o quadro.\n\n## Como entregar\n\n"
            "entregas/AAAA-MM-DD - resumo.md, sempre rascunho.\n{x}\n".format(n=nome, x=corpo_extra), encoding="utf-8")
        (pasta / "TESTES.md").write_text(
            "# Testes\n\n## Teste 1 · 2026-09-29\n\n- Caso: atas da semana de um time comercial\n"
            "- Pedido: resumo da semana\n- Resultado: {}\n- O que ajustou: nada\n".format(resultado), encoding="utf-8")

    def cat(self):
        return {s["nome"]: s for s in json.loads((self.kit / "catalogo.json").read_text(encoding="utf-8"))["skills"]}

    def test_1_ciclo_completo(self):
        r = py(self.kit, "ferramentas/skills.py", "nova", "resumo-da-semana", "Resume as reuniões da semana em decisões e pendências")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(self.cat()["resumo-da-semana"]["estado"], "homologacao")
        self.assertEqual(py(self.kit, "ferramentas/skills.py", "conferir", "resumo-da-semana").returncode, 1,
                         "o modelo em branco não pode passar na conferência")
        self.escrever("resumo-da-semana", resultado="reprovado")
        self.assertEqual(py(self.kit, "ferramentas/skills.py", "conferir", "resumo-da-semana").returncode, 1,
                         "último teste reprovado não pode passar")
        self.escrever("resumo-da-semana")
        py(self.kit, "ferramentas/skills.py", "conferir", "resumo-da-semana", check=True)
        py(self.kit, "ferramentas/skills.py", "promover", "resumo-da-semana", check=True)
        self.assertTrue((self.kit / ".claude" / "skills" / "resumo-da-semana" / "SKILL.md").exists())
        self.assertEqual(self.cat()["resumo-da-semana"]["versao"], "1.0.0")
        py(self.kit, "ferramentas/verificar.py", "--silencioso", "--sem-rede", check=True)
        prog = {p["id"]: p for p in json.loads((self.kit / ".root" / "progresso.json").read_text(encoding="utf-8"))["passos"]}
        self.assertTrue(prog["primeira-skill"]["feito"], prog["primeira-skill"]["detalhe"])

        py(self.kit, "ferramentas/skills.py", "melhorar", "resumo-da-semana", check=True)
        self.assertTrue(self.cat()["resumo-da-semana"].get("rascunho_na_oficina"))
        py(self.kit, "ferramentas/skills.py", "promover", "resumo-da-semana", check=True)
        self.assertEqual(self.cat()["resumo-da-semana"]["versao"], "1.1.0")
        self.assertTrue(any(p.name.startswith("resumo-da-semana-v1.0.0") for p in (self.kit / "oficina" / "_aposentadas").iterdir()))

        py(self.kit, "ferramentas/skills.py", "aposentar", "resumo-da-semana", check=True)
        self.assertEqual(self.cat()["resumo-da-semana"]["estado"], "aposentada")
        self.assertFalse((self.kit / ".claude" / "skills" / "resumo-da-semana").exists())
        self.assertEqual(py(self.kit, "ferramentas/skills.py", "listar").returncode, 0)

    def test_2_segredo_e_caminho_da_maquina_barram(self):
        py(self.kit, "ferramentas/skills.py", "nova", "com-segredo", "Ferramenta de teste que carrega um segredo no texto", check=True)
        self.escrever("com-segredo", "\nsenha: abc12345xyz\nArquivo em /Users/fulano/Desktop/x.pdf\n")
        r = py(self.kit, "ferramentas/skills.py", "conferir", "com-segredo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("senha ou token", r.stdout)
        self.assertIn("caminho desta máquina", r.stdout)
        self.assertNotEqual(py(self.kit, "ferramentas/skills.py", "promover", "com-segredo").returncode, 0)

    def test_3_ferramenta_da_root_nao_se_edita(self):
        r = py(self.kit, "ferramentas/skills.py", "melhorar", "proximo-passo")
        self.assertEqual(r.returncode, 1)
        self.assertIn("--a-partir-de", r.stdout)
        py(self.kit, "ferramentas/skills.py", "nova", "meu-proximo-passo", "O próximo passo do meu jeito, mais curto", "--a-partir-de", "proximo-passo", check=True)
        texto = (self.kit / "oficina" / "meu-proximo-passo" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: meu-proximo-passo", texto)
        self.assertNotRegex(texto, r"<!-- kit-[0-9a-f]+ -->")

    def test_4_nome_invalido(self):
        self.assertEqual(py(self.kit, "ferramentas/skills.py", "nova", "Meu Nome", "Uma ferramenta com nome errado de propósito").returncode, 1)


class AtualizacaoDoCatalogo(unittest.TestCase):
    def test_mantem_as_do_cliente_e_refaz_as_da_root(self):
        existente = {"skills": [
            {"nome": "proximo-passo", "origem": "root", "estado": "ativa", "versao": "1.0.0", "desde": "2026-09-27"},
            {"nome": "skill-que-saiu", "origem": "root", "estado": "ativa", "versao": "1.0.0"},
            {"nome": "minha", "origem": "cliente", "estado": "ativa", "versao": "1.2.0"},
        ]}
        novo = montar.montar_catalogo([], "1.1.0", existente)
        por_nome = {s["nome"]: s for s in novo["skills"]}
        self.assertEqual(por_nome["minha"]["versao"], "1.2.0")
        self.assertEqual(por_nome["proximo-passo"]["versao"], "1.1.0")
        self.assertEqual(por_nome["proximo-passo"]["desde"], "2026-09-27")
        self.assertNotIn("skill-que-saiu", por_nome)
        self.assertIn("criar-skill", por_nome)


if __name__ == "__main__":
    unittest.main()
