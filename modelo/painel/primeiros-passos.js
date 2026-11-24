'use strict';
// Os passos depois da instalação, com o texto pronto para a pessoa mandar ao Claude.
// Arquivo estático: o painel abre direto do disco e o navegador não deixa ler JSON por lá.
// {pasta} e {vault} viram o caminho da pasta do kit e do cofre do Obsidian neste computador.
window.KIT_PRIMEIROS_PASSOS = [
  {
    titulo: 'Abra o Claude na pasta do kit',
    porque: 'É ali que você vai trabalhar. O Claude lê o seu perfil e as regras do kit antes de responder.',
    como: 'No aplicativo do Claude, entre com a sua conta, clique em Code e confirme a pasta do kit. Se o botão Abrir no Claude não funcionar, escolha a pasta à mão: {pasta}',
    prompt: 'Acabei de instalar o kit da Root. Leia o CLAUDE.md e me diga, em poucas linhas, o que já está pronto e qual é o meu próximo passo.'
  },
  {
    titulo: 'Diga ao Claude como você prefere ser atendido',
    porque: 'Ele ajusta o jeito de falar com você: tom, tamanho das respostas, ritmo e o quanto deve sugerir sozinho.',
    prompt: 'Vamos configurar o meu perfil. Me mostre o que a Root entendeu de mim e me faça as perguntas curtas para ajustar tom, formato, ritmo e o quanto você deve sugerir por conta própria.'
  },
  {
    titulo: 'Abra o seu cofre no Obsidian',
    porque: 'O cofre é a sua base de conhecimento. O Claude escreve nele e você lê e corrige quando quiser.',
    como: 'Na primeira vez, o Obsidian pede uma pasta: clique em Abrir pasta como cofre e escolha a pasta vault dentro do kit: {vault}',
    acao: 'obsidian'
  },
  {
    titulo: 'Faça a primeira carga do Obsidian',
    porque: 'Quanto mais o Claude souber do seu trabalho, menos você precisa explicar de novo a cada conversa.',
    prompt: 'Vamos fazer a primeira carga do meu Obsidian. Me pergunte de onde vem o meu contexto de trabalho (conversas antigas no ChatGPT ou no Claude, documentos, planilhas, site e redes da empresa) e me ajude a trazer um de cada vez para a pasta entrada/. Para as conversas antigas, use a skill extrair-contexto. Organize tudo no vault com a skill cuidar-do-vault e me mostre o que vai entrar antes de salvar.'
  },
  {
    titulo: 'Descubra quais conectores você precisa',
    porque: 'Conector é o que deixa o Claude consultar os seus sistemas: e-mail, agenda, arquivos, ERP. Primeiro vem a lista, depois a ligação.',
    prompt: 'Quero ligar o Claude aos sistemas que eu uso no trabalho. Primeiro me pergunte quais eu uso: e-mail, agenda, arquivos na nuvem, WhatsApp, planilhas, ERP, CRM e o que mais aparecer. Depois me diga, para cada um, se existe conector oficial no Claude e se vale ligar agora. Registre a lista no vault.'
  },
  {
    titulo: 'Ligue os conectores, um por vez',
    porque: 'Cada conector se liga na sua conta do Claude, com o seu login. A senha nunca passa pelo chat.',
    prompt: 'Vamos ligar os conectores que escolhemos, um por vez. Para cada um, me guie nas configurações do Claude, em Conectores, sem nunca pedir senha pelo chat. Depois de ligar, me peça para abrir uma conversa nova, faça uma consulta simples para provar que funcionou e anote no vault o que ficou ligado.'
  },
  {
    titulo: 'Feche o dia',
    porque: 'Salva o que você fez, envia o progresso para a Root e traz as atualizações do kit.',
    prompt: 'fechar o dia'
  },
  {
    titulo: 'Se travar, peça ajuda',
    porque: 'O pedido chega à Root com o que aconteceu, sem você precisar explicar tudo de novo no WhatsApp.',
    prompt: 'Preciso de ajuda: [conte aqui o que aconteceu]. Registre o pedido para a Root.'
  }
];
