'use strict';
// Painel do kit. Abre direto do disco (file://) ou servido pelo onboarding do Mac.
// Lê o estado que ferramentas/painel.py grava em _privado/painel/estado.js e se atualiza sozinho.
(function () {
  const ESTADO = '../_privado/painel/estado.js';
  const MARCAS = {pendente: '○', andamento: '●', ok: '✓', atencao: '!', falhou: '✕'};
  const PALAVRAS = {pendente: 'a fazer', andamento: 'em andamento', ok: 'feito', atencao: 'com pendência', falhou: 'não deu certo'};
  const $ = s => document.querySelector(s);
  let ultimo = '';
  let comQuery = true;
  let leituras = 0;

  // Navegador com armazenamento bloqueado não pode derrubar a página.
  const guardado = {ler: k => { try { return localStorage.getItem(k); } catch (e) { return null; } },
                    gravar: (k, v) => { try { localStorage.setItem(k, v); } catch (e) { /* segue sem lembrar */ } }};
  const tema = guardado.ler('root-tema-painel');
  if (tema === 'papel' || tema === 'escuro') { document.documentElement.dataset.theme = tema; $('#tema').value = tema; }
  $('#tema').onchange = () => { document.documentElement.dataset.theme = $('#tema').value; guardado.gravar('root-tema-painel', $('#tema').value); };

  function item(lista, texto, classe) {
    const li = document.createElement('li');
    if (classe) li.className = classe;
    li.textContent = texto;
    lista.append(li);
    return li;
  }

  function linkClaude(pasta, mensagem) {
    return 'claude://code/new?folder=' + encodeURIComponent(pasta || '') + '&q=' + encodeURIComponent(mensagem || '');
  }

  function copiar(texto, botao) {
    const feito = () => { const antes = botao.textContent; botao.textContent = 'Copiado'; setTimeout(() => { botao.textContent = antes; }, 1800); };
    const reserva = () => {
      const area = document.createElement('textarea');
      area.value = texto; area.setAttribute('readonly', ''); area.className = 'fora';
      document.body.append(area); area.select();
      try { document.execCommand('copy'); feito(); } catch (e) { botao.textContent = 'Selecione e copie à mão'; }
      area.remove();
    };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(texto).then(feito, reserva);
    else reserva();
  }

  function agente(s) { return s.agente_nome || 'Claude'; }

  function trocar(texto, s) {
    const valores = {'{pasta}': s.pasta || 'a pasta do kit', '{vault}': s.vault || 'a pasta vault do kit',
                     '{agente}': agente(s), '{instrucoes}': s.agente === 'codex' ? 'AGENTS.md' : 'CLAUDE.md'};
    return Object.keys(valores).reduce((t, k) => t.split(k).join(valores[k]), texto || '');
  }

  function proximos(s) {
    const lista = $('#proximos');
    lista.replaceChildren();
    const comLink = (s.agente || 'claude') === 'claude';
    $('#nota-passos').textContent = comLink
      ? 'Cada passo traz o texto pronto para você mandar ao Claude. Use Abrir no Claude; se não abrir, use Copiar texto e cole no Claude, na área Code, com a pasta do kit aberta.'
      : 'Cada passo traz o texto pronto para você mandar ao ' + agente(s) + '. Use Copiar texto e cole no ' + agente(s) + ', aberto na pasta do kit pelo atalho ' + agente(s) + ' do kit.';
    (window.KIT_PRIMEIROS_PASSOS || []).forEach(p => {
      const li = document.createElement('li');
      li.className = 'cartao';
      const h = document.createElement('h3'); h.textContent = trocar(p.titulo, s); li.append(h);
      const porque = document.createElement('p'); porque.textContent = trocar(p.porque, s); li.append(porque);
      if (p.como) { const como = document.createElement('p'); como.className = 'como'; como.textContent = trocar(p.como, s); li.append(como); }
      const acoes = document.createElement('div'); acoes.className = 'acoes';
      if (p.prompt) {
        const texto = trocar(p.prompt, s);
        const pre = document.createElement('pre'); pre.textContent = texto; li.append(pre);
        if (comLink) {
          const abrir = document.createElement('a'); abrir.className = 'botao primario'; abrir.textContent = 'Abrir no Claude';
          abrir.href = linkClaude(s.pasta, texto); acoes.append(abrir);
        }
        const botao = document.createElement('button'); botao.type = 'button'; botao.textContent = 'Copiar texto';
        if (!comLink) botao.className = 'botao primario';
        botao.onclick = () => copiar(texto, botao); acoes.append(botao);
      }
      if (p.acao === 'obsidian') {
        const obs = document.createElement('a'); obs.className = 'botao primario'; obs.textContent = 'Abrir no Obsidian';
        obs.href = (s.links && s.links.obsidian) || 'obsidian://open'; acoes.append(obs);
        const escolher = document.createElement('a'); escolher.className = 'botao'; escolher.textContent = 'Escolher a pasta do cofre';
        escolher.href = 'obsidian://choose-vault'; acoes.append(escolher);
      }
      li.append(acoes);
      lista.append(li);
    });
  }

  function minutosDesde(iso) {
    const t = Date.parse(iso || '');
    return isNaN(t) ? 0 : (Date.now() - t) / 60000;
  }

  function avisoDeParado(s) {
    // Fora do "nada mudou": o aviso existe justamente para quando o estado para de mudar.
    const parado = s.fase === 'instalando' && minutosDesde(s.atualizado) > 45;
    $('#aviso').hidden = !parado;
    $('#aviso').textContent = parado ? 'Faz mais de 45 minutos que o instalador não manda notícia. Se a janela preta do instalador ainda está aberta, espere: algum download grande pode estar no meio. Se ela fechou, abra o instalador de novo; ele continua de onde parou.' : '';
  }

  function render(s) {
    avisoDeParado(s);
    const chave = JSON.stringify(s);
    if (chave === ultimo) return;
    ultimo = chave;
    $('#nome').textContent = s.nome ? 'Kit de ' + s.nome : '';
    $('#pasta').textContent = s.pasta || '';
    const titulos = {instalando: 'Estamos preparando o seu computador.', pronto: 'Seu kit está pronto. Agora é com você e o Claude.', atencao: 'A instalação terminou, mas ficou algo para resolver.'};
    $('#titulo').textContent = titulos[s.fase] || titulos.instalando;
    document.body.dataset.fase = s.fase || 'instalando';
    $('#agora').textContent = s.agora || '';

    const etapas = s.etapas || [];
    const feitas = etapas.filter(e => e.estado === 'ok').length;
    $('#barra').max = etapas.length || 1;
    $('#barra').value = feitas;
    $('#contagem').textContent = feitas + ' de ' + etapas.length + ' etapas feitas';
    const ol = $('#etapas'); ol.replaceChildren();
    etapas.forEach(e => {
      const li = document.createElement('li'); li.className = 'etapa ' + e.estado;
      const marca = document.createElement('span'); marca.className = 'marca'; marca.textContent = MARCAS[e.estado] || '○'; marca.setAttribute('aria-hidden', 'true');
      const corpo = document.createElement('div');
      const t = document.createElement('strong'); t.textContent = e.titulo; corpo.append(t);
      const st = document.createElement('span'); st.className = 'situacao'; st.textContent = ' · ' + (PALAVRAS[e.estado] || e.estado); corpo.append(st);
      const d = document.createElement('p'); d.textContent = e.detalhe || e.explica || ''; corpo.append(d);
      li.append(marca, corpo); ol.append(li);
    });

    const ul = $('#eventos'); ul.replaceChildren();
    const eventos = (s.eventos || []).slice().reverse();
    if (!eventos.length) item(ul, 'O instalador ainda não registrou nada.', 'vazio');
    eventos.forEach(ev => {
      const li = item(ul, '', ev.tipo);
      const hora = document.createElement('time'); hora.textContent = ev.em; li.append(hora, document.createTextNode(' ' + ev.texto));
    });

    const feito = $('#feito'); const falta = $('#falta');
    feito.replaceChildren(); falta.replaceChildren();
    const c = s.conferencia;
    if (!c) {
      etapas.filter(e => e.estado === 'ok').forEach(e => item(feito, e.titulo + (e.detalhe ? ': ' + e.detalhe : '')));
      if (!feito.children.length) item(feito, 'Ainda nada. As etapas aparecem aqui conforme terminam.', 'vazio');
      etapas.filter(e => e.estado !== 'ok').forEach(e => item(falta, e.titulo));
    } else {
      c.feito.forEach(t => item(feito, t));
      c.falta.forEach(t => item(falta, t));
      if (!c.falta.length) item(falta, 'Nada da instalação. Siga os próximos passos abaixo.', 'vazio');
    }
    item(falta, 'Entrar com a sua conta no ' + agente(s) + ' (é você quem faz)', 'manual');
    proximos(s);
  }

  function vazio() {
    $('#titulo').textContent = 'O instalador ainda não começou.';
    $('#agora').textContent = 'Abra o instalador do kit (pasta instalar) com dois cliques. Esta página acompanha tudo e se atualiza sozinha.';
    proximos({});
  }

  function carregar(semQuery) {
    // Sem ?t= o navegador pode guardar cópia velha: mesmo depois de cair no "sem", tenta de novo a cada 10 leituras.
    leituras += 1;
    const usarQuery = !semQuery && (comQuery || leituras % 10 === 0);
    const s = document.createElement('script');
    s.src = ESTADO + (usarQuery ? '?t=' + Date.now() : '');
    s.onload = () => {
      s.remove();
      if (usarQuery) comQuery = true;
      else if (semQuery) comQuery = false; // este navegador só lê o arquivo sem o ?t=
      if (window.KIT_PAINEL) render(window.KIT_PAINEL); else vazio();
      agendar();
    };
    s.onerror = () => {
      s.remove();
      // Alguns navegadores não aceitam ?t= em arquivo do disco: tenta sem antes de desistir.
      if (usarQuery) return carregar(true);
      if (!window.KIT_PAINEL) vazio();
      agendar();
    };
    document.head.append(s);
  }

  function agendar() {
    const fase = window.KIT_PAINEL && window.KIT_PAINEL.fase;
    setTimeout(carregar, fase && fase !== 'instalando' ? 15000 : 2000);
  }

  carregar();
})();
