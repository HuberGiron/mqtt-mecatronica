import ssl
import time
import paho.mqtt.client as mqtt

BROKER = "mqtt.mecatronica-ibero.mx"
PORT = 443
USERNAME = "huber"
PASSWORD = "1234"
TOPIC = "huber/test"

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Conectado con código:", reason_code)
    client.subscribe(TOPIC)
    client.publish(TOPIC, "Hola desde Python local")

def on_message(client, userdata, msg):
    print(f"{msg.topic} -> {msg.payload.decode()}")

client = mqtt.Client(
    client_id="python-local-test",
    transport="websockets"
)

client.username_pw_set(USERNAME, PASSWORD)

# Importante: como tu endpoint es wss://mqtt.mecatronica-ibero.mx/
client.ws_set_options(path="/")

# TLS para WSS en puerto 443
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, keepalive=60)

client.loop_start()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Desconectando...")
    client.loop_stop()
    client.disconnect()