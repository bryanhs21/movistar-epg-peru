import csv
import html
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import requests

API_URL = "https://contentapi-pe.cdn.telefonica.com/28/default/es-PE/schedules"

CHANNEL_PIDS = ['lch6291', 'lch6299', 'lch6479', 'lch5665', 'lch7229', 'lch7263', 'lch7262', 'lch7245', 'lch7226', 'lch6303', 'lch6306', 'lch6304', 'lch6294', 'lch6292', 'lch6476', 'lch6316', 'lch6475', 'lch6477', 'lch6992', 'lch7204', 'lch7249', 'lch2359', 'lch7108', 'lch7275', 'lch6478', 'lch6480', 'lch7114', 'lch6302', 'lch7281', 'lch6310', 'lch6312', 'lch7203', 'lch6473', 'lch6289', 'lch6308', 'lch6616', 'lch5626', 'lch7115', 'lch7205', 'lch6293', 'lch5704', 'lch2300', 'lch7231', 'lch6619', 'lch7228', 'lch7106', 'lch7230', 'lch5624', 'lch6469', 'lch7250', 'lch7227', 'lch2358', 'lch2357', 'lch2291', 'lch2335', 'lch2328', 'lch7233', 'lch6559', 'lch7254', 'lch7232', 'lch7251', 'lch3489', 'lch7261', 'lch5703', 'lch7265', 'lch2245', 'lch7253', 'lch7252', 'lch2227', 'lch2325', 'lch7234', 'lch5623', 'lch5700', 'lch7264', 'lch6307', 'lch7161', 'lch6311', 'lch7110', 'lch6519', 'lch6470', 'lch4105', 'lch7202', 'lch7224', 'lch7295', 'lch2340', 'lch7276', 'lch6518', 'lch6517', 'lch6295', 'lch6305', 'lch5701', 'lch3753', 'lch6471', 'lch6468', 'lch7217', 'lch2219', 'lch6309', 'lch7216', 'lch2775', 'lch3952', 'lch2776', 'lch2813', 'lch2339', 'lch2341', 'lch5483', 'lch2201', 'lch3298', 'lch2349', 'lch2203', 'lch3297', 'lch2204', 'lch2318', 'lch2205', 'lch2459']

PERU = timezone(timedelta(hours=-5))

# The source URLs supplied by the user use up to 10 channel PIDs
# and a 24-hour window. We preserve that pattern to avoid HTTP 400.
CHANNELS_PER_REQUEST = 10
HOURS_PER_REQUEST = 24
PAGE_SIZE = 1000

FIELDS = (
    "Pid,Title,Description,ChannelName,ChannelNumber,CallLetter,Start,End,"
    "EpgNetworkDvr,LiveChannelPid,LiveProgramPid,EpgSerieId,SeriesPid,SeriesId,"
    "SeasonPid,SeasonNumber,images.videoFrame,images.banner,LiveToVod,AgeRatingPid,"
    "forbiddenTechnology,IsSoDisabled"
)

def clean(value):
    return html.unescape(str(value or "")).strip()

def xml_time(ts):
    return datetime.fromtimestamp(
        int(ts), timezone.utc
    ).astimezone(PERU).strftime("%Y%m%d%H%M%S -0500")

def extract_records(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return None

    keys = (
        "Content", "content",
        "Schedules", "schedules",
        "Items", "items",
        "Results", "results",
        "data",
        "List", "list",
    )

    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return value

    for key in keys:
        value = data.get(key)
        if isinstance(value, dict):
            result = extract_records(value)
            if result is not None:
                return result

    return None

def request_page(channel_group, start_ts, end_ts, offset):
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
        "livechannelpids": ",".join(channel_group),
        "offset": str(offset),
        "limit": str(PAGE_SIZE),
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (EPG generator; GitHub Actions)",
        "Accept": "application/json",
    }

    response = requests.get(API_URL, params=params, headers=headers, timeout=60)

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP {response.status_code} | "
            f"canales={','.join(channel_group)} | "
            f"start={start_ts} | end={end_ts} | offset={offset} | "
            f"respuesta={response.text[:500]}"
        )

    data = response.json()
    records = extract_records(data)

    if records is None:
        raise RuntimeError(
            f"No se encontró la lista de programas | "
            f"canales={','.join(channel_group)} | "
            f"start={start_ts} | end={end_ts} | offset={offset}"
        )

    return records

def fetch_all():
    now = int(time.time())

    # 1 day backward + 14 days forward, matching the previous design.
    first_day = now - 86400
    final_time = now + 14 * 86400

    # Align to 24-hour UTC blocks.
    block_start = first_day - (first_day % 86400)

    all_records = []
    total_requests = 0

    channel_groups = [
        CHANNEL_PIDS[i:i + CHANNELS_PER_REQUEST]
        for i in range(0, len(CHANNEL_PIDS), CHANNELS_PER_REQUEST)
    ]

    total_blocks = ((final_time - block_start) + 86400 - 1) // 86400
    total_work = len(channel_groups) * total_blocks

    print(f"Canales configurados: {len(CHANNEL_PIDS)}")
    print(f"Grupos: {len(channel_groups)}")
    print(f"Bloques de 24h: {total_blocks}")
    print(f"Consultas máximas previstas: {total_work}")

    for group_index, group in enumerate(channel_groups, start=1):
        current_start = block_start
        block_number = 0

        while current_start < final_time:
            block_number += 1
            current_end = min(current_start + 86400, final_time)

            offset = 0

            while True:
                total_requests += 1

                print(
                    f"[{group_index}/{len(channel_groups)}] "
                    f"bloque {block_number}/{total_blocks} | "
                    f"offset={offset} | canales={','.join(group)}"
                )

                records = request_page(
                    group,
                    current_start,
                    current_end,
                    offset,
                )

                count = len(records)
                print(f"  -> {count} registros")

                all_records.extend(records)

                if count < PAGE_SIZE:
                    break

                offset += PAGE_SIZE

            current_start = current_end

    print(f"Total de peticiones realizadas: {total_requests}")
    print(f"Total de registros recibidos: {len(all_records)}")

    return all_records

def build_files(records):
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

        current = channels.setdefault(
            pid,
            {
                "number": number,
                "name": name or call or pid.upper(),
                "call": call,
            },
        )

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
        description = clean(item.get("Description"))
        program_pid = clean(item.get("Pid"))

        key = program_pid or f"{pid}|{start}|{end}|{title}"

        programs[(pid, key)] = {
            "start": start,
            "end": end,
            "title": title,
            "description": description,
        }

    if not channels:
        raise RuntimeError("No se encontraron canales válidos.")

    if not programs:
        raise RuntimeError(
            "No se encontraron programas válidos. "
            "No se publicará un EPG vacío."
        )

    # Manual channel mapping.
    with open("canales.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "channel_number",
                "channel_name",
                "call_letter",
                "live_channel_pid",
                "xmltv_tvg_id",
            ]
        )

        for pid, info in sorted(
            channels.items(),
            key=lambda x: (
                x[1]["number"] or "999999",
                x[1]["name"],
                x[0],
            ),
        ):
            writer.writerow(
                [
                    info["number"],
                    info["name"],
                    info["call"],
                    pid,
                    pid,
                ]
            )

    # XMLTV.
    tv = ET.Element(
        "tv",
        {
            "generator-info-name": "EPG Telefónica Perú automático",
            "generator-info-url": "https://contentapi-pe.cdn.telefonica.com/",
        },
    )

    for pid, info in sorted(
        channels.items(),
        key=lambda x: (
            x[1]["number"] or "999999",
            x[1]["name"],
            x[0],
        ),
    ):
        channel = ET.SubElement(tv, "channel", {"id": pid})

        ET.SubElement(
            channel,
            "display-name",
            {"lang": "es"},
        ).text = info["name"]

        if info["call"] and info["call"] != info["name"]:
            ET.SubElement(
                channel,
                "display-name",
                {"lang": "es"},
            ).text = info["call"]

        if info["number"]:
            ET.SubElement(
                channel,
                "display-name",
                {"lang": "es"},
            ).text = info["number"]

    for (pid, _), program in sorted(
        programs.items(),
        key=lambda x: (
            x[0][0],
            x[1]["start"],
            x[1]["end"],
        ),
    ):
        programme = ET.SubElement(
            tv,
            "programme",
            {
                "start": xml_time(program["start"]),
                "stop": xml_time(program["end"]),
                "channel": pid,
            },
        )

        ET.SubElement(
            programme,
            "title",
            {"lang": "es"},
        ).text = program["title"]

        if program["description"]:
            ET.SubElement(
                programme,
                "desc",
                {"lang": "es"},
            ).text = program["description"]

    ET.indent(tv, space="  ")

    ET.ElementTree(tv).write(
        "epg.xml",
        encoding="UTF-8",
        xml_declaration=True,
    )

    print(f"Canales encontrados: {len(channels)}")
    print(f"Programas únicos generados: {len(programs)}")
    print("Generados correctamente: epg.xml y canales.csv")

def main():
    records = fetch_all()
    build_files(records)

if __name__ == "__main__":
    main()
