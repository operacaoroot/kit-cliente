#!/usr/bin/env python3
"""Exercita o exit code do instalador sem instalar apps nem acessar serviços.

As ferramentas do kit são dublês; o instalador e a parte Codex são os arquivos reais.
O teste Windows aqui é apenas de sintaxe, quando pwsh estiver disponível.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

RAIZ = Path(__file__).resolve().parent.parent

FERRAMENTA = '''import json,os,sys
from pathlib import Path
nome=Path(__file__).stem
etapa=nome+(':'+sys.argv[1] if len(sys.argv)>1 else '')
falha=os.environ.get('FALHA_TESTE','')
if nome=='verificar':
    if falha=='progresso-ausente':
        sys.exit(0)
    pronto=falha not in ('mcp:--registrar','instalar-pendente')
    Path('.root/progresso.json').write_text(json.dumps({'passos':[
        {'id':'instalar','feito':pronto},
        {'id':'perfil','feito':False},
        {'id':'primeira-frente','feito':False}]}))
sys.exit(1 if etapa==falha or (nome=='conectar' and falha=='github-sem-acesso') else 0)
'''


class ResultadoInstalador(unittest.TestCase):
    def executar(self, falha='', github=None):
        with tempfile.TemporaryDirectory(prefix='kit-instalar-resultado-') as pasta:
            raiz = Path(pasta)
            kit = raiz / 'kit'
            for nome in ('instalar', 'ferramentas', '.root'):
                (kit / nome).mkdir(parents=True)
            shutil.copy2(RAIZ / 'modelo/instalar/instalar.sh', kit / 'instalar/instalar.sh')
            shutil.copy2(RAIZ / 'modelo/instalar/agente-codex.sh', kit / 'instalar/agente.sh')
            (kit / '.root/cliente.json').write_text(json.dumps({'mcp': {'nome': 'teste'}, 'github': github}))
            for nome in ('ambiente', 'conectar', 'mcp', 'verificar'):
                (kit / 'ferramentas' / (nome + '.py')).write_text(FERRAMENTA)
            bin_dir = raiz / 'bin'
            bin_dir.mkdir()
            # Usa Linux no dublê para não criar atalhos nem abrir janelas da Apple.
            comandos = {'uname': '#!/bin/sh\necho Linux\n', 'git': '#!/bin/sh\nexit 0\n',
                        'python3': '#!/bin/sh\nexec "{}" "$@"\n'.format(sys.executable)}
            for nome, texto in comandos.items():
                arq = bin_dir / nome
                arq.write_text(texto)
                arq.chmod(0o755)
            casa = raiz / 'home'
            casa.mkdir()
            env = dict(os.environ, HOME=str(casa), PATH=str(bin_dir)+':/usr/bin:/bin', FALHA_TESTE=falha)
            return subprocess.run(['bash', str(kit/'instalar/instalar.sh')], env=env, capture_output=True, text=True)

    def test_instalacao_pronta_nao_exige_onboarding_completo(self):
        resultado = self.executar()
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_falhas_de_instalacao_nao_terminam_com_sucesso(self):
        for etapa in ('ambiente:--instalar', 'ambiente:--venv', 'conectar:--usar-chave',
                      'mcp:--registrar', 'ambiente:--conferir', 'verificar',
                      'instalar-pendente', 'progresso-ausente'):
            with self.subTest(etapa=etapa):
                resultado = self.executar(etapa)
                self.assertNotEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_fallback_github_funciona_quando_chave_funciona(self):
        resultado = self.executar('conectar:--conectar', github='pessoa-teste')
        self.assertEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    def test_fallback_github_falha_quando_nenhum_acesso_funciona(self):
        resultado = self.executar('github-sem-acesso', github='pessoa-teste')
        self.assertNotEqual(resultado.returncode, 0, resultado.stdout + resultado.stderr)

    @unittest.skipUnless(Path('/usr/bin/python3').exists(), 'entrada macOS requer Python da Apple')
    def test_entrada_command_preserva_erro_do_instalador(self):
        with tempfile.TemporaryDirectory(prefix='kit-command-resultado-') as pasta:
            kit = Path(pasta)
            (kit / 'instalar').mkdir()
            (kit / '.root').mkdir()
            (kit / '.root/cliente.json').write_text('{"agente":"codex"}')
            shutil.copy2(RAIZ / 'modelo/instalar/instalar.command', kit / 'instalar/instalar.command')
            (kit / 'instalar/instalar.sh').write_text('#!/bin/sh\nexit 7\n')
            bin_dir = kit / 'bin'
            bin_dir.mkdir()
            xcode = bin_dir / 'xcode-select'
            xcode.write_text('#!/bin/sh\nexit 0\n')
            xcode.chmod(0o755)
            env = dict(os.environ, PATH=str(bin_dir)+':/usr/bin:/bin')
            resultado = subprocess.run(['bash',str(kit/'instalar/instalar.command')],
                                       env=env,input='\n',capture_output=True,text=True)
            self.assertEqual(resultado.returncode, 7, resultado.stdout+resultado.stderr)

    @unittest.skipUnless(shutil.which('pwsh'), 'pwsh ausente; instalador Windows não executado')
    def test_sintaxe_windows(self):
        arq = str(RAIZ / 'modelo/instalar/instalar.ps1').replace("'", "''")
        comando = "$t=$null;$e=$null;[void][System.Management.Automation.Language.Parser]::ParseFile('{}',[ref]$t,[ref]$e);if($e.Count){{$e;exit 1}}".format(arq)
        resultado = subprocess.run(['pwsh','-NoProfile','-Command',comando], capture_output=True,text=True)
        self.assertEqual(resultado.returncode, 0, resultado.stdout+resultado.stderr)


if __name__ == '__main__':
    unittest.main()
