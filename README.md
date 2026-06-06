# Broker MQTT institucional — `mqtt.mecatronica-ibero.mx`

Documento de referencia para el broker MQTT montado en el droplet de DigitalOcean y expuesto mediante el subdominio:

```text
mqtt.mecatronica-ibero.mx
```

El broker está pensado para proyectos de automatización, robótica móvil, sistemas ciberfísicos, interfaces web, backends en línea, agentes LLM y pruebas de comunicación con ESP32, Python, JavaScript y otros clientes MQTT.

---

## 1. Arquitectura general

La arquitectura recomendada usa **Mosquitto** como broker MQTT y **Nginx** como proxy seguro para WebSocket sobre HTTPS.

```text
Clientes MQTT / Web / Robots / Backends
        │
        ├── MQTT sin TLS         → mqtt://mqtt.mecatronica-ibero.mx:1883
        ├── MQTT con TLS         → mqtts://mqtt.mecatronica-ibero.mx:8883
        ├── WebSocket sin TLS    → ws://mqtt.mecatronica-ibero.mx:9001/
        └── WebSocket con TLS    → wss://mqtt.mecatronica-ibero.mx/
                                      │
                                      ▼
                                  Nginx :443
                                      │
                                      ▼
                              Mosquitto :9001
```

La ruta principal recomendada para aplicaciones web modernas es:

```text
wss://mqtt.mecatronica-ibero.mx/
```

---

## 2. Puertos habilitados

| Puerto | Protocolo | URL equivalente | Uso recomendado |
|---:|---|---|---|
| 1883 | MQTT sin TLS | `mqtt://mqtt.mecatronica-ibero.mx:1883` | Aplicaciones antiguas, pruebas rápidas, clientes embebidos simples |
| 8883 | MQTT con TLS | `mqtts://mqtt.mecatronica-ibero.mx:8883` | Python, backends, robots y clientes MQTT seguros |
| 9001 | WebSocket sin TLS | `ws://mqtt.mecatronica-ibero.mx:9001/` | Pruebas directas WebSocket sin Nginx |
| 443 | WebSocket con TLS | `wss://mqtt.mecatronica-ibero.mx/` | Navegador, JavaScript, dashboards, backends modernos |

---

## 3. Recomendación de uso

Para proyectos nuevos se recomienda usar:

```text
wss://mqtt.mecatronica-ibero.mx/
```

o, en clientes MQTT nativos:

```text
mqtts://mqtt.mecatronica-ibero.mx:8883
```

El puerto `1883` debe conservarse únicamente por compatibilidad con aplicaciones existentes que todavía no usan TLS.

---

## 4. Configuración de Mosquitto

Archivo sugerido:

```bash
/etc/mosquitto/conf.d/mecatronica.conf
```

Contenido:

```conf
allow_anonymous false
password_file /etc/mosquitto/passwd

# MQTT sin TLS
listener 1883 0.0.0.0
protocol mqtt

# WebSocket sin TLS
listener 9001 0.0.0.0
protocol websockets

# MQTT con TLS
listener 8883 0.0.0.0
protocol mqtt
certfile /etc/mosquitto/certs/fullchain.pem
keyfile /etc/mosquitto/certs/privkey.pem
```

Después de editar:

```bash
sudo systemctl reset-failed mosquitto
sudo systemctl restart mosquitto
sudo systemctl status mosquitto --no-pager -l
```

Verificación de puertos:

```bash
sudo ss -tulpn | grep mosquitto
```

---

## 5. Certificados TLS para Mosquitto

Si el certificado de Certbot ya existe en:

```bash
/etc/letsencrypt/live/mqtt.mecatronica-ibero.mx/
```

copiarlo a una carpeta legible por Mosquitto:

```bash
sudo mkdir -p /etc/mosquitto/certs

sudo cp /etc/letsencrypt/live/mqtt.mecatronica-ibero.mx/fullchain.pem /etc/mosquitto/certs/fullchain.pem
sudo cp /etc/letsencrypt/live/mqtt.mecatronica-ibero.mx/privkey.pem /etc/mosquitto/certs/privkey.pem

sudo chown root:mosquitto /etc/mosquitto/certs/fullchain.pem
sudo chown root:mosquitto /etc/mosquitto/certs/privkey.pem

sudo chmod 644 /etc/mosquitto/certs/fullchain.pem
sudo chmod 640 /etc/mosquitto/certs/privkey.pem
```

---

## 6. Configuración de Nginx para WSS en 443

Archivo sugerido:

```bash
/etc/nginx/sites-available/mqtt.mecatronica-ibero.mx
```

Configuración básica:

```nginx
server {
    listen 80;
    server_name mqtt.mecatronica-ibero.mx;

    location / {
        proxy_pass http://127.0.0.1:9001;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;

        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

Activar sitio:

```bash
sudo ln -s /etc/nginx/sites-available/mqtt.mecatronica-ibero.mx /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Certificado HTTPS:

```bash
sudo certbot --nginx -d mqtt.mecatronica-ibero.mx
```

---

## 7. Firewall

Con `ufw`:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw allow 1883/tcp
sudo ufw allow 8883/tcp
sudo ufw allow 9001/tcp
sudo ufw status
```

En el firewall de DigitalOcean también deben estar habilitados:

```text
22/tcp    SSH
80/tcp    HTTP
443/tcp   HTTPS / WSS
1883/tcp  MQTT sin TLS
8883/tcp  MQTT TLS
9001/tcp  WebSocket sin TLS
```

---

## 8. Pruebas con MQTT Explorer

### 8.1 WSS por puerto 443

Equivalente a:

```text
wss://mqtt.mecatronica-ibero.mx/
```

Configuración en MQTT Explorer:

```text
Protocol: ws://
Host: mqtt.mecatronica-ibero.mx
Port: 443
Basepath: /
Username: huber
Password: ********
Encryption (tls): ON
Validate certificate: ON
```

### 8.2 MQTT sin TLS por puerto 1883

Equivalente a:

```text
mqtt://mqtt.mecatronica-ibero.mx:1883
```

```text
Protocol: mqtt://
Host: mqtt.mecatronica-ibero.mx
Port: 1883
Username: huber
Password: ********
Encryption (tls): OFF
Validate certificate: OFF
```

### 8.3 MQTT con TLS por puerto 8883

Equivalente a:

```text
mqtts://mqtt.mecatronica-ibero.mx:8883
```

```text
Protocol: mqtt://
Host: mqtt.mecatronica-ibero.mx
Port: 8883
Username: huber
Password: ********
Encryption (tls): ON
Validate certificate: ON
```

### 8.4 WebSocket sin TLS por puerto 9001

Equivalente a:

```text
ws://mqtt.mecatronica-ibero.mx:9001/
```

```text
Protocol: ws://
Host: mqtt.mecatronica-ibero.mx
Port: 9001
Basepath: /
Username: huber
Password: ********
Encryption (tls): OFF
Validate certificate: OFF
```

---

## 9. Pruebas desde terminal

### Suscripción por MQTT 1883

```bash
mosquitto_sub \
  -h mqtt.mecatronica-ibero.mx \
  -p 1883 \
  -t "huber/test" \
  -u huber \
  -P "TU_PASSWORD"
```

### Publicación por MQTT 1883

```bash
mosquitto_pub \
  -h mqtt.mecatronica-ibero.mx \
  -p 1883 \
  -t "huber/test" \
  -m "hola por 1883" \
  -u huber \
  -P "TU_PASSWORD"
```

### Suscripción por MQTT TLS 8883

```bash
mosquitto_sub \
  -h mqtt.mecatronica-ibero.mx \
  -p 8883 \
  -t "huber/test" \
  -u huber \
  -P "TU_PASSWORD" \
  --cafile /etc/ssl/certs/ca-certificates.crt
```

### Publicación por MQTT TLS 8883

```bash
mosquitto_pub \
  -h mqtt.mecatronica-ibero.mx \
  -p 8883 \
  -t "huber/test" \
  -m "hola por 8883 TLS" \
  -u huber \
  -P "TU_PASSWORD" \
  --cafile /etc/ssl/certs/ca-certificates.crt
```

---

## 10. Prueba desde JavaScript en navegador

```html
<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>

<script>
const client = mqtt.connect("wss://mqtt.mecatronica-ibero.mx/", {
  username: "huber",
  password: "TU_PASSWORD",
  clientId: "browser-" + Math.random().toString(16).substring(2)
});

client.on("connect", () => {
  console.log("Conectado por WSS 443");
  client.subscribe("huber/test");
  client.publish("huber/test", "Hola desde navegador por WSS");
});

client.on("message", (topic, message) => {
  console.log(topic, message.toString());
});

client.on("error", (err) => {
  console.error("Error MQTT:", err.message);
});
</script>
```

---

## 11. Prueba desde Python por MQTT sin TLS

```python
import paho.mqtt.client as mqtt

BROKER = "mqtt.mecatronica-ibero.mx"
PORT = 1883
USERNAME = "huber"
PASSWORD = "TU_PASSWORD"
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
```

---

## 12. Prueba desde Python por MQTT TLS

```python
import ssl
import paho.mqtt.client as mqtt

BROKER = "mqtt.mecatronica-ibero.mx"
PORT = 8883
USERNAME = "huber"
PASSWORD = "TU_PASSWORD"
TOPIC = "huber/test"

def on_connect(client, userdata, flags, rc):
    print("Conectado:", rc)
    client.subscribe(TOPIC)
    client.publish(TOPIC, "Hola desde Python por 8883 TLS")

def on_message(client, userdata, msg):
    print(msg.topic, "->", msg.payload.decode())

client = mqtt.Client(client_id="python-8883-test")
client.username_pw_set(USERNAME, PASSWORD)
client.tls_set(cert_reqs=ssl.CERT_REQUIRED)

client.on_connect = on_connect
client.on_message = on_message

client.connect(BROKER, PORT, 60)
client.loop_forever()
```

---

## 13. Tópicos sugeridos para proyectos

Para pruebas generales:

```text
huber/test
```

Para robots:

```text
huber/R1/cmd
huber/R1/status
huber/R1/telemetry

huber/R2/cmd
huber/R2/status
huber/R2/telemetry
```

Para arquitectura LLM → Planner → Robot:

```text
huber/robot/plan/cmd
huber/robot/goal
huber/robot/plan/status
```

Flujo sugerido:

```text
Frontend web
    │ publica comandos
    ▼
huber/robot/plan/cmd
    │
    ▼
Planner Python
    │ publica poses deseadas
    ▼
huber/robot/goal
    │
    ▼
Robot digital / robot físico
```

---

## 14. Usuarios y seguridad

Para pruebas se puede usar un usuario único, por ejemplo:

```text
huber
```

Para producción se recomienda crear usuarios separados:

```bash
sudo mosquitto_passwd /etc/mosquitto/passwd frontend
sudo mosquitto_passwd /etc/mosquitto/passwd planner
sudo mosquitto_passwd /etc/mosquitto/passwd robot1
sudo mosquitto_passwd /etc/mosquitto/passwd robot2

sudo systemctl restart mosquitto
```

Recomendaciones:

- No publicar contraseñas en repositorios públicos.
- No usar `allow_anonymous true` en un broker público.
- Preferir `wss://` o `mqtts://` para proyectos nuevos.
- Mantener `1883` solo para compatibilidad.
- Separar tópicos por proyecto, robot, grupo o curso.

---

## 15. Publicar una página informativa del broker

Como el endpoint principal usa la raíz:

```text
wss://mqtt.mecatronica-ibero.mx/
```

hay dos formas prácticas de publicar una página informativa.

### Opción A — Conservar WSS en `/` y poner la página en `/info`

Esta opción mantiene el endpoint limpio:

```text
wss://mqtt.mecatronica-ibero.mx/
```

y publica la documentación en:

```text
https://mqtt.mecatronica-ibero.mx/info
```

Ejemplo Nginx:

```nginx
server {
    listen 80;
    server_name mqtt.mecatronica-ibero.mx;

    location = /info {
        root /var/www/mqtt;
        try_files /index.html =404;
    }

    location / {
        proxy_pass http://127.0.0.1:9001;
        proxy_http_version 1.1;

        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;

        proxy_read_timeout 86400;
        proxy_send_timeout 86400;
    }
}
```

Crear carpeta pública:

```bash
sudo mkdir -p /var/www/mqtt
sudo nano /var/www/mqtt/index.html
```

### Opción B — Usar `/` como página pública y mover MQTT WebSocket a `/mqtt`

Esta opción permite:

```text
https://mqtt.mecatronica-ibero.mx/
```

como página pública, pero cambia el endpoint WebSocket a:

```text
wss://mqtt.mecatronica-ibero.mx/mqtt
```

Es más explícito, pero menos limpio que usar la raíz.

---

## 16. Página HTML pública sugerida

El siguiente contenido puede guardarse como:

```bash
/var/www/mqtt/index.html
```

No incluir contraseñas reales en esta página.

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Broker MQTT | Mecatrónica Ibero</title>
  <style>
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      margin: 0;
      background: #f5f7fa;
      color: #1f2933;
      line-height: 1.6;
    }

    header {
      background: #002855;
      color: white;
      padding: 48px 24px;
      text-align: center;
    }

    main {
      max-width: 980px;
      margin: 0 auto;
      padding: 32px 24px;
    }

    section {
      background: white;
      margin-bottom: 24px;
      padding: 24px;
      border-radius: 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.06);
    }

    h1, h2 {
      margin-top: 0;
    }

    code, pre {
      background: #eef2f7;
      padding: 2px 6px;
      border-radius: 6px;
    }

    pre {
      overflow-x: auto;
      padding: 16px;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      overflow-x: auto;
    }

    th, td {
      border-bottom: 1px solid #e5e7eb;
      padding: 12px;
      text-align: left;
    }

    th {
      background: #f3f4f6;
    }

    .badge {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: #e0f2fe;
      color: #075985;
      font-size: 0.9rem;
      font-weight: 600;
    }

    footer {
      text-align: center;
      padding: 24px;
      color: #6b7280;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>
  <header>
    <p class="badge">Broker MQTT</p>
    <h1>mqtt.mecatronica-ibero.mx</h1>
    <p>Servicio MQTT para proyectos de robótica, automatización, IoT, sistemas ciberfísicos e interfaces inteligentes.</p>
  </header>

  <main>
    <section>
      <h2>Endpoint recomendado</h2>
      <p>Para aplicaciones web, dashboards y clientes JavaScript se recomienda usar:</p>
      <pre>wss://mqtt.mecatronica-ibero.mx/</pre>
    </section>

    <section>
      <h2>Puertos disponibles</h2>
      <table>
        <thead>
          <tr>
            <th>Puerto</th>
            <th>Protocolo</th>
            <th>Endpoint</th>
            <th>Uso sugerido</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>1883</td>
            <td>MQTT</td>
            <td><code>mqtt://mqtt.mecatronica-ibero.mx:1883</code></td>
            <td>Aplicaciones existentes sin TLS</td>
          </tr>
          <tr>
            <td>8883</td>
            <td>MQTT TLS</td>
            <td><code>mqtts://mqtt.mecatronica-ibero.mx:8883</code></td>
            <td>Clientes MQTT seguros</td>
          </tr>
          <tr>
            <td>9001</td>
            <td>WebSocket</td>
            <td><code>ws://mqtt.mecatronica-ibero.mx:9001/</code></td>
            <td>Pruebas directas WebSocket</td>
          </tr>
          <tr>
            <td>443</td>
            <td>WebSocket TLS</td>
            <td><code>wss://mqtt.mecatronica-ibero.mx/</code></td>
            <td>Navegador, JS y dashboards</td>
          </tr>
        </tbody>
      </table>
    </section>

    <section>
      <h2>Ejemplo JavaScript</h2>
      <pre>&lt;script src="https://unpkg.com/mqtt/dist/mqtt.min.js"&gt;&lt;/script&gt;

&lt;script&gt;
const client = mqtt.connect("wss://mqtt.mecatronica-ibero.mx/", {
  username: "USUARIO",
  password: "PASSWORD",
  clientId: "browser-" + Math.random().toString(16).substring(2)
});

client.on("connect", () =&gt; {
  console.log("Conectado por WSS");
  client.subscribe("huber/test");
  client.publish("huber/test", "Hola desde navegador");
});

client.on("message", (topic, message) =&gt; {
  console.log(topic, message.toString());
});
&lt;/script&gt;</pre>
    </section>

    <section>
      <h2>Notas de seguridad</h2>
      <ul>
        <li>El broker requiere usuario y contraseña.</li>
        <li>No se recomienda publicar contraseñas en repositorios públicos.</li>
        <li>Para proyectos nuevos se recomienda usar <code>wss://</code> o <code>mqtts://</code>.</li>
        <li>El puerto <code>1883</code> se conserva principalmente por compatibilidad.</li>
      </ul>
    </section>
  </main>

  <footer>
    Mecatrónica Ibero · Broker MQTT para proyectos académicos y de prototipado
  </footer>
</body>
</html>
```
