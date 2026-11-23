// Escenas de las ilustraciones. Cada una: alt (texto alternativo, en español y en inglés) y hacer(S, L) → capas de atrás hacia adelante.
// Sin texto escrito en la imagen: sirve igual en todos los idiomas. Los personajes son los del juego; las gelatinas no usan la mascota nueva de la marca.
const E = {};

E['medusa-mirada'] = {
  alt: { es: 'Ilustración de caricatura: Medusa, una gelatina roja con serpientes por pelo, clava la mirada verde en un caballero que se vuelve piedra mientras sus compañeros huyen asustados.', en: 'Cartoon illustration: Medusa, a red jelly with snakes for hair, fixes her green stare on a knight who is turning to stone while his friends run away in fright.' },
  hacer: (S, L) => [
    L.fondoPrado({ cielo: ['#ffb067', '#ffe7bd'], suelo: ['#b7d96b', '#7fbf4f'], semilla: 21 }),
    L.lineas(150, 520, 60, 150, 7, { c: '#fff', w: 7, semilla: 5, desde: -0.3, hasta: 0.5 }),
    S('campesino', 0, 160, 480, 82, { dir: -1, rot: -14 }), L.signo(190, 335, '!', 46),
    S('pollo', 0, 310, 540, 58, { dir: -1, rot: -10 }), L.signo(330, 440, '!', 34),
    S('caballero', 0, 560, 430, 118, { dir: 1, filtro: 'grayscale(1) brightness(1.08) contrast(.92)' }), L.grietas(560, 440, 120, { semilla: 3 }),
    // la mirada: un haz verde y anillos que salen de sus ojos
    '<defs><linearGradient id="haz" x1="1" y1="0" x2="0" y2="0"><stop offset="0" stop-color="#5de39a" stop-opacity=".75"/><stop offset="1" stop-color="#5de39a" stop-opacity=".15"/></linearGradient></defs><polygon points="850,368 600,330 600,462 850,418" fill="url(#haz)"/>',
    '<g transform="translate(790 392)">' + L.ondas(-30, 0, 34, 70, 4, { c: '#6fe3a0', w: 12, paso: 0.55, alfa: 0.95 }) + '</g>',
    S('medusa', 1, 930, 400, 150, { dir: -1, golpe: 0.5 }),
    L.destellos([[640, 300, 20, '#fff'], [690, 470, 14, '#d4ffe6'], [520, 330, 14, '#fff']]),
  ],
};

E['premios-escenario'] = {
  alt: { es: 'Ilustración de caricatura: en el escenario de una gala de premios, Zeus y Merlín levantan juntos un enorme trofeo dorado entre reflectores y confeti, ante un público en sombra.', en: 'Cartoon illustration: on an awards-gala stage, Zeus and Merlin lift a huge golden trophy together under spotlights and confetti, in front of a silhouetted crowd.' },
  hacer: (S, L) => [
    L.fondoEscenario({ semilla: 33 }),
    L.foco(250, 0, 330, 500, 150), L.foco(950, 0, 870, 500, 150), L.foco(600, 0, 600, 520, 90, { alfa: 0.14 }),
    S('pollo', 0, 1115, 480, 52, { dir: -1, rot: 8 }), L.microfono(1110, 545, 100),
    S('zeus', 0, 320, 400, 118, { dir: 1, golpe: 0.4 }),
    S('merlin', 1, 880, 405, 112, { dir: -1, golpe: 0.4 }),
    L.destellos([[600, 215, 38, '#fff'], [545, 250, 18, '#fff6c9'], [660, 260, 22, '#fff6c9']]),
    L.trofeo(600, 540, 128),
    L.confeti(80, { semilla: 7, y0: 0, y1: 640 }),
    L.destellos([[120, 120, 20], [1090, 140, 24], [470, 300, 14], [740, 300, 16], [120, 430, 14]]),
  ],
};

E['viernes-negro'] = {
  alt: { es: 'Ilustración de caricatura: una estampida de gelatinas corre con carritos de compras hacia una tienda con una gran etiqueta de «-100%», levantando polvo y monedas.', en: 'Cartoon illustration: a stampede of jellies rushes toward a shop with a giant “-100%” price tag, pushing shopping carts and kicking up dust and coins.' },
  hacer: (S, L) => [
    L.fondoTienda(),
    L.etiqueta(600, 178, '-100%', 140, { c: '#e24a33', giro: -6 }),
    L.nube(150, 570, 90, { semilla: 3, c: '#f6efe2' }), L.nube(430, 590, 80, { semilla: 8, c: '#f6efe2' }), L.nube(760, 595, 70, { semilla: 5, c: '#f6efe2' }),
    S('campesino', 0, 280, 450, 98, { dir: 1, rot: 10, golpe: 0.3 }), L.carrito(430, 525, 150),
    S('caballero', 1, 650, 450, 108, { dir: 1, rot: 8, golpe: 0.4 }), L.carrito(820, 540, 165),
    S('pollo', 0, 1010, 480, 70, { dir: 1, rot: 12 }), L.signo(1010, 370, '!', 38),
    L.lineas(80, 450, 40, 150, 6, { c: '#fff', w: 7, semilla: 12, desde: Math.PI - 0.5, hasta: Math.PI + 0.5 }),
    L.moneda(210, 340, 24), L.moneda(540, 300, 20), L.moneda(760, 340, 26), L.moneda(930, 390, 18), L.estrellita(380, 340, 22), L.estrellita(880, 310, 20),
  ],
};

E['lunes-sin-juntas'] = {
  alt: { es: 'Ilustración de caricatura: en una sala de juntas, un caballero y una bruja se pelean por encima de la mesa entre papeles y tazas que vuelan, mientras un campesino se asoma con miedo.', en: 'Cartoon illustration: in a meeting room, a knight and a witch brawl over the table amid flying papers and mugs, while a farmer peeks out in fear.' },
  hacer: (S, L) => [
    L.fondoOficina(), L.reloj(430, 150, 62, 9, 0),
    S('caballero', 0, 290, 395, 112, { dir: 1, golpe: 0.8, sombra: false }),
    S('bruja', 1, 910, 395, 108, { dir: -1, golpe: 0.8, sombra: false }),
    S('campesino', 0, 600, 462, 70, { dir: 1, sombra: false }),
    L.mesa(600, 520, 1000),
    L.signo(690, 392, '!', 40),
    L.rayo(775, 225, 640, 305, { ancho: 22 }),
    L.impacto(590, 300, 105, { semilla: 4, giro: 0.2 }),
    L.papel(470, 220, 70, -20), L.papel(770, 150, 64, 25), L.papel(560, 120, 60, 8, { lineas: 3 }), L.papel(360, 300, 58, -35), L.papel(880, 290, 56, 40),
    L.taza(930, 200, 80, 35), L.taza(250, 190, 70, -30),
    L.papel(400, 505, 56, 12, { lineas: 3 }), L.taza(800, 495, 70, -8),
    L.destellos([[470, 360, 14], [740, 350, 16]]),
  ],
};

E['merlin-ranas'] = {
  alt: { es: 'Ilustración de caricatura: el mago Merlín agita su varita y llueven ranas sobre un caballero rojo que mira hacia arriba, asustado.', en: 'Cartoon illustration: the wizard Merlin waves his wand and it rains frogs onto a red knight who looks up in alarm.' },
  hacer: (S, L) => [
    L.fondoPrado({ cielo: ['#8fb4ff', '#e1ecff'], semilla: 41 }),
    S('merlin', 0, 270, 440, 140, { dir: 1, golpe: 0.8 }),
    L.destellos([[470, 215, 36, '#9ff0ff'], [520, 150, 20, '#fff'], [420, 140, 16, '#9ff0ff']]),
    S('caballero', 1, 850, 460, 112, { dir: -1 }),
    S('rana', 0, 640, 150, 52, { rot: -20 }), S('rana', 0, 740, 260, 56, { rot: 25 }), S('rana', 0, 930, 170, 50, { rot: 10 }),
    S('rana', 0, 1020, 330, 48, { rot: -35 }), S('rana', 0, 850, 350, 44, { rot: 15 }), S('rana', 0, 560, 340, 46, { rot: 40 }),
    L.lineas(700, 300, 40, 120, 5, { c: '#fff', w: 6, semilla: 4, desde: -Math.PI / 2 - 0.4, hasta: -Math.PI / 2 + 0.4 }),
    L.nube(1060, 540, 70, { semilla: 6 }),
  ],
};

E['pelea-nube'] = {
  alt: { es: 'Ilustración de caricatura: una gran nube de polvo de pelea con puños, botas y un garrote asomando, y dos gelatinas que salen volando entre estrellitas.', en: 'Cartoon illustration: a big cartoon fight dust cloud with fists, boots and a club sticking out, and two jellies flying off among little stars.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 51 }),
    S('campesino', 0, 250, 220, 84, { dir: 1, rot: -32 }),
    S('pollo', 1, 960, 200, 66, { dir: -1, rot: 36 }),
    L.nube(600, 410, 235, { semilla: 9, n: 9, c: '#f6efe2' }),
    L.nube(470, 470, 120, { semilla: 4, n: 6, c: '#fff' }), L.nube(740, 470, 120, { semilla: 6, n: 6, c: '#fff' }),
    L.garrote(690, 430, 270, 36),
    '<g transform="translate(450 0) scale(-1 1) translate(-450 0)">' + L.bota(450, 380, 150, -16) + '</g>',
    L.flecha(380, 520, 480, 470),
    '<line x1="580" y1="320" x2="580" y2="205" stroke="' + L.O + '" stroke-width="44" stroke-linecap="round"/><line x1="580" y1="320" x2="580" y2="205" stroke="' + L.C.piel + '" stroke-width="28" stroke-linecap="round"/>', L.mano(580, 190, 36),
    '<line x1="760" y1="455" x2="850" y2="455" stroke="' + L.O + '" stroke-width="44" stroke-linecap="round"/><line x1="760" y1="455" x2="850" y2="455" stroke="' + L.C.piel + '" stroke-width="28" stroke-linecap="round"/>', L.mano(860, 455, 34),
    L.lineas(600, 410, 240, 340, 14, { c: '#fff', w: 8, semilla: 3 }),
    L.impacto(600, 400, 95, { semilla: 7 }), L.estrellita(450, 370, 26), L.estrellita(770, 350, 22), L.estrellita(610, 260, 20),
    L.estrellita(150, 330, 20), L.estrellita(1060, 330, 22), L.estrellita(360, 160, 18, '#fff'),
  ],
};

// ---------------------------------------------------------------- tanda 1
E['anubis-trio'] = {
  alt: { es: 'Ilustración de caricatura: tres Anubis idénticos, gelatinas azules con orejas de chacal y bastón dorado, posan juntos como equipo ideal frente a las pirámides, con cruces de vida flotando sobre ellos.', en: 'Cartoon illustration: three identical Anubis, blue jellies with jackal ears and golden staffs, pose together as a dream team in front of the pyramids, with ankh symbols floating above them.' },
  hacer: (S, L) => [
    L.fondoPrado({ cielo: ['#ffc96b', '#ffeab8'], suelo: ['#f0cf8a', '#d9ac5a'], horizonte: 400, semilla: 61 }), L.piramides({ y: 410 }),
    S('anubis', 0, 215, 440, 104, { dir: 1 }), S('anubis', 0, 985, 440, 104, { dir: -1 }),
    S('anubis', 0, 600, 420, 128, { dir: 1, golpe: 0.3 }),
    L.ankh(215, 170, 70), L.ankh(600, 110, 84), L.ankh(985, 170, 70),
    L.destellos([[440, 250, 18], [760, 250, 18], [150, 330, 14], [1050, 330, 14]]),
  ],
};

E['anubis-revive'] = {
  alt: { es: 'Ilustración de caricatura: Anubis levanta su bastón y tres gelatinas aplastadas en el suelo vuelven a la vida entre rayos de luz dorada y cruces de vida.', en: 'Cartoon illustration: Anubis raises his staff and three flattened jellies on the ground come back to life amid golden beams of light and ankh symbols.' },
  hacer: (S, L) => [
    L.fondoPrado({ cielo: ['#3a2a6e', '#d9789a'], suelo: ['#d9b46a', '#b98a45'], horizonte: 400, semilla: 62, sol: false }),
    L.piramides({ y: 410 }),
    S('anubis', 0, 270, 420, 135, { dir: 1, golpe: 0.8 }),
    ['#ffe98a'].map((c) => [640, 820, 1000].map((x) => '<defs><linearGradient id="hz' + x + '" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="' + c + '" stop-opacity=".85"/><stop offset="1" stop-color="' + c + '" stop-opacity="0"/></linearGradient></defs><polygon points="' + (x - 46) + ',540 ' + (x + 46) + ',540 ' + (x + 80) + ',120 ' + (x - 80) + ',120" fill="url(#hz' + x + ')"/>').join('')).join(''),
    S('campesino', 0, 640, 505, 105, { extra: { dead: true, rot: 0.1 }, sombra: false, dir: 1 }),
    S('arquero', 0, 830, 495, 105, { alfa: 1, extra: { dead: true, rot: -0.15 }, sombra: false }),
    S('caballero', 0, 1000, 470, 80, { dir: -1, rot: -8 }),
    L.ankh(640, 330, 46), L.ankh(820, 300, 46), L.signo(1010, 330, '!', 38),
    L.destellos([[560, 400, 18], [720, 380, 16], [900, 390, 18], [470, 250, 20, '#ffe98a'], [400, 160, 14, '#fff']]),
  ],
};

E['bot-marketing'] = {
  alt: { es: 'Ilustración de caricatura: el «bot de marketing», una gelatina con antena en la cabeza, trabaja en un escritorio con laptop y megáfono, con una gráfica que sube en la pared y un globo donde cuenta el juego a otra gelatina.', en: 'Cartoon illustration: the “marketing bot”, a jelly with an antenna on its head, works at a desk with a laptop and a megaphone, with a rising chart on the wall and a speech bubble where it tells another jelly about the game.' },
  hacer: (S, L) => [
    L.fondoOficina(), L.graficaPared(120, 100, 330, 220),
    S('pollo', 0, 560, 410, 120, { dir: 1, sombra: false }), L.antena(560, 262, 55),
    L.mesa(560, 530, 760),
    L.laptop(470, 508, 110), L.megafono(700, 480, 85, -14), L.taza(380, 505, 70),
    '<path d="M720 255 Q860 195 960 245 Q1060 215 1090 300 Q1100 360 1000 360 L900 362 L850 400 L850 362 Q760 350 740 310 Z" fill="#fff"' + L.O.replace(/.*/, '') + ' stroke="' + L.O + '" stroke-width="7" stroke-linejoin="round"/>',
    S('campesino', 1, 930, 300, 46, { dir: -1, sombra: false }), L.corazon(1030, 270, 20),
    L.destellos([[300, 380, 14], [690, 180, 16]]),
  ],
};

E['zeus-rayos'] = {
  alt: { es: 'Ilustración de caricatura: Zeus levanta su rayo bajo una tormenta y tres rayos caen sobre tres gelatinas rojas muy sorprendidas.', en: 'Cartoon illustration: Zeus raises his bolt under a storm and three lightning bolts strike three very surprised red jellies.' },
  hacer: (S, L) => [
    L.fondoTormenta({ semilla: 71 }),
    S('zeus', 0, 250, 430, 128, { dir: 1, golpe: 0.8 }),
    L.rayo(700, 90, 700, 410, { ancho: 30, semilla: 3 }), L.rayo(880, 70, 880, 400, { ancho: 30, semilla: 8 }), L.rayo(1050, 100, 1050, 440, { ancho: 30, semilla: 5 }),
    S('arquero', 1, 700, 480, 76, { dir: -1, extra: { flash: true } }), S('caballero', 1, 880, 470, 84, { dir: -1, rot: 6 }), S('campesino', 1, 1050, 500, 72, { dir: -1, extra: { flash: true } }),
    L.impacto(700, 560, 60, { semilla: 2 }), L.impacto(880, 570, 60, { semilla: 3 }), L.impacto(1050, 585, 55, { semilla: 6 }),
    L.signo(780, 330, '!', 36), L.signo(960, 330, '!', 34),
  ],
};

E['dracula-botiquin'] = {
  alt: { es: 'Ilustración de caricatura: Drácula muerde a un caballero rojo y una corriente de corazones pasa de la víctima al vampiro, con un botiquín de primeros auxilios a sus pies, de noche y con murciélagos.', en: 'Cartoon illustration: Dracula bites a red knight and a stream of hearts flows from the victim to the vampire, with a first-aid kit at his feet, at night with bats.' },
  hacer: (S, L) => [
    L.fondoNoche({ semilla: 81 }),
    L.murcielago(220, 150, 80, -10), L.murcielago(1010, 200, 70, 12), L.murcielago(640, 90, 56, 4),
    S('dracula', 0, 360, 420, 140, { dir: 1, golpe: 0.7 }),
    S('caballero', 1, 800, 430, 110, { dir: -1, extra: { flash: true }, rot: 8 }),
    L.corazon(700, 330, 22), L.corazon(620, 280, 28), L.corazon(540, 300, 20), L.corazon(480, 350, 16), L.corazon(740, 400, 14),
    L.botiquin(610, 590, 120),
    L.destellos([[480, 220, 16, '#ffb3c8'], [880, 280, 14]]),
  ],
};

E['llorona-lamento'] = {
  alt: { es: 'Ilustración de caricatura: La Llorona, una gelatina con vestido blanco y pelo negro largo, llora enormes lágrimas de noche mientras su lamento en ondas hace huir despavoridos a tres guerreros rojos.', en: 'Cartoon illustration: La Llorona, a jelly with a white dress and long black hair, cries huge tears at night while her wail, in rings, sends three red warriors running away in terror.' },
  hacer: (S, L) => [
    L.fondoNoche({ semilla: 91 }),
    L.ondas(600, 400, 150, 105, 4, { c: '#cfe2ff', w: 9, paso: 0.62 }),
    S('llorona', 0, 600, 400, 165, { dir: 1 }),
    L.gota(530, 440, 22), L.gota(670, 450, 20), L.gota(500, 520, 16), L.gota(700, 530, 14),
    S('caballero', 1, 140, 470, 80, { dir: -1, rot: -14 }), L.signo(160, 330, '!', 38),
    S('gigante', 1, 1030, 440, 74, { dir: 1, rot: 10 }), L.signo(1040, 270, '!', 38),
    S('arquero', 1, 250, 260, 56, { dir: -1, rot: -30 }),
    L.lineas(80, 480, 30, 120, 6, { c: '#fff', w: 7, semilla: 9, desde: -0.5, hasta: 0.5, alfa: 0.7 }),
  ],
};

E['hercules-furia'] = {
  alt: { es: 'Ilustración de caricatura: Hércules, con llamas de furia a su espalda, pega un pisotón que agrieta el suelo y manda a volar a dos guerreros rojos.', en: 'Cartoon illustration: Hercules, with flames of fury behind him, stomps so hard that the ground cracks and two red warriors are sent flying.' },
  hacer: (S, L) => [
    L.fondoRayos({ c1: '#ff9a5a', c2: '#ffb783', cy: 400 }),
    L.llamas(600, 520, 230),
    L.ondas(600, 585, 170, 40, 4, { c: '#fff', w: 10, paso: 0.55 }), L.grietas(600, 590, 270, { semilla: 4 }),
    S('hercules', 0, 600, 410, 155, { dir: 1, golpe: 0.9 }), L.enojo(740, 250, 46),
    S('campesino', 1, 250, 230, 70, { dir: 1, rot: -40 }), S('arquero', 1, 960, 200, 66, { dir: -1, rot: 38 }),
    L.estrellita(190, 330, 22), L.estrellita(1020, 300, 20), L.estrellita(330, 150, 16, '#fff'),
    L.nube(210, 560, 70, { semilla: 3, c: '#f6efe2' }), L.nube(1000, 570, 76, { semilla: 5, c: '#f6efe2' }),
  ],
};

E['gigantes-ranas'] = {
  alt: { es: 'Ilustración de caricatura: dos gigantes rojos miran con cara de susto cómo llueven ranitas sobre ellos mientras Merlín, al fondo, sonríe de lado.', en: 'Cartoon illustration: two red giants look up in alarm as little frogs rain down on them while Merlin, in the background, grins.' },
  hacer: (S, L) => [
    L.fondoPrado({ cielo: ['#8fb4ff', '#e1ecff'], semilla: 101 }),
    S('merlin', 0, 1070, 520, 70, { dir: -1, golpe: 0.6 }), L.destellos([[985, 400, 18, '#9ff0ff'], [940, 340, 12, '#fff']]),
    S('gigante', 1, 250, 440, 128, { dir: 1 }), S('gigante', 1, 820, 450, 125, { dir: -1 }),
    L.signo(330, 215, '?', 44), L.signo(880, 220, '!', 44),
    S('rana', 0, 360, 160, 46, { rot: 15 }), S('rana', 0, 560, 230, 50, { rot: -30 }), S('rana', 0, 650, 120, 44, { rot: 25 }),
    S('rana', 0, 830, 150, 48, { rot: -10 }), S('rana', 0, 500, 400, 40, { rot: 40 }), S('rana', 0, 980, 290, 42, { rot: -35 }),
    L.lineas(560, 320, 40, 110, 5, { c: '#fff', w: 6, semilla: 4, desde: -Math.PI / 2 - 0.4, hasta: -Math.PI / 2 + 0.4 }),
  ],
};

E['sin-descarga'] = {
  alt: { es: 'Ilustración de caricatura: dentro de la ventana de un navegador, un icono de descarga está tachado en rojo, la barra de carga ya está llena y Zeus y Medusa se preparan para pelear.', en: 'Cartoon illustration: inside a browser window, a download icon is crossed out in red, the loading bar is already full, and Zeus and Medusa get ready to fight.' },
  hacer: (S, L) => [
    L.fondoNavegador(),
    L.iconoDescarga(300, 330, 110), L.prohibido(300, 330, 140),
    L.barraCarga(240, 535, 720, 44, 1),
    S('zeus', 0, 650, 380, 95, { dir: 1, golpe: 0.5 }), S('medusa', 1, 930, 380, 100, { dir: -1, golpe: 0.5 }),
    L.impacto(790, 330, 56, { semilla: 3 }), L.destellos([[1010, 220, 18], [520, 240, 14]]),
  ],
};

// ---------------------------------------------------------------- tanda 2
// dos mitades con una diagonal en medio: (izq, der) son funciones que devuelven el contenido de cada lado
const mitades = (L, izq, der, x = 600) => {
  const id = 'mi' + Math.round(Math.random() * 1e6);
  return '<defs><clipPath id="' + id + 'a"><polygon points="0,0 ' + (x + 60) + ',0 ' + (x - 60) + ',675 0,675"/></clipPath><clipPath id="' + id + 'b"><polygon points="' + (x + 60) + ',0 1200,0 1200,675 ' + (x - 60) + ',675"/></clipPath></defs>' +
    '<g clip-path="url(#' + id + 'a)">' + izq + '</g><g clip-path="url(#' + id + 'b)">' + der + '</g>' +
    '<line x1="' + (x + 60) + '" y1="0" x2="' + (x - 60) + '" y2="675" stroke="' + L.O + '" stroke-width="14"/><line x1="' + (x + 60) + '" y1="0" x2="' + (x - 60) + '" y2="675" stroke="#fff" stroke-width="5"/>';
};
const bolsa = (L, x, y, s) => '<g transform="translate(' + x + ' ' + y + ') scale(' + s / 100 + ')"><path d="M-22 -70 Q0 -96 22 -70 L14 -52 L-14 -52Z" fill="#a8703a" stroke="' + L.O + '" stroke-width="7" stroke-linejoin="round"/><path d="M-14 -52 C-80 -20 -78 60 0 62 C78 60 80 -20 14 -52Z" fill="#c78a43" stroke="' + L.O + '" stroke-width="8" stroke-linejoin="round"/><circle cx="0" cy="8" r="26" fill="' + L.C.oro + '" stroke="' + L.O + '" stroke-width="6"/><circle cx="0" cy="8" r="15" fill="none" stroke="#fff3b0" stroke-width="5"/></g>';

E['zeus-horario'] = {
  alt: { es: 'Ilustración de caricatura: Zeus mira un gran reloj de pared en plena tormenta; del reloj cae un rayo puntual sobre dos gelatinas rojas que no lo esperaban.', en: 'Cartoon illustration: Zeus looks at a big wall clock in the middle of a storm; a bolt falls right on time from the clock onto two red jellies that did not expect it.' },
  hacer: (S, L) => [
    L.fondoTormenta({ semilla: 111 }),
    L.reloj(830, 230, 145, 6, 30),
    S('zeus', 0, 300, 430, 135, { dir: 1, golpe: 0.4 }),
    L.rayo(830, 385, 940, 505, { ancho: 28, semilla: 4, tramos: 4 }),
    S('caballero', 1, 930, 550, 68, { dir: -1, extra: { flash: true } }), S('arquero', 1, 1080, 555, 56, { dir: -1 }),
    L.impacto(930, 612, 52, { semilla: 5 }), L.signo(1075, 450, '!', 36),
    L.destellos([[540, 250, 16], [640, 130, 18, '#fff6c9']]),
  ],
};

E['zeus-vs-hercules'] = {
  alt: { es: 'Ilustración de caricatura dividida en dos: a la izquierda Zeus con su rayo en una tormenta, a la derecha Hércules en llamas pisando fuerte, con un signo de interrogación en medio: ¿con quién empiezas?', en: 'Cartoon illustration split in two: on the left Zeus with his bolt in a storm, on the right Hercules in flames stomping hard, with a question mark in the middle: who do you start with?' },
  hacer: (S, L) => [
    mitades(L, L.fondoTormenta({ semilla: 121 }), L.fondoRayos({ c1: '#ff9a5a', c2: '#ffb783', cx: 900, cy: 400 })),
    L.llamas(900, 540, 190),
    L.rayo(330, 80, 330, 270, { ancho: 24, semilla: 3, tramos: 4 }),
    S('zeus', 0, 290, 430, 140, { dir: 1, golpe: 0.8 }),
    L.ondas(900, 590, 150, 36, 3, { c: '#fff', w: 9, paso: 0.55 }),
    S('hercules', 0, 910, 420, 148, { dir: -1, golpe: 0.8 }),
    L.signo(600, 120, '?', 66),
  ],
};

E['robin-tres-flechas'] = {
  alt: { es: 'Ilustración de caricatura: Robin Hood dispara tres flechas a la vez hacia una diana y una de ellas, dorada, da justo en el centro entre destellos.', en: 'Cartoon illustration: Robin Hood fires three arrows at once toward a target, and one of them, golden, hits the dead center amid sparkles.' },
  hacer: (S, L) => [
    L.fondoPrado({ cielo: ['#9fd7ff', '#e6f5ff'], suelo: ['#9ad66a', '#6fbf4f'], semilla: 131 }),
    '<rect x="1000" y="470" width="20" height="130" fill="#8a5a2b" stroke="' + L.O + '" stroke-width="7"/>', L.diana(1010, 400, 110),
    S('robin', 0, 240, 440, 130, { dir: 1, golpe: 0.7 }),
    L.lineas(420, 400, 20, 140, 5, { c: '#fff', w: 6, semilla: 7, desde: -0.15, hasta: 0.25 }),
    L.flecha(430, 360, 930, 325), L.flecha(430, 415, 890, 480), L.flecha(430, 388, 1005, 400, { c: '#f7b21b', pluma: '#ffe14a', w: 9 }),
    L.destellos([[1010, 400, 40, '#fff'], [940, 330, 18], [1090, 340, 16]]),
  ],
};

E['dracula-noche'] = {
  alt: { es: 'Ilustración de caricatura: Drácula, sonriente y con colmillos, sostiene un portapapeles con su «plan de salud» —un colmillo y un corazón— bajo la luna llena y entre murciélagos.', en: 'Cartoon illustration: Dracula, smiling with fangs, holds a clipboard with his “health plan” (a fang and a heart) under the full moon and among bats.' },
  hacer: (S, L) => [
    L.fondoNoche({ semilla: 141 }),
    L.murcielago(240, 170, 90, -12), L.murcielago(1020, 230, 80, 10), L.murcielago(420, 90, 56, 6), L.murcielago(860, 90, 60, -6),
    S('dracula', 0, 520, 410, 165, { dir: 1 }),
    '<g transform="translate(880 430) rotate(8)"><rect x="-95" y="-125" width="190" height="250" rx="16" fill="#a8703a" stroke="' + L.O + '" stroke-width="8"/><rect x="-75" y="-100" width="150" height="212" rx="6" fill="#fff"/><rect x="-32" y="-138" width="64" height="30" rx="8" fill="#9aa6b2" stroke="' + L.O + '" stroke-width="6"/>' +
      '<path d="M-42 -60 L-6 -60 L-24 -14Z M6 -60 L42 -60 L24 -14Z" fill="#fff" stroke="' + L.O + '" stroke-width="7" stroke-linejoin="round"/>' + L.corazon(0, 50, 26) + '</g>',
    L.destellos([[300, 260, 16], [700, 230, 14, '#ffb3c8'], [980, 150, 14]]),
  ],
};

E['llorona-huida'] = {
  alt: { es: 'Ilustración de caricatura: de noche, La Llorona solloza a lo lejos con ondas a su alrededor mientras cinco guerreros rojos salen corriendo espantados, dejando polvo y signos de exclamación.', en: 'Cartoon illustration: at night, La Llorona sobs in the distance with rings around her while five red warriors run away in a panic, leaving dust and exclamation marks behind.' },
  hacer: (S, L) => [
    L.fondoNoche({ semilla: 151 }),
    L.ondas(260, 420, 100, 70, 4, { c: '#cfe2ff', w: 8, paso: 0.6 }),
    S('llorona', 0, 260, 420, 118, { dir: 1 }), L.gota(215, 460, 16), L.gota(305, 470, 14),
    L.nube(560, 560, 60, { semilla: 3, c: '#9fb4ff', alfa: 0.45 }),
    S('pollo', 1, 560, 500, 50, { dir: 1, rot: 12 }), L.signo(570, 415, '!', 30),
    S('arquero', 1, 690, 470, 62, { dir: 1, rot: 14 }), S('campesino', 1, 810, 500, 58, { dir: 1, rot: 12 }), L.signo(830, 395, '!', 34),
    S('caballero', 1, 930, 450, 72, { dir: 1, rot: 10 }), S('gigante', 1, 1060, 460, 60, { dir: 1, rot: 8 }),
    L.lineas(520, 480, 30, 110, 7, { c: '#fff', w: 6, semilla: 4, desde: Math.PI - 0.35, hasta: Math.PI + 0.35, alfa: 0.6 }),
  ],
};

E['gigante-vs-campesinos'] = {
  alt: { es: 'Ilustración de caricatura: un Gigante enorme a la izquierda frente a un montón de campesinos a la derecha, con una bolsa de oro del mismo tamaño sobre cada bando: ¿cuál conviene más?', en: 'Cartoon illustration: a huge Giant on the left facing a crowd of farmers on the right, with an identical bag of gold above each side: which one is the better buy?' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 161 }),
    bolsa(L, 270, 150, 120), bolsa(L, 860, 150, 120),
    '<path d="M390 150 H740" stroke="' + L.O + '" stroke-width="14" stroke-linecap="round" stroke-dasharray="4 26"/>',
    S('gigante', 0, 270, 430, 160, { dir: 1, golpe: 0.4 }),
    [[690, 440, 56], [800, 455, 56], [910, 440, 56], [1020, 455, 56], [640, 545, 58], [750, 550, 58], [860, 545, 58], [970, 550, 58], [1080, 545, 58]].map(([x, y, r], i) => S('campesino', 1, x, y, r, { dir: -1, golpe: (i % 3) * 0.25 })),
  ],
};

E['ocho-foto'] = {
  alt: { es: 'Ilustración de caricatura: las ocho Leyendas —Zeus, Hércules, Merlín, Robin Hood, Anubis, La Llorona, Drácula y Medusa— posan apretadas en dos filas para una foto de grupo, con un destello de flash.', en: 'Cartoon illustration: the eight Legends (Zeus, Hercules, Merlin, Robin Hood, Anubis, La Llorona, Dracula and Medusa) pose squeezed into two rows for a group photo, with a camera flash.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 171, horizonte: 330 }),
    S('zeus', 0, 325, 340, 82, { dir: 1 }), S('merlin', 0, 575, 340, 82, { dir: 1 }), S('anubis', 1, 825, 340, 82, { dir: -1 }), S('medusa', 1, 1075, 340, 82, { dir: -1 }),
    S('hercules', 0, 200, 500, 92, { dir: 1 }), S('robin', 0, 450, 500, 92, { dir: 1 }), S('llorona', 1, 700, 500, 92, { dir: -1 }), S('dracula', 1, 950, 500, 92, { dir: -1 }),
    '<g transform="translate(90 590)"><rect x="-44" y="-30" width="88" height="56" rx="10" fill="#2b2f3a" stroke="' + L.O + '" stroke-width="6"/><circle cx="0" cy="-2" r="19" fill="#9aa6b2" stroke="' + L.O + '" stroke-width="5"/><circle cx="0" cy="-2" r="9" fill="#2f6fe0"/><rect x="-30" y="-42" width="22" height="14" rx="4" fill="#9aa6b2" stroke="' + L.O + '" stroke-width="5"/></g>',
    L.destello(90, 540, 56, { c: '#fff', trazo: 5 }), L.destellos([[150, 500, 18], [60, 480, 14]]),
  ],
};

E['tres-poderes'] = {
  alt: { es: 'Ilustración de caricatura: tres Leyendas sobre tres pedestales dorados, cada una con su poder: Zeus con rayos, Drácula con corazones y Merlín con ranas, para elegir una.', en: 'Cartoon illustration: three Legends on three golden pedestals, each with their power: Zeus with lightning, Dracula with hearts and Merlin with frogs, to pick one.' },
  hacer: (S, L) => [
    L.fondoRayos({ c1: '#5a3aa6', c2: '#6c4cbb', cy: 330 }),
    '<rect x="150" y="520" width="200" height="170" rx="16" fill="#ffd95e" stroke="' + L.O + '" stroke-width="8"/><rect x="500" y="520" width="200" height="170" rx="16" fill="#ffd95e" stroke="' + L.O + '" stroke-width="8"/><rect x="850" y="520" width="200" height="170" rx="16" fill="#ffd95e" stroke="' + L.O + '" stroke-width="8"/>',
    L.rayo(160, 60, 160, 210, { ancho: 18, semilla: 2, tramos: 3 }), L.rayo(340, 70, 340, 220, { ancho: 18, semilla: 5, tramos: 3 }),
    S('zeus', 0, 250, 440, 105, { dir: 1, golpe: 0.5, sombra: false }),
    L.corazon(520, 190, 22), L.corazon(680, 200, 20), L.corazon(600, 130, 26),
    S('dracula', 0, 600, 440, 112, { dir: 1, sombra: false }),
    S('rana', 0, 870, 190, 42, { rot: -15 }), S('rana', 0, 1010, 220, 40, { rot: 20 }), S('rana', 0, 940, 120, 38, { rot: 5 }),
    S('merlin', 0, 950, 440, 105, { dir: -1, golpe: 0.5, sombra: false }),
    L.destellos([[420, 330, 20], [760, 330, 20], [90, 300, 14], [1110, 300, 14]]),
  ],
};

E['duelo-sustos'] = {
  alt: { es: 'Ilustración de caricatura: Medusa y La Llorona se miran frente a frente de noche, cada una con sus ondas de miedo, mientras un campesino rojo en medio tiembla de espanto.', en: 'Cartoon illustration: Medusa and La Llorona face each other at night, each with her own rings of fear, while a red farmer in the middle trembles in terror.' },
  hacer: (S, L) => [
    L.fondoNoche({ semilla: 181 }),
    L.ondas(300, 400, 70, 90, 4, { c: '#6fe3a0', w: 10, paso: 0.7 }), L.ondas(900, 400, 70, 90, 4, { c: '#cfe2ff', w: 10, paso: 0.7 }),
    S('medusa', 1, 250, 400, 135, { dir: 1, golpe: 0.5 }), S('llorona', 0, 950, 400, 135, { dir: -1 }),
    L.gota(900, 450, 16), L.gota(1000, 460, 14),
    S('campesino', 1, 600, 520, 62, { dir: 1 }), L.gota(560, 450, 12), L.gota(650, 455, 12), L.signo(600, 370, '!', 40),
    L.destellos([[600, 250, 20, '#fff'], [520, 300, 12, '#d4ffe6'], [680, 300, 12, '#cfe2ff']]),
  ],
};

E['gigante-antes-despues'] = {
  alt: { es: 'Ilustración de caricatura en dos mitades: a la izquierda, un Gigante rojo furioso con su garrote enorme; a la derecha, el mismo garrote junto a una ranita roja, y en medio Merlín con chispas mágicas.', en: 'Cartoon illustration in two halves: on the left, a furious red Giant with his huge club; on the right, the same club next to a little red frog, and in the middle Merlin with magic sparks.' },
  hacer: (S, L) => [
    mitades(L, L.fondoPrado({ semilla: 191 }), L.fondoPrado({ cielo: ['#e5b8ff', '#fbe8ff'], suelo: ['#a6dd6e', '#6fbf4f'], semilla: 192 })),
    S('gigante', 1, 270, 420, 165, { dir: 1 }),
    L.garrote(980, 560, 190, 22), S('rana', 1, 880, 470, 95, { dir: -1 }),
    S('merlin', 0, 610, 540, 68, { dir: 1, golpe: 0.7 }), L.destellos([[640, 400, 24, '#9ff0ff'], [560, 330, 18], [700, 300, 16, '#fff'], [800, 400, 16, '#e5b8ff']]),
  ],
};

E['sin-registro'] = {
  alt: { es: 'Ilustración de caricatura: en la ventana de un navegador, una tarjeta de cuenta y un icono de descarga aparecen tachados en rojo, y un reloj con alas se va volando mientras un campesino juega tan tranquilo.', en: 'Cartoon illustration: in a browser window, an account card and a download icon are crossed out in red, and a winged clock flies away while a farmer plays calmly.' },
  hacer: (S, L) => [
    L.fondoNavegador({ c: '#e8f6ec' }),
    L.iconoCuenta(270, 300, 100), L.prohibido(270, 300, 135),
    L.iconoDescarga(560, 300, 85), L.prohibido(560, 300, 125),
    '<g transform="translate(900 300) rotate(-14)"><path d="M-80 -12 Q-190 -70 -150 20 Q-130 50 -80 28Z" fill="#fff" stroke="' + L.O + '" stroke-width="7"/><path d="M80 -12 Q190 -70 150 20 Q130 50 80 28Z" fill="#fff" stroke="' + L.O + '" stroke-width="7"/>' + L.reloj(0, 0, 80, 3, 0) + '</g>',
    L.lineas(1010, 330, 30, 130, 5, { c: '#9aa6b2', w: 6, semilla: 3, desde: -0.3, hasta: 0.3, alfa: 0.8 }),
    S('campesino', 0, 600, 520, 66, { dir: 1, golpe: 0.3 }), L.destellos([[700, 480, 14], [500, 470, 12]]),
  ],
};

E['contra-ti-mismo'] = {
  alt: { es: 'Ilustración de caricatura: dos Merlines idénticos, uno azul y otro rojo, se lanzan rayos mágicos de frente en un prado y chocan en el centro entre chispas.', en: 'Cartoon illustration: two identical Merlins, one blue and one red, fire magic beams at each other in a meadow and collide in the middle amid sparks.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 201 }),
    S('merlin', 0, 260, 430, 135, { dir: 1, golpe: 0.9 }), S('merlin', 1, 940, 430, 135, { dir: -1, golpe: 0.9 }),
    L.rayo(400, 250, 600, 310, { ancho: 22, c: '#7de8ff', semilla: 3, tramos: 4 }), L.rayo(800, 250, 600, 310, { ancho: 22, c: '#ff9ac2', semilla: 4, tramos: 4 }),
    L.impacto(600, 310, 80, { semilla: 2 }), L.gota(110, 330, 14), L.gota(1090, 330, 14),
    L.destellos([[600, 180, 20], [500, 400, 14], [700, 400, 14]]),
  ],
};

// ---------------------------------------------------------------- tanda 3
E['reto-escalera'] = {
  alt: { es: 'Ilustración de caricatura: Hércules mira hacia arriba al pie de una escalera de cinco peldaños donde esperan rivales cada vez más grandes —un campesino, un arquero, un caballero y un gigante— y, en lo alto, un trofeo dorado.', en: 'Cartoon illustration: Hercules looks up at the foot of a five-step staircase where ever-bigger rivals wait (a farmer, an archer, a knight and a giant) with a golden trophy at the very top.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 211 }),
    L.escalera(280, 560, 160, 5, 80),
    S('hercules', 0, 130, 500, 85, { dir: 1, golpe: 0.3 }),
    S('campesino', 1, 360, 515, 44, { dir: -1 }), S('arquero', 1, 520, 430, 50, { dir: -1 }), S('caballero', 1, 680, 345, 58, { dir: -1 }), S('gigante', 1, 840, 245, 72, { dir: -1 }),
    L.trofeo(1000, 240, 90),
    L.moneda(250, 350, 22), L.moneda(190, 300, 18), L.moneda(310, 280, 16), L.destellos([[1000, 60, 22], [920, 130, 14]]),
  ],
};

E['robin-confuso'] = {
  alt: { es: 'Ilustración de caricatura: Robin Hood dispara tres flechas; una da en el centro de la diana y las otras dos se clavan en el suelo y en una nube, con signos de interrogación sobre ellas.', en: 'Cartoon illustration: Robin Hood fires three arrows; one hits the center of the target while the other two stick into the ground and into a cloud, with question marks above them.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 221 }),
    '<rect x="880" y="470" width="20" height="130" fill="#8a5a2b" stroke="' + L.O + '" stroke-width="7"/>', L.diana(890, 400, 105),
    S('robin', 0, 230, 440, 125, { dir: 1, golpe: 0.6 }),
    L.flecha(410, 395, 880, 400, { c: '#f7b21b', pluma: '#ffe14a', w: 9 }),
    L.flecha(420, 360, 640, 120), L.flecha(430, 430, 640, 580),
    L.signo(690, 80, '?', 40), L.signo(700, 600, '?', 40),
    L.destellos([[890, 400, 36, '#fff'], [980, 330, 16]]),
  ],
};

E['leyenda-nueva'] = {
  alt: { es: 'Ilustración de caricatura: las ocho Leyendas en fila y, en lo alto bajo un reflector, la silueta negra de una novena gelatina misteriosa con un signo de interrogación.', en: 'Cartoon illustration: the eight Legends in a row and, high up under a spotlight, the black silhouette of a mysterious ninth jelly with a question mark.' },
  hacer: (S, L) => [
    L.fondoRayos({ c1: '#2f3a8a', c2: '#3a47a1', cy: 300 }),
    L.foco(600, 0, 600, 420, 170, { alfa: 0.3 }),
    S('pollo', 1, 600, 250, 115, { dir: 1, filtro: 'brightness(0)', contorno: false, sombra: false }),
    L.signo(600, 215, '?', 70, { c: '#ffd95e' }),
    ['zeus', 'hercules', 'merlin', 'robin', 'anubis', 'llorona', 'dracula', 'medusa'].map((t, i) => S(t, i < 4 ? 0 : 1, 100 + i * 143, 570, 58, { dir: i < 4 ? 1 : -1 })),
    L.destellos([[250, 160, 16], [950, 140, 18], [380, 330, 12], [840, 330, 12]]),
  ],
};

E['bot-pizza'] = {
  alt: { es: 'Ilustración de caricatura: el bot-gelatina, con antena en la cabeza y sin manos, mira confundido una pizza con piña mientras un signo de interrogación flota sobre él.', en: 'Cartoon illustration: the jelly bot, with an antenna on its head and no hands, looks puzzled at a pizza with pineapple while a question mark floats above it.' },
  hacer: (S, L) => [
    L.fondoRayos({ c1: '#ffe9b8', c2: '#fff3d3', cx: 800, cy: 400 }),
    S('pollo', 0, 330, 430, 135, { dir: 1, sombra: true }), L.antena(330, 270, 60), L.signo(330, 130, '?', 60),
    L.sombra(850, 585, 190),
    L.pizza(850, 410, 160),
    L.destellos([[640, 300, 18], [1050, 240, 16], [720, 200, 12]]),
  ],
};

E['delirios'] = {
  alt: { es: 'Ilustración de caricatura: un campesino chiquito sueña, en un globo de pensamiento enorme, con un campo de batalla lleno de Leyendas de los dos bandos.', en: 'Cartoon illustration: a tiny farmer dreams, in a huge thought bubble, of a battlefield full of Legends from both sides.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 231 }),
    L.pensamiento(700, 250, 360, 175, 330, 470),
    S('zeus', 0, 490, 195, 46, { dir: 1, sombra: false }), S('merlin', 0, 590, 195, 46, { dir: 1, sombra: false }), S('hercules', 0, 490, 295, 46, { dir: 1, sombra: false }), S('robin', 0, 590, 295, 46, { dir: 1, sombra: false }),
    S('medusa', 1, 820, 195, 46, { dir: -1, sombra: false }), S('anubis', 1, 920, 195, 46, { dir: -1, sombra: false }), S('dracula', 1, 820, 295, 46, { dir: -1, sombra: false }), S('llorona', 1, 920, 295, 46, { dir: -1, sombra: false }),
    L.impacto(705, 250, 46, { semilla: 3, trazo: 5 }),
    S('campesino', 0, 280, 540, 78, { dir: 1 }),
    L.estrellita(160, 450, 16), L.estrellita(430, 430, 12),
  ],
};

E['tres-miedos'] = {
  alt: { es: 'Ilustración de caricatura: una rueda de sospechosos con un Gigante, Medusa y un campesino sudando que abraza un plan de batalla arrugado, frente a una pared con marcas de estatura.', en: 'Cartoon illustration: a police lineup with a Giant, Medusa and a sweating farmer hugging a crumpled battle plan, in front of a wall with height marks.' },
  hacer: (S, L) => [
    '<rect width="1200" height="675" fill="#cfd6df"/><rect y="560" width="1200" height="115" fill="#a7b0bd"/><line x1="0" y1="560" x2="1200" y2="560" stroke="' + L.O + '" stroke-width="8"/>' +
      [150, 250, 350, 450].map((y) => '<line x1="0" y1="' + y + '" x2="1200" y2="' + y + '" stroke="#7d8896" stroke-width="5"/>' + [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((i) => '<line x1="' + (i * 100) + '" y1="' + y + '" x2="' + (i * 100) + '" y2="' + (y + 22) + '" stroke="#7d8896" stroke-width="5"/>').join('')).join(''),
    S('gigante', 1, 260, 440, 150, { dir: 1 }), S('medusa', 1, 610, 450, 120, { dir: 1 }),
    S('campesino', 0, 930, 500, 80, { dir: 1, sombra: true }),
    '<g transform="translate(990 520) rotate(-18)"><path d="M-46 -30 L-20 -48 L10 -34 L40 -46 L50 -10 L34 20 L44 44 L10 52 L-20 40 L-44 46 L-36 10Z" fill="#fff" stroke="' + L.O + '" stroke-width="6" stroke-linejoin="round"/><path d="M-26 -14 H22 M-28 8 H24 M-22 28 H14" stroke="#9aa6b2" stroke-width="5" stroke-linecap="round"/></g>',
    L.gota(870, 410, 14), L.gota(1010, 420, 12), L.signo(930, 340, '?', 44),
    L.destellos([[130, 200, 14], [1100, 200, 14]]),
  ],
};

E['podio-rota'] = {
  alt: { es: 'Ilustración de caricatura: un podio con Medusa en primer lugar sosteniendo un trofeo, Zeus en segundo y Anubis en tercero, mientras otras cinco Leyendas los aclaman desde abajo entre confeti.', en: 'Cartoon illustration: a podium with Medusa in first place holding a trophy, Zeus in second and Anubis in third, while five other Legends cheer from below amid confetti.' },
  hacer: (S, L) => [
    L.fondoEscenario({ semilla: 241 }),
    '<rect x="270" y="400" width="230" height="290" rx="14" fill="#c7d0da" stroke="' + L.O + '" stroke-width="8"/><rect x="485" y="320" width="230" height="370" rx="14" fill="#ffd95e" stroke="' + L.O + '" stroke-width="8"/><rect x="700" y="440" width="230" height="250" rx="14" fill="#d9965a" stroke="' + L.O + '" stroke-width="8"/>' +
      '<circle cx="385" cy="470" r="32" fill="#e8edf3" stroke="' + L.O + '" stroke-width="6"/><circle cx="600" cy="390" r="36" fill="#ffe98a" stroke="' + L.O + '" stroke-width="6"/><circle cx="815" cy="510" r="30" fill="#e6b27a" stroke="' + L.O + '" stroke-width="6"/>',
    S('zeus', 0, 385, 300, 78, { dir: 1, sombra: false }), S('medusa', 1, 600, 215, 88, { dir: -1, sombra: false }), S('anubis', 1, 815, 340, 76, { dir: -1, sombra: false }),
    L.trofeo(600, 220, 36),
    S('hercules', 0, 90, 590, 58, { dir: 1 }), S('merlin', 0, 190, 600, 54, { dir: 1 }), S('robin', 0, 1010, 600, 54, { dir: -1 }), S('llorona', 1, 1110, 590, 58, { dir: -1 }), S('dracula', 1, 130, 500, 46, { dir: 1 }),
    L.confeti(70, { semilla: 3, y0: 0, y1: 600 }), L.destellos([[300, 130, 18], [900, 120, 20], [1080, 300, 14]]),
  ],
};

E['merlin-pizarra'] = {
  alt: { es: 'Ilustración de caricatura: Merlín señala con su varita una pizarra con un plan dibujado: un gigante enojado, una flecha y una rana, y un tercer recuadro vacío con signo de interrogación.', en: 'Cartoon illustration: Merlin points his wand at a whiteboard with a drawn plan: an angry giant, an arrow and a frog, and an empty third box with a question mark.' },
  hacer: (S, L) => [
    L.fondoOficina(),
    '<rect x="70" y="80" width="760" height="360" rx="16" fill="#fff" stroke="' + L.O + '" stroke-width="10"/><rect x="70" y="440" width="760" height="22" rx="8" fill="#9aa6b2" stroke="' + L.O + '" stroke-width="7"/>' +
      // paso 1: gigante dibujado a mano
      '<circle cx="190" cy="270" r="62" fill="#e24a33" stroke="' + L.O + '" stroke-width="7"/><path d="M148 160 L168 215 M232 160 L212 215" stroke="' + L.O + '" stroke-width="12" stroke-linecap="round"/><path d="M158 250 L186 262 M222 250 L194 262" stroke="' + L.O + '" stroke-width="8" stroke-linecap="round"/><circle cx="172" cy="272" r="9" fill="' + L.O + '"/><circle cx="210" cy="272" r="9" fill="' + L.O + '"/>' +
      '<path d="M272 270 H350 M326 240 L356 270 L326 300" fill="none" stroke="' + L.O + '" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>' +
      // paso 2: rana
      '<ellipse cx="470" cy="285" rx="60" ry="48" fill="#46c68d" stroke="' + L.O + '" stroke-width="7"/><circle cx="440" cy="235" r="22" fill="#fff" stroke="' + L.O + '" stroke-width="6"/><circle cx="500" cy="235" r="22" fill="#fff" stroke="' + L.O + '" stroke-width="6"/><circle cx="444" cy="238" r="8" fill="' + L.O + '"/><circle cx="496" cy="238" r="8" fill="' + L.O + '"/>' +
      '<path d="M570 270 H640 M616 240 L646 270 L616 300" fill="none" stroke="' + L.O + '" stroke-width="12" stroke-linecap="round" stroke-linejoin="round"/>' +
      // paso 3: recuadro vacío
      '<rect x="670" y="205" width="120" height="130" rx="14" fill="none" stroke="' + L.O + '" stroke-width="8" stroke-dasharray="14 12"/>' + L.signo(730, 270, '?', 46),
    S('merlin', 0, 960, 440, 125, { dir: -1, golpe: 0.7 }),
    L.destellos([[860, 300, 16, '#9ff0ff'], [840, 220, 12]]),
  ],
};

E['zeus-clima'] = {
  alt: { es: 'Ilustración de caricatura: Zeus, con su rayo, rodeado de iconos del clima —sol, nube con lluvia, copo de nieve, arcoíris y relámpago— porque su personalidad entera es el tiempo.', en: 'Cartoon illustration: Zeus, with his bolt, surrounded by weather icons (sun, rain cloud, snowflake, rainbow and lightning) because his whole personality is the weather.' },
  hacer: (S, L) => [
    L.fondoPrado({ semilla: 251 }).replace('<circle cx="1010" cy="110" r="64" fill="#fff3b0" opacity=".9"/><circle cx="1010" cy="110" r="44" fill="#ffe27a"/>', ''),
    L.sol(170, 140, 56), L.nubeIcono(1000, 130, 70), L.lluvia(1000, 200, 70, 5),
    L.copo(150, 430, 55), L.arcoiris(1000, 470, 110),
    L.rayo(600, 50, 600, 200, { ancho: 22, semilla: 3, tramos: 3 }),
    S('zeus', 0, 600, 420, 150, { dir: 1, golpe: 0.5 }),
    L.destellos([[330, 260, 16], [860, 280, 16], [420, 560, 12], [800, 560, 12]]),
  ],
};

E['plan-batalla'] = {
  alt: { es: 'Ilustración de caricatura dividida en dos: a la izquierda, una fila perfectamente ordenada de campesinos chiquitos; a la derecha, una nube de pelea con puños, botas y dos gelatinas saliendo volando.', en: 'Cartoon illustration split in two: on the left, a perfectly neat row of tiny farmers; on the right, a fight cloud with fists, boots and two jellies flying out.' },
  hacer: (S, L) => [
    mitades(L,
      L.fondoPrado({ semilla: 261, sol: false }) + '<line x1="30" y1="505" x2="600" y2="505" stroke="#fff" stroke-width="6" stroke-dasharray="14 12" opacity=".9"/>',
      L.fondoPrado({ semilla: 262 }), 600),
    [0, 1, 2, 3, 4, 5, 6].map((i) => S('campesino', 0, 70 + i * 76, 455, 36, { dir: 1, sombra: true })),
    S('arquero', 0, 800, 230, 54, { dir: 1, rot: -30 }), S('pollo', 1, 1100, 220, 50, { dir: -1, rot: 36 }),
    L.nube(930, 430, 150, { semilla: 9, n: 8, c: '#f6efe2' }),
    L.garrote(990, 470, 170, 36),
    '<line x1="880" y1="420" x2="880" y2="300" stroke="' + L.O + '" stroke-width="40" stroke-linecap="round"/><line x1="880" y1="420" x2="880" y2="300" stroke="' + L.C.piel + '" stroke-width="26" stroke-linecap="round"/>', L.mano(880, 288, 32),
    L.impacto(930, 430, 62, { semilla: 7, trazo: 6 }), L.estrellita(780, 400, 20), L.estrellita(1100, 400, 20),
  ],
};

E['oro-tres-montones'] = {
  alt: { es: 'Ilustración de caricatura: tres montones de monedas de oro, uno chico, uno mediano y uno grande, cada uno con el ejército que alcanza a comprar: dos campesinos, un caballero con un arquero, y un gigante con Zeus.', en: 'Cartoon illustration: three piles of gold coins, small, medium and large, each with the army it can afford: two farmers, a knight with an archer, and a giant with Zeus.' },
  hacer: (S, L) => {
    const pila = (cx, filas) => { let s = ''; for (let f = 0; f < filas; f++) for (let k = 0; k < filas - f; k++) s += L.moneda(cx + (k - (filas - f - 1) / 2) * 44, 625 - f * 34, 22); return s; };
    return [
      L.fondoPrado({ semilla: 271 }),
      S('campesino', 0, 150, 440, 56, { dir: 1 }), S('campesino', 0, 260, 455, 52, { dir: 1 }),
      S('caballero', 0, 520, 420, 70, { dir: 1 }), S('arquero', 0, 660, 445, 58, { dir: 1 }),
      S('gigante', 0, 930, 410, 88, { dir: 1 }), S('zeus', 0, 1075, 445, 66, { dir: 1, golpe: 0.3 }),
      pila(205, 2), pila(590, 3), pila(1000, 4),
    ];
  },
};

E['llorona-rio'] = {
  alt: { es: 'Ilustración de caricatura: La Llorona, de noche junto a un río bajo la luna, con lágrimas y niebla, mientras un campesino rojo asoma los ojos asustado detrás de una lápida.', en: 'Cartoon illustration: La Llorona at night beside a river under the moon, with tears and mist, while a red farmer peeks out in fear from behind a gravestone.' },
  hacer: (S, L) => [
    L.fondoNoche({ semilla: 281 }),
    '<rect y="520" width="1200" height="155" fill="#25348a"/><path d="M0 520 H1200" stroke="' + L.O + '" stroke-width="8"/><ellipse cx="900" cy="590" rx="120" ry="26" fill="#fff6c8" opacity=".5"/>' +
      [[100, 560], [380, 600], [640, 570], [1050, 630], [230, 640]].map(([x, y]) => '<path d="M' + x + ' ' + y + ' q30 -14 60 0 t60 0" fill="none" stroke="#6f86e8" stroke-width="6" stroke-linecap="round"/>').join(''),
    S('llorona', 0, 420, 400, 150, { dir: 1 }), L.gota(370, 450, 20), L.gota(470, 460, 18), L.gota(330, 520, 14),
    S('campesino', 1, 900, 395, 58, { dir: -1, sombra: false }), L.signo(980, 290, '!', 38),
    '<path d="M840 560 V430 Q840 380 900 380 Q960 380 960 430 V560Z" fill="#4b4f86" stroke="' + L.O + '" stroke-width="7"/><line x1="900" y1="420" x2="900" y2="480" stroke="#6b70b0" stroke-width="9" stroke-linecap="round"/><line x1="878" y1="440" x2="922" y2="440" stroke="#6b70b0" stroke-width="9" stroke-linecap="round"/>',
    '<ellipse cx="300" cy="560" rx="360" ry="40" fill="#9fb4ff" opacity=".2"/>',
  ],
};

module.exports = E;
