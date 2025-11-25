from flask import Flask, render_template_string, request, jsonify
import random
import time  # Para timestamps
import textwrap  # Para limpiar indentación en HTML

app = Flask(__name__)

# Variables para alertas del ESP32 (se actualizan con POST)
alerts = []  # Lista de alertas recientes
armed = True
intrusion = False
solar_volt = round(random.uniform(3.5, 5.0), 2)
auto_volt = round(random.uniform(11.5, 14.5), 2)
last_update = time.strftime("%H:%M:%S")

# HTML inline (degradados azules-morados, dashboard con alertas) – limpio con dedent
HTML_TEMPLATE = textwrap.dedent('''\
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { font-family: Arial; background: linear-gradient(to bottom, #1e3c72, #2a1b3d); color: white; text-align: center; padding: 20px; margin: 0; }
h1 { color: #a8e6cf; text-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
.status { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 15px; margin: 10px auto; max-width: 300px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }
.alerts { background: rgba(255,0,0,0.2); padding: 15px; border-radius: 15px; margin: 20px auto; max-width: 300px; }
button { background: linear-gradient(#667eea, #764ba2); color: white; border: none; padding: 15px; font-size: 18px; margin: 10px; border-radius: 10px; width: 80%; cursor: pointer; }
.arm { background: linear-gradient(#4CAF50, #45a049); }
.disarm { background: linear-gradient(#f44336, #da190b); }
.silence { background: linear-gradient(#ff9800, #e68900); }
.simulate { background: linear-gradient(#ff5722, #d84315); }
.track { background: rgba(255,255,255,0.1); padding: 15px; border-radius: 15px; margin: 20px auto; max-width: 300px; }
#map { height: 200px; border-radius: 10px; margin-top: 10px; }
</style>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
</head><body>
<h1>🌿 FloraLock - Dashboard Central</h1>
<div class="status">Voltaje Solar: {{ solar_volt }} V</div>
<div class="status">Voltaje Auto: {{ auto_volt }} V</div>
<div class="status">Modo: {{ "ARMADO 🔒" if armed else "DESARMADO 🔓" }}</div>
<div class="status">Última Update: {{ last_update }}</div>
{% if intrusion %}<div class="status" style="background: rgba(255,0,0,0.3);">¡INTRUSIÓN ACTIVA! ⚠️</div>{% endif %}
<button class="arm" onclick="arm()">ARMAR</button>
<button class="disarm" onclick="disarm()">DESARMAR</button>
<button class="silence" onclick="silence()">SILENCIAR ALARMA</button>
<button class="simulate" onclick="simulate()">SIMULAR ALERTA ESP32</button>
<div class="track"><h3 style="color: #a8e6cf;">Rastreo</h3><div id="map"></div><p>Lat/Long: 19.4326, -99.1332</p></div>
<div class="alerts"><h3 style="color: #a8e6cf;">Alertas Recientes</h3>
{% for alert in alerts[-3:] %}
<p>{{ alert.time }}: {{ alert.type }} (Volt: {{ alert.volt }}V)</p>
{% endfor %}
{% if not alerts %}<p>No hay alertas aún.</p>{% endif %}</div>
<script>
function arm() { fetch('/arm', {method: 'POST'}).then(() => location.reload()); }
function disarm() { fetch('/disarm', {method: 'POST'}).then(() => location.reload()); }
function silence() { fetch('/silence', {method: 'POST'}).then(() => location.reload()); }
function simulate() { fetch('/alert', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({intrusion: true, volt: Math.random()*5, message: 'Simulada desde app'})}).then(() => location.reload()); }
var map = L.map('map').setView([19.4326, -99.1332], 13);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(map);
L.marker([19.4326, -99.1332]).addTo(map).bindPopup('Auto');
setInterval(() => location.reload(), 5000);
</script>
</body></html>
''')

@app.route('/')
def index():
    global armed, intrusion, solar_volt, auto_volt, last_update
    solar_volt = round(random.uniform(3.5, 5.0), 2)
    auto_volt = round(random.uniform(11.5, 14.5), 2)
    last_update = time.strftime("%H:%M:%S")
    return render_template_string(HTML_TEMPLATE, armed=armed, intrusion=intrusion, solar_volt=solar_volt, auto_volt=auto_volt, alerts=alerts, last_update=last_update)

@app.route('/arm', methods=['POST'])
def arm():
    global armed
    armed = True
    return jsonify({"status": "Armado"})

@app.route('/disarm', methods=['POST'])
def disarm():
    global armed
    armed = False
    return jsonify({"status": "Desarmado"})

@app.route('/silence', methods=['POST'])
def silence():
    global intrusion
    intrusion = False
    return jsonify({"status": "Silenciada"})

@app.route('/alert', methods=['POST'])
def receive_alert():
    global intrusion, alerts
    data = request.json
    intrusion = data.get('intrusion', False)
    volt = data.get('volt', 0)
    message = data.get('message', 'Alerta genérica')
    alerts.append({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "type": message, "volt": volt})
    if len(alerts) > 10:
        alerts = alerts[-10:]  # Últimas 10
    print(f"Alerta del ESP32: {message} - Volt: {volt}")
    return jsonify({"status": "Alerta recibida"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)