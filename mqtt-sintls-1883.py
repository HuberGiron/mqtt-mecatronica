import paho.mqtt.client as mqtt

BROKER = "mqtt.mecatronica-ibero.mx"
PORT = 1883
USERNAME = "huber"
PASSWORD = "1234"
TOPIC = "huber/test"

def on_connect(client, userdata, flags, rc):
    print("Conectado:", rc)
    client.subscribe(TOPIC)
    client.publish(TOPIC, "Hola desde Python por 1883")

def on_message(client, userdata, msg):
    print(msg.topic, "->", msg.payload.decode())

client = mqtt.Client(client_id="python-1883-test")
client.username_pw_set(USERNAME, PASSWORD)

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()