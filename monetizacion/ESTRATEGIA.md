# Estrategia de monetización

Escrita el 18 de noviembre de 2026. Las reglas de las plataformas cambian: antes de enviar un juego a un portal o de encender una ruta, hay que releer su documentación. Cada dato dice de dónde sale: **oficial** (documentación de la plataforma, leída al escribir esto), **terceros** (guías, foros, blogs de editores) o **supuesto nuestro**.

## En tres líneas

1. Meter anuncios es lo fácil: el motor ya lo sabe hacer, apagado, y se enciende con una línea. Lo difícil y lo lento es **que alguien los vea**: sin visitas no hay ingresos, y hoy el sitio no tiene analítica.
2. Hay tres rutas. La que puede dar los primeros pesos antes es **un portal con revenue share** (CrazyGames primero), porque aporta sus propios jugadores; **AdSense en el sitio propio** exige dominio propio y aprobaciones que tardan; **las donaciones** son inmediatas pero pequeñas.
3. Los primeros ingresos reales, en el mejor caso, llegan en semanas, y el primer *cobro* en meses, porque los portales pagan al juntar un mínimo (ver las cuentas abajo). Ninguna cifra de aquí es una promesa.

## Las tres rutas

### 1. Portales con revenue share (empezar por CrazyGames)

- **Cómo entra un juego** (oficial): CrazyGames lo revisa con su equipo de calidad; empieza en «Basic Launch», donde **los anuncios están desactivados y no se comparte ningún ingreso**; solo si sus métricas superan los umbrales lo invitan a «Full Launch», con su SDK y los anuncios. O sea: el SDK que ya está listo no genera dinero hasta que el juego demuestre que retiene jugadores.
- **Reglas de anuncios** (oficial): solo los del SDK del portal; anuncios entre niveles o tras perder, nunca durante la partida ni en botones de navegación (menú, ajustes, tienda); la recompensa no puede encadenarse; el juego se pausa durante el anuncio y se silencia cuando el anuncio realmente empieza; un error de anuncio con recompensa no premia. Poki además prohíbe temporizadores propios de anuncios, otros anuncios, pantallas de bienvenida y enlaces de salida, bloquea los productos de Google, pide lienzo 16:9 y menos de 8 MB iniciales; entrega la documentación de su SDK solo después de aceptar el juego.
- **Qué hace el motor** (hecho): el módulo `anuncios` cumple esas reglas por construcción; `python3 fabrica.py monetizar variantes ID` arma la versión para CrazyGames (con la dirección oficial de su SDK, sin enlace de apoyo y con una revisión que rechaza anuncios ajenos y llamadas de salida). Probado en navegador con un SDK simulado; **la prueba real es la herramienta de vista previa del propio portal**, que solo se puede usar con tu cuenta.
- **Qué te toca**: crear la cuenta de desarrollador y dejar listo cómo cobrar (los portales piden el dato de pago antes de recibir un juego), y subir el archivo. Yo preparo el archivo y la ficha.
- **Qué juegos**: Guerreros y Compás pasan el filtro de novedad de la fábrica para portales; **Torre no** (riesgo alto de verse como clon de Stack, ver `python3 fabrica.py novedad`). Poki avisa que no acepta plantillas con poca variación ni juegos hechos solo con IA sin aporte propio (oficial): por eso cada juego debe poder enseñar qué lo hace distinto y qué hizo una persona. No se niega el uso de IA; según terceros, Poki puede pedir el registro de herramientas, instrucciones y cambios, y se entrega si lo piden.
- **Cuánto se queda uno** (terceros, no oficial): CrazyGames no publica su reparto en la documentación principal; las bases de un concurso de 2026 hablan de 60 % de los anuncios. Poki: 100 % del tráfico que uno trae y mitad y mitad del que trae Poki. GameMonetize ronda 45 %. Mínimos de pago: €100 en CrazyGames, €50 en GameDistribution. Revisión de CrazyGames: 1 a 2 días de respuesta; Poki: su prueba web tarda de 5 a 7 días (terceros).

### 2. AdSense en el sitio propio

- **Qué pide Google** (oficial): ser dueño de un sitio de juegos HTML5, cumplir las políticas, y **solicitar aparte «H5 Games Ads»**; Google puede aprobar o rechazar en cualquier momento. Los anuncios de pantalla completa solo en cortes naturales, no tras cada interacción ni interrumpiendo el juego. Para tráfico del EEE, el Reino Unido y Suiza se exige un mensaje de consentimiento certificado.
- **Dominio propio** (terceros): varios editores reportan que AdSense no aprueba sitios en subdominios gratuitos (como `*.vercel.app` o `*.netlify.app`). Hoy el sitio vive en `taller-gelatina.pages.dev`; no lo verifiqué con Google, pero es la señal más fuerte de que hace falta comprar un dominio (un gasto tuyo, no mío).
- **Contenido escaso** (terceros): con solo dos o tres juegos y poco texto, AdSense puede rechazar por «contenido de poco valor». Es el motivo para que los portales vayan primero.
- **Qué hace el motor** (hecho): con la ruta encendida y `adsense_publisher` puesto, construye los juegos con el módulo cargando AdSense en **modo de prueba** (`data-adbreak-test`) hasta que el dueño lo apague; el sitio ya genera `ads.txt` y cambia la privacidad al texto con anuncios.
- **Qué te toca**: dominio, cuenta de AdSense, solicitud de H5 Games Ads, el mensaje de consentimiento en la cuenta y el identificador `pub-…`.

### 3. Donaciones y pago libre

- El botón de apoyo ya existe y aparece solo si el juego tiene `apoyo_url`. Falta únicamente el enlace de una cuenta tuya. Cada juego que se actualice con el enlace es una versión nueva y la apruebas tú.
- Esperable: poco. Sirve para empezar a cobrar sin esperar aprobaciones y para medir cuánta gente quiere apoyar.

## Cuentas con la fórmula

Ingresos = sesiones × anuncios por sesión × relleno × eCPM / 1000 (la fórmula es de terceros y estándar en el sector). **Los supuestos son nuestros**: 2 anuncios por sesión, 70 % de relleno, eCPM de US$2 a US$5 (prudente; los portales con tráfico de Estados Unidos y Europa pagan más y el tráfico de América Latina menos). Con datos reales se reemplazan.

| Sesiones por día | Por mes con eCPM US$2 | Por mes con eCPM US$5 |
|---|---|---|
| 100 | US$8 | US$21 |
| 1,000 | US$84 | US$210 |
| 10,000 | US$840 | US$2,100 |

Con 100 sesiones por día, llegar a un mínimo de pago de 50 tarda de 2 a 6 meses; con 1,000, de 1 a 3 semanas. **El factor que manda es el tráfico**, y por eso las dos palancas reales son: entrar a un portal (que trae jugadores) y la difusión que ya opera el motor. `python3 fabrica.py monetizar escenarios N` hace las cuentas para otro tráfico.

## Qué hace el motor solo y qué no

| Lo hace solo | Lo hace el dueño |
|---|---|
| Módulo `anuncios`: cortes naturales, pausa y silencio, lector de pantalla, tope y espera, recompensa que no premia sin anuncio visto | Crear cuentas (portales, AdSense, propinas) y fijar cómo cobrar |
| Política `monetizacion/politica.json`: todo apagado hasta que se decida | Comprar el dominio si se va por AdSense |
| Versión para CrazyGames con revisión automática | Subir el archivo al portal con su cuenta |
| Estado semanal en `publicacion/PENDIENTE.md`: qué falta por ruta y de quién es cada pendiente | Encender una ruta (cambia lo que el sitio le promete al jugador) |
| Cuentas con supuestos explícitos | Aprobar cada versión nueva de un juego publicado |

## Orden de trabajo

1. **Ya hecho**: módulo, política, estado, versión para CrazyGames, ganchos en Compás (aún no publicado: sale con anuncios apagados en el sitio propio, y la versión de portal los usa) y su **paquete de envío a CrazyGames** (`python3 fabrica.py monetizar envio compas-gelatina`: tres portadas, dos videos de vista previa y la ficha `kit/ficha-crazygames.md`, con cada requisito del portal contra el estado real del juego). Con CrazyGames, el módulo toma el idioma del jugador de su SDK, como exige el portal.
2. **Compás primero** como ejemplo de portal. Los ganchos de **Guerreros** (anuncio al pasar a otra batalla desde el cartel de resultado) ya están en la rama `guerreros-1.5.0-anuncios`, junto a su actualización de calidad: apagados por defecto y sin publicar; el paquete de envío de Guerreros se hace después, si se decide mandarlo a un portal. Torre, solo si se decide mandarlo a portales distinto de Stack.
3. **Medición**: decidir la analítica (Cloudflare Web Analytics) para saber cuántas sesiones hay. Sin eso, no hay cuentas reales.
4. **AdSense** solo cuando haya dominio y tráfico que justifique la espera de aprobación.
5. **Datos de ingresos**: hoy no se leen solos (los reportes de cada portal y de AdSense necesitan una clave tuya); se anotan con `python3 fabrica.py metricas anotar`. Leerlos solos sería la siguiente mejora del motor y requiere esas claves.

## Lo que no está verificado

- El reparto exacto de CrazyGames, los umbrales de su paso a Full Launch y la herramienta de vista previa: solo se pueden ver con una cuenta.
- La forma exacta de las llamadas de los SDK de CrazyGames (`requestAd` y sus eventos), de Poki y de AdSense (`adBreak`) está implementada según la documentación que pude leer y según mi conocimiento de los SDK; probada con simulaciones, no contra los servicios reales. Poki está como borrador hasta que entregue su documentación.
- Que AdSense rechace `pages.dev` (reportes de terceros, no Google).
- Que el mensaje de consentimiento de la propia cuenta de AdSense cubra el requisito del EEE: depende de cómo se configure en la cuenta.
- Cualquier cifra de ingresos: son cuentas con supuestos, no pronósticos.

## Fuentes

- CrazyGames, requisitos de anuncios: https://docs.crazygames.com/requirements/ads/ · SDK: https://docs.crazygames.com/sdk/intro/ · requisitos generales: https://docs.crazygames.com/requirements/intro/
- Poki, requisitos: https://sdk.poki.com/new-requirements · trabajo con IA: https://sdk.poki.com/working-with-ai · guía de calidad: https://sdk.poki.com/poki-quality-guidelines
- AdSense H5 Games Ads: https://adsense.google.com/start/h5-games-ads/ · políticas de anuncios de pantalla completa: https://support.google.com/publisherpolicies/answer/11975916 · consentimiento en el EEE y el Reino Unido: https://support.google.com/adsense/answer/13554116
- Terceros (reparto, mínimos, plazos): https://app.cinevva.com/guides/web-game-monetization · https://app.cinevva.com/guides/publish-game-crazygames · https://app.cinevva.com/guides/publish-game-poki
- Terceros (AdSense y subdominios): https://dev.to/morinaga/why-google-adsense-will-not-approve-a-vercelapp-site-110b
- Terceros (fórmula de ingresos): https://playgama.com/blog/business-faqs/how-much-can-i-earn-from-ads/
