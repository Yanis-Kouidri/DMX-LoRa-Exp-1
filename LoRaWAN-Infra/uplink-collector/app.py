import base64
import hashlib
import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg
from chirpstack_api import gw
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import DecodeError
from psycopg.types.json import Jsonb

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
# Device integration events (up, join, ack, txack, status, log, location,
# integration) and all gateway <-> network server traffic of every region.
MQTT_TOPICS = os.getenv(
    "MQTT_TOPICS",
    "application/+/device/+/event/+,+/gateway/+/+/+",
).split(",")

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://chirpstack:chirpstack@postgres:5432/lorawan_experiments",
)

DB_RETRY_MAX_DELAY_S = 30

# Protobuf message carried by each gateway topic ({direction}/{type}).
GATEWAY_MESSAGES = {
    ("event", "up"): gw.UplinkFrame,
    ("event", "stats"): gw.GatewayStats,
    ("event", "ack"): gw.DownlinkTxAck,
    ("event", "exec"): gw.GatewayCommandExecResponse,
    ("event", "raw"): gw.RawPacketForwarderEvent,
    ("state", "conn"): gw.ConnState,
    ("command", "down"): gw.DownlinkFrame,
    ("command", "config"): gw.GatewayConfiguration,
    ("command", "exec"): gw.GatewayCommandExecRequest,
    ("command", "raw"): gw.RawPacketForwarderCommand,
}

M_TYPES = [
    "JoinRequest",
    "JoinAccept",
    "UnconfirmedDataUp",
    "UnconfirmedDataDown",
    "ConfirmedDataUp",
    "ConfirmedDataDown",
    "RejoinRequest",
    "Proprietary",
]


class MalformedMessage(Exception):
    pass


def with_db_retry(fn, *args):
    # Retry until PostgreSQL is reachable: the message is only acknowledged to
    # the broker once this returns, so it is never dropped while the DB is down.
    # If the MQTT connection times out meanwhile, the broker redelivers it and
    # the ON CONFLICT clauses discard the duplicate.
    delay = 1
    while True:
        try:
            return fn(*args)
        except psycopg.OperationalError as err:
            print(f"PostgreSQL unavailable, retrying in {delay}s: {err}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, DB_RETRY_MAX_DELAY_S)


def insert_uplinks(cur, event, record, receptions):
    # One row per gateway reception.
    inserted = []
    for reception in receptions:
        cur.execute(
            """
            INSERT INTO uplinks (
                received_at, collected_at, deduplication_id, dev_eui,
                gateway_id, uplink_id,
                f_cnt, f_port, confirmed, data_rate, frequency_hz,
                bandwidth_hz, spreading_factor, coding_rate, channel,
                rssi_dbm, snr_db, gw_time, ns_time, payload_base64, raw_event
            )
            VALUES (
                %(received_at)s, %(collected_at)s, %(deduplication_id)s,
                %(dev_eui)s, %(gateway_id)s,
                %(uplink_id)s, %(f_cnt)s, %(f_port)s, %(confirmed)s,
                %(data_rate)s, %(frequency_hz)s, %(bandwidth_hz)s,
                %(spreading_factor)s, %(coding_rate)s, %(channel)s,
                %(rssi_dbm)s, %(snr_db)s, %(gw_time)s, %(ns_time)s,
                %(payload_base64)s, %(raw_event)s
            )
            ON CONFLICT (deduplication_id, gateway_id) DO NOTHING
            """,
            {
                **record,
                **reception,
                "deduplication_id": event.get("deduplicationId"),
                "confirmed": event.get("confirmed"),
                "data_rate": event.get("dr"),
                "raw_event": Jsonb(event),
            },
        )
        inserted.append(cur.rowcount == 1)
    return inserted


def insert_device_event(cur, row):
    cur.execute(
        """
        INSERT INTO device_events (
            event_type, time, collected_at, deduplication_id, application_id,
            dev_eui, device_name, f_cnt, log_level, log_code, log_description,
            raw_event, message_sha256
        )
        VALUES (
            %(event_type)s, %(time)s, %(collected_at)s, %(deduplication_id)s,
            %(application_id)s, %(dev_eui)s, %(device_name)s, %(f_cnt)s,
            %(log_level)s, %(log_code)s, %(log_description)s, %(raw_event)s,
            %(message_sha256)s
        )
        ON CONFLICT (message_sha256) DO NOTHING
        """,
        row,
    )
    return cur.rowcount == 1


def store_device_event(row, uplink):
    # The event and its uplink rows are committed in a single transaction.
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
            inserted = insert_device_event(cur, row)
            uplinks_inserted = insert_uplinks(cur, *uplink) if uplink else []
    return inserted, uplinks_inserted


def store_gateway_event(row):
    with psycopg.connect(POSTGRES_DSN) as conn:
        conn.execute(
            """
            INSERT INTO gateway_events (
                region, gateway_id, direction, event_type, time, collected_at,
                frequency_hz, bandwidth_hz, spreading_factor, rssi_dbm, snr_db,
                crc_status, m_type, dev_addr, dev_eui, f_cnt,
                phy_payload_base64, raw_event
            )
            VALUES (
                %(region)s, %(gateway_id)s, %(direction)s, %(event_type)s,
                %(time)s, %(collected_at)s, %(frequency_hz)s, %(bandwidth_hz)s,
                %(spreading_factor)s, %(rssi_dbm)s, %(snr_db)s, %(crc_status)s,
                %(m_type)s, %(dev_addr)s, %(dev_eui)s, %(f_cnt)s,
                %(phy_payload_base64)s, %(raw_event)s
            )
            """,
            row,
        )


def parse_uplink(event):
    lora = event.get("txInfo", {}).get("modulation", {}).get("lora", {})
    record = {
        "received_at": event.get("time"),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "dev_eui": event.get("deviceInfo", {}).get("devEui"),
        "f_cnt": event.get("fCnt"),
        "f_port": event.get("fPort"),
        "frequency_hz": event.get("txInfo", {}).get("frequency"),
        "bandwidth_hz": lora.get("bandwidth"),
        "spreading_factor": lora.get("spreadingFactor"),
        "coding_rate": lora.get("codeRate"),
        "payload_base64": event.get("data"),
    }
    receptions = [
        {
            "gateway_id": rx.get("gatewayId"),
            "uplink_id": rx.get("uplinkId"),
            "channel": rx.get("channel"),
            "rssi_dbm": rx.get("rssi"),
            "snr_db": rx.get("snr"),
            "gw_time": rx.get("gwTime"),
            "ns_time": rx.get("nsTime"),
        }
        for rx in event.get("rxInfo") or [{}]
    ]
    return event, record, receptions


def handle_device_event(message, event_type):
    try:
        event = json.loads(message.payload.decode("utf-8"))
        device = event.get("deviceInfo") or {}
        row = {
            "event_type": event_type,
            "time": event.get("time"),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "deduplication_id": event.get("deduplicationId"),
            "application_id": device.get("applicationId"),
            "dev_eui": device.get("devEui"),
            "device_name": device.get("deviceName"),
            "f_cnt": event.get("fCnt", event.get("fCntDown")),
            "log_level": event.get("level"),
            "log_code": event.get("code"),
            "log_description": event.get("description"),
            "raw_event": Jsonb(event),
            "message_sha256": hashlib.sha256(message.payload).hexdigest(),
        }
        uplink = parse_uplink(event) if event_type == "up" else None
    except (ValueError, AttributeError, TypeError) as err:
        raise MalformedMessage(err) from err

    inserted, uplinks_inserted = with_db_retry(store_device_event, row, uplink)

    print(
        f"{'Stored' if inserted else 'Duplicate skipped'}: {event_type} event "
        f"dev_eui={row['dev_eui']} fCnt={row['f_cnt']}",
        flush=True,
    )
    if uplink:
        _, record, receptions = uplink
        for reception, was_inserted in zip(receptions, uplinks_inserted):
            if was_inserted:
                print(json.dumps({**record, **reception}, separators=(",", ":")), flush=True)
            else:
                print(
                    f"Duplicate uplink skipped: deduplicationId={event.get('deduplicationId')} "
                    f"gateway={reception['gateway_id']} fCnt={record['f_cnt']}",
                    flush=True,
                )


def decode_gateway_message(direction, event_type, payload):
    if payload.startswith(b"{"):
        return json.loads(payload.decode("utf-8"))
    message_type = GATEWAY_MESSAGES.get((direction, event_type))
    if message_type is None:
        return {"payloadBase64": base64.b64encode(payload).decode()}
    message = message_type()
    try:
        message.ParseFromString(payload)
    except DecodeError as err:
        # Keep the undecodable message rather than dropping it.
        return {"payloadBase64": base64.b64encode(payload).decode(), "decodeError": str(err)}
    return MessageToDict(message, always_print_fields_with_no_presence=True)


def parse_phy_payload(phy_b64):
    fields = {"m_type": None, "dev_addr": None, "dev_eui": None, "f_cnt": None}
    if not phy_b64:
        return fields
    phy = base64.b64decode(phy_b64)
    if not phy:
        return fields
    m_type = phy[0] >> 5
    fields["m_type"] = M_TYPES[m_type]
    if m_type in (2, 3, 4, 5) and len(phy) >= 8:
        fields["dev_addr"] = phy[1:5][::-1].hex()
        fields["f_cnt"] = int.from_bytes(phy[6:8], "little")
    elif m_type == 0 and len(phy) >= 17:
        fields["dev_eui"] = phy[9:17][::-1].hex()
    return fields


def handle_gateway_event(message, region, gateway_id, direction, event_type):
    try:
        event = decode_gateway_message(direction, event_type, message.payload)
        collected_at = datetime.now(timezone.utc).isoformat()
        # Uplinks carry one frame; downlinks carry one item per RX window.
        frame = event if direction == "event" else (event.get("items") or [{}])[0]
        tx = frame.get("txInfo") or {}
        lora = (tx.get("modulation") or {}).get("lora") or {}
        rx = event.get("rxInfo") or {}
        row = {
            "region": region,
            "gateway_id": gateway_id,
            "direction": direction,
            "event_type": event_type,
            "time": rx.get("gwTime") or rx.get("nsTime") or event.get("time") or collected_at,
            "collected_at": collected_at,
            "frequency_hz": tx.get("frequency"),
            "bandwidth_hz": lora.get("bandwidth"),
            "spreading_factor": lora.get("spreadingFactor"),
            "rssi_dbm": rx.get("rssi"),
            "snr_db": rx.get("snr"),
            "crc_status": rx.get("crcStatus"),
            "phy_payload_base64": frame.get("phyPayload") or None,
            "raw_event": Jsonb(event),
        }
        row.update(parse_phy_payload(row["phy_payload_base64"]))
    except (ValueError, AttributeError, TypeError, IndexError) as err:
        raise MalformedMessage(err) from err

    with_db_retry(store_gateway_event, row)
    print(
        f"Stored: gateway {direction}/{event_type} gateway={gateway_id} "
        f"m_type={row['m_type']} dev_addr={row['dev_addr']} fCnt={row['f_cnt']}",
        flush=True,
    )


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        raise RuntimeError(f"MQTT connection failed: {reason_code}")
    print(f"Connected to MQTT — subscribed to: {', '.join(MQTT_TOPICS)}", flush=True)
    client.subscribe([(topic, 1) for topic in MQTT_TOPICS])


def on_message(client, userdata, message):
    # Retained messages (gateway conn state) are replays of an earlier event
    # sent on every (re)subscription, not new events.
    if message.retain:
        return

    parts = message.topic.split("/")
    try:
        if len(parts) == 6 and parts[0] == "application" and parts[4] == "event":
            handle_device_event(message, parts[5])
        elif len(parts) == 5 and parts[1] == "gateway":
            handle_gateway_event(message, parts[0], parts[2], parts[3], parts[4])
        else:
            print(f"Unexpected topic skipped: {message.topic}", flush=True)
    except MalformedMessage as err:
        print(f"Malformed message skipped on {message.topic}: {err}: {message.payload!r}", flush=True)
    except psycopg.Error as err:
        print(f"Message rejected by PostgreSQL on {message.topic}: {err}: {message.payload!r}", flush=True)


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="uplink-collector",
    clean_session=False,
)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
client.loop_forever()
