# EPG Telefónica Perú — todos los canales

EPG XMLTV independiente de cualquier lista M3U.

## Uso manual

No modifica ni necesita tu M3U. Puedes introducir la URL del EPG manualmente en tu aplicación IPTV.

El proyecto genera `canales.csv` con:

- Número de canal
- Nombre
- Call Letter
- LiveChannelPid
- XMLTV tvg-id

El `tvg-id`/`channel id` utilizado es el `LiveChannelPid` de Telefónica. Esto mantiene una identificación estable y evita depender de nombres que pueden variar. XMLTV requiere que el `channel` de cada programa corresponda al `id` del canal. citeturn0search0

Ejemplos:

- L1 MAX → `lch7216`
- L1 → `lch7217`

## Archivos generados

- `epg.xml` → EPG completo
- `canales.csv` → tabla para realizar la asignación manual

## Actualización

GitHub Actions consulta la API cada 6 horas.

Ventana:
- 1 día hacia atrás
- 14 días hacia adelante

Si la API no devuelve programación válida, el workflow falla y no publica un EPG vacío.

## URL prevista

https://raw.githubusercontent.com/bryanhs21/limaxby-epg/refs/heads/main/epg.xml
