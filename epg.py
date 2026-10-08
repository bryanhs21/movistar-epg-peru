import csv
import html
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

API_URL = "https://contentapi-pe.cdn.telefonica.com/28/default/es-PE/schedules"
CHANNEL_PIDS = ['lch6291', 'lch6299', 'lch6479', 'lch5665', 'lch7229', 'lch7263', 'lch7262', 'lch7245', 'lch7226', 'lch6303', 'lch6306', 'lch6304', 'lch6294', 'lch6292', 'lch6476', 'lch6316', 'lch6475', 'lch6477', 'lch6992', 'lch7204', 'lch7249', 'lch2359', 'lch7108', 'lch7275', 'lch6478', 'lch6480', 'lch7114', 'lch6302', 'lch7281', 'lch6310', 'lch6312', 'lch7203', 'lch6473', 'lch6289', 'lch6308', 'lch6616', 'lch5626', 'lch7115', 'lch7205', 'lch6293', 'lch5704', 'lch2300', 'lch7231', 'lch6619', 'lch7228', 'lch7106', 'lch7230', 'lch5624', 'lch6469', 'lch7250', 'lch7227', 'lch2358', 'lch2357', 'lch2291', 'lch2335', 'lch2328', 'lch7233', 'lch6559', 'lch7254', 'lch7232', 'lch7251', 'lch3489', 'lch7261', 'lch5703', 'lch7265', 'lch2245', 'lch7253', 'lch7252', 'lch2227', 'lch2325', 'lch7234', 'lch5623', 'lch5700', 'lch7264', 'lch6307', 'lch7161', 'lch6311', 'lch7110', 'lch6519', 'lch6470', 'lch4105', 'lch7202', 'lch7224', 'lch7295', 'lch2340', 'lch7276', 'lch6518', 'lch6517', 'lch6295', 'lch6305', 'lch5701', 'lch3753', 'lch6471', 'lch6468', 'lch7217', 'lch2219', 'lch6309', 'lch7216', 'lch2775', 'lch3952', 'lch2776', 'lch2813', 'lch2339', 'lch2341', 'lch5483', 'lch2201', 'lch3298', 'lch2349', 'lch2203', 'lch3297', 'lch2204', 'lch2318', 'lch2205', 'lch2459']
PERU = timezone(timedelta(hours=-5))

FIELDS = (
    "Pid,Title,Description,ChannelName,ChannelNumber,CallLetter,Start,End,"
    "EpgNetworkDvr,LiveChannelPid,LiveProgramPid,EpgSerieId,SeriesPid,SeriesId,"
    "SeasonPid,SeasonNumber,images.videoFrame,images.banner,LiveToVod,AgeRatingPid,"
    "forbiddenTechnology,IsSoDisabled"
)

def clean(value):
    return html.unescape(str(value or "")).strip()

def xml_time(ts):
    return datetime.fromtimestamp(int(ts), timezone.utc).astimezone(PERU).strftime("%Y%m%d%H%M%S -0500")

def fetch(start_ts, end_ts):
    params = {
        "ca_deviceTypes": "null|401",
        "ca_channelmaps": "142|null",
        "fields": FIELDS,
        "includeRelations": "Genre",
        "orderBy": "START_TIME:a",
        "filteravailability": "false",
        "includeAttributes": "ca_cpvrDisable,ca_descriptors,ca_blackout_target,ca_blackout_areas",
        "starttime": str(start_ts),
        "endtime": str(end_ts),
        "livechannelpids": ",".join(CHANNEL_PIDS),
        "offset": "0",
        "limit": "1000",
    }
    r = requests.get(
        API_URL,
        params=params,
        headers={"User-Agent": "Mozilla/5.0 (EPG generator; GitHub Actions)", "Accept": "application/json"},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()

    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        candidates = ("Content", "content", "Schedules", "schedules", "Items", "items", "Results", "results", "data")
        for key in candidates:
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                for sub in candidates + ("List", "list"):
                    if isinstance(value.get(sub), list):
                        return value[sub]
    raise RuntimeError("No se encontró una lista de programas en la respuesta.")

def main():
    now = int(time.time())
    records = fetch(now - 86400, now + 14 * 86400)
    valid = {p.lower() for p in CHANNEL_PIDS}

    channels = {}
    programs = {}

    for item in records:
        pid = clean(item.get("LiveChannelPid")).lower()
        if pid not in valid:
            continue

        name = clean(item.get("ChannelName"))
        call = clean(item.get("CallLetter"))
        number = clean(item.get("ChannelNumber"))

        current = channels.setdefault(pid, {
            "number": number,
            "name": name or call or pid.upper(),
            "call": call,
        })
        if not current["number"] and number:
            current["number"] = number
        if current["name"] == pid.upper() and (name or call):
            current["name"] = name or call
        if not current["call"] and call:
            current["call"] = call

        try:
            start = int(item["Start"])
            end = int(item["End"])
        except (KeyError, TypeError, ValueError):
            continue
        if end <= start:
            continue

        title = clean(item.get("Title")) or current["name"]
        desc = clean(item.get("Description"))
        key = clean(item.get("Pid")) or f"{pid}|{start}|{end}|{title}"
        programs[(pid, key)] = (start, end, title, desc)

    if not programs:
        raise RuntimeError("No se encontraron programas válidos. No se publicará un EPG vacío.")

    with open("canales.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["channel_number", "channel_name", "call_letter", "live_channel_pid", "xmltv_tvg_id"])
        for pid, info in sorted(channels.items(), key=lambda x: (x[1]["number"] or "999999", x[1]["name"], x[0])):
            w.writerow([info["number"], info["name"], info["call"], pid, pid])

    tv = ET.Element("tv", {
        "generator-info-name": "EPG Telefónica Perú automático",
        "generator-info-url": "https://contentapi-pe.cdn.telefonica.com/",
    })

    for pid, info in sorted(channels.items(), key=lambda x: (x[1]["number"] or "999999", x[1]["name"], x[0])):
        ch = ET.SubElement(tv, "channel", {"id": pid})
        ET.SubElement(ch, "display-name", {"lang": "es"}).text = info["name"]
        if info["call"] and info["call"] != info["name"]:
            ET.SubElement(ch, "display-name", {"lang": "es"}).text = info["call"]
        if info["number"]:
            ET.SubElement(ch, "display-name", {"lang": "es"}).text = info["number"]

    for (pid, _), (start, end, title, desc) in sorted(
        programs.items(), key=lambda x: (x[0][0], x[1][0], x[1][1])
    ):
        p = ET.SubElement(tv, "programme", {
            "start": xml_time(start),
            "stop": xml_time(end),
            "channel": pid,
        })
        ET.SubElement(p, "title", {"lang": "es"}).text = title
        if desc:
            ET.SubElement(p, "desc", {"lang": "es"}).text = desc

    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write("epg.xml", encoding="UTF-8", xml_declaration=True)

    print(f"Registros recibidos: {len(records)}")
    print(f"Canales encontrados: {len(channels)}")
    print(f"Programas generados: {len(programs)}")
    print("Generados: epg.xml y canales.csv")

if __name__ == "__main__":
    main()
