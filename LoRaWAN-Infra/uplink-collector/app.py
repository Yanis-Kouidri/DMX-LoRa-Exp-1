import json
import os
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt
import psycopg
from psycopg.types.json import Jsonb

MQTT_HOST = os.getenv("MQTT_HOST", "mosquitto")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv(
    "MQTT_TOPIC",
    "application/7c5f57e0-c72d-4452-a5e6-58dac3bc32e8/device/+/event/up",
)

POSTGRES_DSN = os.getenv(
    "POSTGRES_DSN",
    "postgresql://chirpstack:chirpstack@postgres:5432/lorawan_experiments",
)

DB_RETRY_MAX_DELAY_S = 30


def insert_uplink(event, record, rx):
    with psycopg.connect(POSTGRES_DSN) as conn:
        with conn.cursor() as cur:
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
                    "deduplication_id": event.get("deduplicationId"),
                    "uplink_id": rx.get("uplinkId"),
                    "confirmed": event.get("confirmed"),
                    "data_rate": event.get("dr"),
                    "gw_time": rx.get("gwTime"),
                    "ns_time": rx.get("nsTime"),
                    "raw_event": Jsonb(event),
                },
            )
            return cur.rowcount == 1


def store_uplink(event, record, rx):
    # Retry until PostgreSQL is reachable: the message is only acknowledged to
    # the broker once this returns, so it is never dropped while the DB is down.
    # If the MQTT connection times out meanwhile, the broker redelivers it and
    # the ON CONFLICT clause discards the duplicate.
    delay = 1
    while True:
        try:
            return insert_uplink(event, record, rx)
        except psycopg.OperationalError as err:
            print(f"PostgreSQL unavailable, retrying in {delay}s: {err}", flush=True)
            time.sleep(delay)
            delay = min(delay * 2, DB_RETRY_MAX_DELAY_S)


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code != 0:
        raise RuntimeError(f"MQTT connection failed: {reason_code}")
    print(f"Connected to MQTT — subscribed to: {MQTT_TOPIC}", flush=True)
    client.subscribe(MQTT_TOPIC, qos=1)


def on_message(client, userdata, message):
    try:
        event = json.loads(message.payload.decode("utf-8"))
        rx = (event.get("rxInfo") or [{}])[0]
        lora = event.get("txInfo", {}).get("modulation", {}).get("lora", {})
        record = {
            "received_at": event.get("time"),
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "dev_eui": event.get("deviceInfo", {}).get("devEui"),
            "gateway_id": rx.get("gatewayId"),
            "f_cnt": event.get("fCnt"),
            "f_port": event.get("fPort"),
            "frequency_hz": event.get("txInfo", {}).get("frequency"),
            "bandwidth_hz": lora.get("bandwidth"),
            "spreading_factor": lora.get("spreadingFactor"),
            "coding_rate": lora.get("codeRate"),
            "channel": rx.get("channel"),
            "rssi_dbm": rx.get("rssi"),
            "snr_db": rx.get("snr"),
            "payload_base64": event.get("data"),
        }
    except (ValueError, AttributeError, TypeError) as err:
        print(f"Malformed message skipped on {message.topic}: {err}: {message.payload!r}", flush=True)
        return

    try:
        inserted = store_uplink(event, record, rx)
    except psycopg.Error as err:
        print(f"Uplink rejected by PostgreSQL: {err}: {message.payload!r}", flush=True)
        return

    if inserted:
        print(json.dumps(record, separators=(",", ":")), flush=True)
    else:
        print(
            f"Duplicate uplink skipped: deduplicationId={event.get('deduplicationId')} "
            f"gateway={record['gateway_id']} fCnt={record['f_cnt']}",
            flush=True,
        )


client = mqtt.Client(
    mqtt.CallbackAPIVersion.VERSION2,
    client_id="uplink-collector",
    clean_session=False,
)
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
client.loop_forever()
