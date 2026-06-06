#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#python mqtt_latency_test.py --mode wss443 --username huber --password "TU_PASSWORD" --count 4000 --interval 0.05 --y-limit 1
#python mqtt_latency_test.py --mode mqtt1883 --username huber --password "TU_PASSWORD" --count 4000 --interval 0.05 --y-limit 1
#python mqtt_latency_test.py --mode mqtts8883 --username huber --password "TU_PASSWORD" --count 4000 --interval 0.05 --y-limit 1
#python mqtt_latency_test.py --mode ws9001 --username huber --password "TU_PASSWORD" --count 4000 --interval 0.05 --y-limit 1

"""
MQTT latency benchmark for mqtt.mecatronica-ibero.mx

Measures end-to-end message latency as observed by the client:
publish timestamp -> broker -> receive subscribed message.

This is not only broker-internal latency. It includes:
- client network path
- TLS overhead, when enabled
- WebSocket overhead, when enabled
- broker processing
- local client scheduling

Install:
    pip install paho-mqtt matplotlib pandas

Examples:
    python mqtt_latency_test.py --mode wss443 --username huber --password "PASSWORD" --count 4000 --interval 0.05
    python mqtt_latency_test.py --mode mqtt1883 --username huber --password "PASSWORD" --count 4000 --interval 0.05
    python mqtt_latency_test.py --mode all --username huber --password "PASSWORD" --count 1000 --interval 0.05

Modes:
    mqtt1883  -> mqtt://mqtt.mecatronica-ibero.mx:1883
    mqtts8883 -> mqtts://mqtt.mecatronica-ibero.mx:8883
    ws9001    -> ws://mqtt.mecatronica-ibero.mx:9001/
    wss443    -> wss://mqtt.mecatronica-ibero.mx/
"""

import argparse
import json
import ssl
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt
import paho.mqtt.client as mqtt


BROKER_DEFAULT = "mqtt.mecatronica-ibero.mx"


@dataclass
class ModeConfig:
    name: str
    label: str
    port: int
    transport: str
    tls: bool
    ws_path: Optional[str] = None


MODES: Dict[str, ModeConfig] = {
    "mqtt1883": ModeConfig(
        name="mqtt1883",
        label="MQTT 1883 sin TLS",
        port=1883,
        transport="tcp",
        tls=False,
        ws_path=None,
    ),
    "mqtts8883": ModeConfig(
        name="mqtts8883",
        label="MQTT 8883 con TLS",
        port=8883,
        transport="tcp",
        tls=True,
        ws_path=None,
    ),
    "ws9001": ModeConfig(
        name="ws9001",
        label="WebSocket 9001 sin TLS",
        port=9001,
        transport="websockets",
        tls=False,
        ws_path="/",
    ),
    "wss443": ModeConfig(
        name="wss443",
        label="WebSocket 443 con TLS",
        port=443,
        transport="websockets",
        tls=True,
        ws_path="/",
    ),
}


def create_client(client_id: str, transport: str) -> mqtt.Client:
    """
    Creates a Paho client compatible with paho-mqtt 1.x and 2.x.
    """
    try:
        return mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            protocol=mqtt.MQTTv311,
            transport=transport,
        )
    except Exception:
        return mqtt.Client(
            client_id=client_id,
            protocol=mqtt.MQTTv311,
            transport=transport,
        )


def run_latency_test(
    broker: str,
    mode: ModeConfig,
    username: str,
    password: str,
    count: int,
    interval: float,
    qos: int,
    base_topic: str,
    timeout_after_publish: float,
    out_dir: Path,
    y_limit: Optional[float],
    show_plot: bool,
) -> Dict[str, object]:

    run_id = uuid.uuid4().hex[:8]
    client_id = f"latency-{mode.name}-{run_id}"
    topic = f"{base_topic}/{mode.name}/{run_id}"

    connected = False
    received_rows: List[Dict[str, object]] = []
    sent_times: Dict[int, int] = {}

    client = create_client(client_id, mode.transport)
    client.username_pw_set(username, password)

    if mode.transport == "websockets" and mode.ws_path:
        client.ws_set_options(path=mode.ws_path)

    if mode.tls:
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED)
        client.tls_insecure_set(False)

    def on_connect(client, userdata, flags, rc, *extra):
        nonlocal connected
        try:
            rc_value = int(rc)
        except Exception:
            rc_value = getattr(rc, "value", rc)

        if rc_value == 0:
            connected = True
            print(f"[{mode.name}] Connected to {broker}:{mode.port}")
            client.subscribe(topic, qos=qos)
        else:
            print(f"[{mode.name}] Connection failed. rc={rc}")

    def on_message(client, userdata, msg):
        now_ns = time.perf_counter_ns()

        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            seq = int(payload["seq"])
            t_pub_ns = int(payload["t_pub_ns"])
            latency_s = (now_ns - t_pub_ns) / 1_000_000_000
            sent_ns = sent_times.get(seq)

            received_rows.append(
                {
                    "mode": mode.name,
                    "label": mode.label,
                    "broker": broker,
                    "port": mode.port,
                    "transport": mode.transport,
                    "tls": mode.tls,
                    "topic": msg.topic,
                    "seq": seq,
                    "t_pub_ns": t_pub_ns,
                    "t_recv_ns": now_ns,
                    "latency_s": latency_s,
                    "qos": qos,
                    "client_id": client_id,
                    "sent_known": sent_ns is not None,
                }
            )
        except Exception as exc:
            print(f"[{mode.name}] Invalid message: {exc}")

    client.on_connect = on_connect
    client.on_message = on_message

    print("\n" + "=" * 72)
    print(f"Mode: {mode.label}")
    print(f"Endpoint: {broker}:{mode.port}")
    print(f"Transport: {mode.transport} | TLS: {mode.tls} | Topic: {topic}")
    print("=" * 72)

    client.connect(broker, mode.port, keepalive=60)
    client.loop_start()

    t0 = time.time()
    while not connected:
        if time.time() - t0 > 10:
            client.loop_stop()
            client.disconnect()
            raise TimeoutError(f"[{mode.name}] Connection timeout")
        time.sleep(0.05)

    time.sleep(0.5)

    print(f"[{mode.name}] Publishing {count} messages, interval={interval}s, qos={qos}")

    for seq in range(count):
        t_pub_ns = time.perf_counter_ns()
        sent_times[seq] = t_pub_ns

        payload = {
            "seq": seq,
            "t_pub_ns": t_pub_ns,
            "mode": mode.name,
            "client_id": client_id,
        }

        result = client.publish(topic, json.dumps(payload), qos=qos, retain=False)

        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"[{mode.name}] Publish error at seq={seq}, rc={result.rc}")

        if interval > 0:
            time.sleep(interval)

        if seq > 0 and seq % 500 == 0:
            print(f"[{mode.name}] Sent {seq}/{count} | received {len(received_rows)}")

    print(f"[{mode.name}] Waiting for remaining messages...")
    wait_start = time.time()
    while len(received_rows) < count and (time.time() - wait_start) < timeout_after_publish:
        time.sleep(0.05)

    client.loop_stop()
    client.disconnect()

    df = pd.DataFrame(received_rows)
    if df.empty:
        raise RuntimeError(f"[{mode.name}] No messages received")

    df = df.sort_values("seq").reset_index(drop=True)
    missing = count - len(df)
    mean = df["latency_s"].mean()
    std = df["latency_s"].std()
    median = df["latency_s"].median()
    p95 = df["latency_s"].quantile(0.95)
    p99 = df["latency_s"].quantile(0.99)
    min_v = df["latency_s"].min()
    max_v = df["latency_s"].max()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_label = mode.name
    csv_path = out_dir / f"mqtt_latency_{safe_label}_{timestamp}.csv"
    png_path = out_dir / f"mqtt_latency_{safe_label}_{timestamp}.png"

    df.to_csv(csv_path, index=False)

    fig = plt.figure(figsize=(12, 8))
    ax = plt.gca()

    ax.plot(df["seq"], df["latency_s"], color="blue", linewidth=1.1, label="Latency (s)")
    ax.axhline(mean, color="green", linestyle="--", linewidth=1.3, label=f"Mean = {mean:.4f} s")

    if pd.notna(std):
        ax.axhline(mean + std, color="red", linestyle="--", linewidth=1.2, label=f"+1 Std Dev = {mean + std:.4f} s")
        ax.axhline(max(mean - std, 0), color="red", linestyle="--", linewidth=1.2, label=f"−1 Std Dev = {max(mean - std, 0):.4f} s")

    ax.set_title(f"MQTT Message Latency\n{mode.label}", fontsize=20, fontstyle="italic")
    ax.set_xlabel("Message Index", fontsize=14, fontstyle="italic")
    ax.set_ylabel("Δt (s)", fontsize=14, fontstyle="italic")
    ax.grid(True)
    ax.legend(fontsize=12)

    if y_limit is not None:
        ax.set_ylim(0, y_limit)
    else:
        upper = max(0.1, min(max_v * 1.15, max(max_v, mean + 4 * std if pd.notna(std) else max_v)))
        ax.set_ylim(0, upper)

    fig.text(
        0.5,
        0.02,
        f"{mode.label} · received={len(df)}/{count} · mean={mean:.4f}s · median={median:.4f}s · p95={p95:.4f}s · p99={p99:.4f}s",
        ha="center",
        fontsize=12,
        family="monospace",
    )

    plt.tight_layout(rect=[0, 0.06, 1, 1])
    plt.savefig(png_path, dpi=200)

    if show_plot:
        plt.show()
    else:
        plt.close(fig)

    print(f"\n[{mode.name}] Results")
    print(f"  Received: {len(df)}/{count}")
    print(f"  Missing:  {missing}")
    print(f"  Mean:     {mean:.6f} s")
    print(f"  Std:      {std:.6f} s")
    print(f"  Median:   {median:.6f} s")
    print(f"  P95:      {p95:.6f} s")
    print(f"  P99:      {p99:.6f} s")
    print(f"  Min:      {min_v:.6f} s")
    print(f"  Max:      {max_v:.6f} s")
    print(f"  CSV:      {csv_path}")
    print(f"  PNG:      {png_path}")

    return {
        "mode": mode.name,
        "label": mode.label,
        "broker": broker,
        "port": mode.port,
        "transport": mode.transport,
        "tls": mode.tls,
        "count_requested": count,
        "count_received": len(df),
        "count_missing": missing,
        "qos": qos,
        "interval_s": interval,
        "mean_s": mean,
        "std_s": std,
        "median_s": median,
        "p95_s": p95,
        "p99_s": p99,
        "min_s": min_v,
        "max_s": max_v,
        "csv_path": str(csv_path),
        "png_path": str(png_path),
    }


def main():
    parser = argparse.ArgumentParser(description="MQTT latency benchmark")
    parser.add_argument("--broker", default=BROKER_DEFAULT, help="Broker host")
    parser.add_argument("--mode", default="wss443", choices=["mqtt1883", "mqtts8883", "ws9001", "wss443", "all"])
    parser.add_argument("--username", required=True, help="MQTT username")
    parser.add_argument("--password", required=True, help="MQTT password")
    parser.add_argument("--count", type=int, default=4000, help="Number of messages")
    parser.add_argument("--interval", type=float, default=0.05, help="Seconds between publishes")
    parser.add_argument("--qos", type=int, default=0, choices=[0, 1, 2], help="MQTT QoS")
    parser.add_argument("--base-topic", default="huber/latency", help="Base topic")
    parser.add_argument("--timeout-after-publish", type=float, default=15.0, help="Seconds to wait after publishing")
    parser.add_argument("--out-dir", default="mqtt_latency_results", help="Output directory")
    parser.add_argument("--y-limit", type=float, default=None, help="Optional y-axis limit in seconds")
    parser.add_argument("--show-plot", action="store_true", help="Show plot window")

    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected_modes = list(MODES.values()) if args.mode == "all" else [MODES[args.mode]]

    summaries = []
    for mode in selected_modes:
        try:
            summary = run_latency_test(
                broker=args.broker,
                mode=mode,
                username=args.username,
                password=args.password,
                count=args.count,
                interval=args.interval,
                qos=args.qos,
                base_topic=args.base_topic,
                timeout_after_publish=args.timeout_after_publish,
                out_dir=out_dir,
                y_limit=args.y_limit,
                show_plot=args.show_plot,
            )
            summaries.append(summary)
        except Exception as exc:
            print(f"\nERROR in mode {mode.name}: {exc}")
            summaries.append(
                {
                    "mode": mode.name,
                    "label": mode.label,
                    "broker": args.broker,
                    "port": mode.port,
                    "transport": mode.transport,
                    "tls": mode.tls,
                    "error": str(exc),
                }
            )

    summary_df = pd.DataFrame(summaries)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    summary_path = out_dir / f"mqtt_latency_summary_{timestamp}.csv"
    summary_df.to_csv(summary_path, index=False)

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(summary_df.to_string(index=False))
    print(f"\nSummary CSV: {summary_path}")


if __name__ == "__main__":
    main()
