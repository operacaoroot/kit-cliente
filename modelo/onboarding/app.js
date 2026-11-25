'use strict';
const token = location.hash.slice(1) || sessionStorage.getItem('onboarding-token');
if (token) sessionStorage.setItem('onboarding-token', token);
history.replaceState(null, '', '/');
const $ = s => document.querySelector(s);
const themes = ['escuro', 'papel', 'mono'];
const savedTheme = localStorage.getItem('root-theme');
$('#theme').value = themes.includes(savedTheme) ? savedTheme : 'escuro';
document.documentElement.dataset.theme = $('#theme').value;
$('#theme').onchange = () => { document.documentElement.dataset.theme = $('#theme').value; localStorage.setItem('root-theme', $('#theme').value); };
let state, initialized = false, sourcesVersion = '', dirty = false;
$('#profile').addEventListener('input', () => { dirty = true; });
function notice(text, error = false, kind = 'neutro') { $('#notice').textContent = text; $('#notice').classList.toggle('error', error || kind === 'erro'); $('#notice').classList.toggle('success', !error && kind === 'ok'); $('#notice').classList.toggle('attention', !error && kind === 'atencao'); }
async function api(path, data) {
  const r = await fetch('/api/' + path, {method: data ? 'POST' : 'GET', headers: {'X-Onboarding-Token': token || '', 'Content-Type': 'application/json'}, ...(data ? {body: JSON.stringify(data)} : {})});
  const value = await r.json();
  if (!r.ok) throw Error(value.erro || 'Não foi possível concluir.');
  return value;
}
function step(n) {
  if (dirty && String(n) !== '0') { notice('Salve seus dados antes de continuar para outra etapa.', true); return; }
  document.querySelectorAll('[data-panel]').forEach(e => e.hidden = e.dataset.panel !== String(n));
  document.querySelectorAll('[data-step]').forEach(e => e.classList.toggle('active', e.dataset.step === String(n)));
  $('#counter').textContent = `${Number(n) + 1} de 5`;
  localStorage.setItem('onboarding-step', n);
  window.scrollTo(0, 0);
}
document.querySelectorAll('[data-step],[data-next]').forEach(b => b.onclick = () => step(b.dataset.step ?? b.dataset.next));
function line(parent, text, ok) { const el = document.createElement('div'); el.className = 'status ' + (ok ? 'ok' : 'pending'); el.textContent = (ok ? '✓ ' : '○ ') + text; parent.append(el); }
function render(s) {
  state = s;
  if (initialized && !s.ocupado && s.perfil_confirmado && [...new FormData($('#profile'))].every(([k,v]) => (s.perfil[k] || '') === v.trim())) dirty = false;
  notice(s.mensagem, false, s.tipo_mensagem);
  if (!initialized) {
    Object.entries(s.perfil).forEach(([k,v]) => {if ($('#profile').elements[k]) $('#profile').elements[k].value = v;});
    dirty = false;
    step(localStorage.getItem('onboarding-step') || (s.revisao ? 2 : s.perfil_confirmado ? 1 : 0)); initialized = true;
  }
  document.querySelectorAll('button:not([data-step]):not([data-next])').forEach(b => b.disabled = s.ocupado);
  $('#profile-review').replaceChildren();
  const labels = {nome:'Nome',cargo:'Atividade',empresa:'Empresa',setor:'Setor',responsabilidades:'Responsabilidades',publico:'Público',objetivo:'Primeira tarefa',tom:'Preferência de explicação',site_pessoal:'Site pessoal',site_empresa:'Site da empresa',redes_pessoais:'Redes pessoais',redes_empresa:'Redes da empresa'};
  for (const [key, value] of Object.entries(s.perfil)) {if (value) {const p = document.createElement('p'); p.textContent = `${labels[key] || key}: ${value}`; $('#profile-review').append(p);}}
  $('#sync').href = s.sincronizar_url;
  $('#folder').textContent = s.pasta; $('#vault-folder').textContent = s.vault_pasta;
  $('#probe').href = s.prova_url; $('#vault').href = s.obsidian_url; $('#daily').href = s.claude_url;
  document.querySelectorAll('.painel-link').forEach(a => { a.href = s.painel_url || '/painel/index.html'; });
  $('#atividade').replaceChildren();
  for (const ev of (s.atividade || [])) { const li = document.createElement('li'); li.className = ev.tipo; li.textContent = ev.em + '  ' + ev.texto; $('#atividade').append(li); }
  if (!(s.atividade || []).length) { const li = document.createElement('li'); li.textContent = 'Nada ainda. A lista começa quando você clicar em Instalar programas.'; $('#atividade').append(li); }
  const version = JSON.stringify(s.fontes);
  if (version !== sourcesVersion) {
    sourcesVersion = version; $('#sources').replaceChildren();
    for (const source of s.fontes) {
      const box = document.createElement('div'); box.className = 'box';
      const title = document.createElement('h2'); title.textContent = source.url; box.append(title);
      const detail = document.createElement('p'); detail.textContent = source.erro || `Lido em ${source.coletado_em}. Confira se o trecho é sobre você ou sua empresa.`; box.append(detail);
      const label = document.createElement('label'); label.className = 'check';
      const check = document.createElement('input'); check.type = 'checkbox'; check.dataset.source = source.id; label.append(check, document.createTextNode('Incluir este trecho após minha revisão')); box.append(label);
      const textarea = document.createElement('textarea'); textarea.rows = 8; textarea.maxLength = 12000; textarea.value = source.texto; textarea.dataset.text = source.id; textarea.setAttribute('aria-label', 'Conteúdo de ' + source.url); box.append(textarea);
      $('#sources').append(box);
    }
  }
  const c = s.conferencia;
  $('#apps').replaceChildren(); $('#results').replaceChildren();
  line($('#results'), 'Dados profissionais confirmados', s.perfil_confirmado);
  line($('#results'), 'Carga inicial revisada e salva no vault', s.revisao);
  if (c) {
    for (const a of c.ambiente.apps.filter(a => a.nivel === 'obrigatorio' || a.id === 'claude-app')) line($('#apps'), a.nome, a.instalado);
    line($('#apps'), 'Ambiente Python do kit', c.ambiente.venv.pronto);
    line($('#results'), 'Programas e ambiente do kit disponíveis', !c.ambiente.faltam_obrigatorios.length && c.ambiente.venv.pronto && c.claude_app);
    line($('#results'), 'Acesso de leitura ao repositório confirmado', c.repositorio);
    line($('#results'), 'Carga inicial e nota de teste sincronizadas com o repositório', c.sincronizado);
    line($('#results'), 'Claude usou o perfil e registrou a prova no vault', c.prova);
    $('#repo').textContent = c.repositorio ? (c.sincronizado ? 'Carga inicial e nota de teste conferidas no repositório.' : 'Acesso de leitura confirmado. Falta enviar a carga inicial e a nota de teste.') : 'Pendente: confira a internet e peça ao Claude para ligar o kit ao GitHub.';
  } else line($('#results'), 'Falta conferir o ambiente e fazer o teste no Claude', false);
  $('#result-title').textContent = c?.pronto ? 'Seu ambiente está pronto para começar.' : 'Vamos conferir o que falta.';
  $('#daily').hidden = !c?.pronto;
}
async function refresh() { try { render(await api('estado')); } catch(e) { notice(e.message + ' Se você fechou o instalador, reabra Continuar onboarding.', true); } }
async function action(name, data) { try { await api(name, data); await refresh(); } catch(e) { notice(e.message, true); } }
$('#profile').onsubmit = e => {e.preventDefault(); action('perfil', Object.fromEntries(new FormData(e.target)));};
$('#collect').onclick = () => action('coletar', {consentimento: $('#consent').checked});
$('#review').onclick = () => {const fontes = {}; document.querySelectorAll('[data-source]:checked').forEach(e => fontes[e.dataset.source] = document.querySelector(`[data-text="${e.dataset.source}"]`).value); action('revisar', {confirmar: $('#review-consent').checked, fontes});};
$('#install').onclick = () => action('instalar', {confirmar: $('#install-consent').checked});
document.querySelectorAll('.refresh').forEach(b => b.onclick = () => action('conferir', {}));
refresh();
setInterval(() => {if (state?.ocupado) refresh();}, 1500);
