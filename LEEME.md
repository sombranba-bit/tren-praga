# Rastreador tren Madrid → Zaragoza (vuelta de Praga, 5 ene 2027)

Cada 3 horas GitHub consulta los precios de Renfe (AVE, Avlo, Alvia) y Ouigo para
4 adultos con salida entre las 14:00 y las 19:30, y guarda cada pasada. La página
`index.html` enseña el más barato ahora, el mínimo visto, la evolución por operador
y si conviene comprar o esperar.

Gratis, sin ordenador encendido y sin gastar tokens: lo ejecuta GitHub Actions y
lo publica GitHub Pages.

## Puesta en marcha (una vez, ~10 minutos)

1. Crea una cuenta en github.com si no tienes.
2. **New repository** → nombre `tren-praga` → **Public** → *Create repository*.
   (Público: solo contiene precios de tren, ningún dato personal. Así Actions y
   Pages son gratis sin límite.)
3. **Add file → Upload files** y sube `rastreador.py`, `index.html`,
   `test_rastreador.py` y `LEEME.md` → *Commit changes*.
4. **Add file → Create new file**, escribe como nombre
   `.github/workflows/rastrear.yml`, pega dentro el contenido de ese archivo →
   *Commit changes*.
5. **Settings → Actions → General → Workflow permissions** → marca
   *Read and write permissions* → *Save*.
6. **Settings → Pages** → *Source: Deploy from a branch* → rama `main`, carpeta
   `/ (root)` → *Save*.
7. **Actions → Rastrear precios → Run workflow** para lanzar la primera pasada.
8. Abre `https://TU-USUARIO.github.io/tren-praga/` (guárdala en el móvil).

Si una pasada falla del todo, GitHub te manda un correo. Las pasadas paran solas
después del 5 de enero.

## Cambiar algo

- Franja horaria, fecha o número de viajeros: las 4 líneas de arriba de
  `rastreador.py` (se editan desde la web de GitHub con el lápiz).
- Frecuencia: la línea `cron` de `rastrear.yml` (`23 */3 * * *` = cada 3 h).

## Limitaciones

- **Iryo no se rastrea**: bloquea las consultas desde servidores. Míralo a mano.
- Precios por persona y tarifa base, sin descuentos.
- Renfe abre la venta unos 80 días antes: hasta entonces verás
  «aún no está a la venta».
- Ouigo se consulta por persona; si quedan menos de 4 plazas a ese precio, la
  tabla lo avisa.
- Renfe se consulta con [renfecli](https://github.com/seifreed/renfecli)
  (no oficial, MIT), versión fijada y verificada por huella SHA-256. Si Renfe
  cambia su web, puede dejar de funcionar hasta que se actualice.
