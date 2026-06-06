const mqtt = require("mqtt");

const client = mqtt.connect("wss://mqtt.mecatronica-ibero.mx/", {
  clientId: "node-backend-test-" + Math.random().toString(16).substring(2),
  username: "huber",
  password: "1234",
  reconnectPeriod: 2000,
  connectTimeout: 8000
});

client.on("connect", () => {
  console.log("Conectado desde Node.js backend");

  client.subscribe("huber/test", (err) => {
    if (err) {
      console.error("Error al suscribirse:", err);
      return;
    }

    console.log("Suscrito a huber/test");
    client.publish("huber/test", "Hola desde Node.js backend");
  });
});

client.on("message", (topic, message) => {
  console.log(`${topic} -> ${message.toString()}`);
});

client.on("error", (err) => {
  console.error("Error MQTT:", err.message);
});