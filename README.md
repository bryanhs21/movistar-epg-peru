# EPG Telefónica Perú — todos los canales

Generador XMLTV independiente de cualquier lista M3U.

## Fuente

Utiliza directamente el endpoint de programación de Telefónica Perú.

## 114 canales

El proyecto contiene los 114 `LiveChannelPid` proporcionados en las URLs `schedule`.

## Cómo evita el HTTP 400

La API original proporcionada utiliza consultas de aproximadamente 10 canales y 24 horas.

Por ello el generador:

1. Divide los canales en grupos de máximo 10.
2. Consulta la programación en bloques de 24 horas.
3. Utiliza `offset=0,1000,2000...` si un bloque supera 1000 registros.
4. Junta todos los resultados.
5. Elimina duplicados por `Pid`.
6. Genera `epg.xml` y `canales.csv`.

Ventana temporal:

- 1 día hacia atrás.
- 14 días hacia adelante.

## Archivos

`epg.xml`
: EPG XMLTV completo.

`canales.csv`
: tabla para asignación manual de los canales.

Columnas:

`channel_number, channel_name, call_letter, live_channel_pid, xmltv_tvg_id`

Ejemplo:

`14,L1MAX,LIGA 1 MAX,lch7216,lch7216`

## M3U

No modifica ni necesita una lista M3U.

Puedes colocar el EPG manualmente en tu aplicación IPTV.

## URL prevista

https://raw.githubusercontent.com/bryanhs21/limaxby-epg/refs/heads/main/epg.xml

## Actualización

GitHub Actions ejecuta el proceso cada 6 horas y permite ejecución manual.
