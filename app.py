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

# HTML inline para dashboard (tonos pasteles: rosas, blancos, azul pastel; botones más chicos y responsive con flexbox; iconos Font Awesome)
DASHBOARD_TEMPLATE = textwrap.dedent('''\
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
body { font-family: Arial, sans-serif; background: linear-gradient(to bottom, #ffeef8, #e8f4fd); color: #333; text-align: center; padding: 20px; margin: 0; }
h1 { color: #ff69b4; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); margin-bottom: 20px; }
.status { background: rgba(255,255,255,0.8); padding: 12px; border-radius: 12px; margin: 8px auto; max-width: 300px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
.alerts { background: rgba(255, 182, 193, 0.3); padding: 12px; border-radius: 12px; margin: 15px auto; max-width: 300px; }
.buttons { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin: 20px 0; }
button { background: linear-gradient(#ff9a9e, #fecfef); color: #333; border: none; padding: 8px 16px; font-size: 14px; border-radius: 8px; cursor: pointer; min-width: 120px; transition: transform 0.2s; }
button:hover { transform: scale(1.05); }
.arm { background: linear-gradient(#a8edea, #fed6e3); }
.disarm { background: linear-gradient(#ffecd2, #fcb69f); }
.silence { background: linear-gradient(#ffd89b, #19547b); color: white; }
.simulate { background: linear-gradient(#ff9a9e, #fecfef); }
.history { background: linear-gradient(#a8e6cf, #dcedc1); }
.track { background: rgba(255,255,255,0.8); padding: 12px; border-radius: 12px; margin: 15px auto; max-width: 300px; }
#map { height: 200px; border-radius: 8px; margin-top: 10px; }
@media (max-width: 600px) { .buttons { flex-direction: column; align-items: center; } button { width: 80%; } }
</style>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
</head><body>
<h1><i class="fas fa-seedling"></i> FloraLock - Dashboard Central</h1>
<div class="status">Voltaje Solar: {{ solar_volt }} V <i class="fas fa-solar-panel"></i></div>
<div class="status">Voltaje Auto: {{ auto_volt }} V <i class="fas fa-car-battery"></i></div>
<div class="status">Modo: {{ "ARMADO" if armed else "DESARMADO" }} <i class="fas fa-{{ 'lock' if armed else 'unlock' }}"></i></div>
<div class="status">Última Update: {{ last_update }} <i class="fas fa-clock"></i></div>
{% if intrusion %}<div class="status" style="background: rgba(255, 182, 193, 0.5);">¡INTRUSIÓN ACTIVA! <i class="fas fa-exclamation-triangle"></i></div>{% endif %}
<div class="buttons">
<button class="arm" onclick="arm()"><i class="fas fa-shield-alt"></i> ARMAR</button>
<button class="disarm" onclick="disarm()"><i class="fas fa-unlock"></i> DESARMAR</button>
<button class="silence" onclick="silence()"><i class="fas fa-volume-mute"></i> SILENCIAR</button>
<button class="simulate" onclick="simulate()"><i class="fas fa-play"></i> SIMULAR</button>
<button class="history" onclick="window.location.href='/history'"><i class="fas fa-history"></i> HISTORIAL</button>
</div>
<div class="track"><h3 style="color: #ff69b4;">Rastreo</h3><div id="map"></div><p>Lat/Long: 19.4326, -99.1332 <i class="fas fa-map-marker-alt"></i></p></div>
<div class="alerts"><h3 style="color: #ff69b4;">Alertas Recientes</h3>
{% for alert in alerts[-3:] %}
<p><i class="fas fa-bell"></i> {{ alert.time }}: {{ alert.type }} (Volt: {{ alert.volt }}V)</p>
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

# HTML inline para página de historial (mismo estilo pastel, lista completa de alertas en tabla)
HISTORY_TEMPLATE = textwrap.dedent('''\
<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
body { font-family: Arial, sans-serif; background: linear-gradient(to bottom, #ffeef8, #e8f4fd); color: #333; text-align: center; padding: 20px; margin: 0; }
h1 { color: #ff69b4; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); margin-bottom: 20px; }
.back { background: linear-gradient(#a8e6cf, #dcedc1); color: #333; border: none; padding: 10px 20px; font-size: 16px; border-radius: 8px; cursor: pointer; margin: 10px; }
table { width: 80%; max-width: 600px; margin: 20px auto; background: rgba(255,255,255,0.8); border-radius: 12px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
th, td { padding: 12px; text-align: left; border-bottom: 1px solid rgba(0,0,0,0.1); }
th { background: linear-gradient(#ff9a9e, #fecfef); color: #333; }
tr:hover { background: rgba(255, 182, 193, 0.2); }
@media (max-width: 600px) { table { width: 95%; font-size: 14px; } }
</style>
</head><body>
<h1><i class="fas fa-history"></i> Historial de Alarmas</h1>
<button class="back" onclick="window.location.href='/'"><i class="fas fa-arrow-left"></i> Volver al Dashboard</button>
{% if alerts %}
<table>
<thead><tr><th><i class="fas fa-clock"></i> Hora</th><th><i class="fas fa-bell"></i> Tipo</th><th><i class="fas fa-bolt"></i> Voltaje (V)</th></tr></thead>
<tbody>
{% for alert in alerts %}
<tr><td>{{ alert.time }}</td><td>{{ alert.type }}</td><td>{{ alert.volt }}</td></tr>
{% endfor %}
</tbody>
</table>
{% else %}
<p>No hay alertas en el historial.</p>
{% endif %}
</body></html>
''')

@app.route('/')
def index():
    global armed, intrusion, solar_volt, auto_volt, last_update
    solar_volt = round(random.uniform(3.5, 5.0), 2)
    auto_volt = round(random.uniform(11.5, 14.5), 2)
    last_update = time.strftime("%H:%M:%S")
    return render_template_string(DASHBOARD_TEMPLATE, armed=armed, intrusion=intrusion, solar_volt=solar_volt, auto_volt=auto_volt, alerts=alerts, last_update=last_update)

@app.route('/history')
def history():
    return render_template_string(HISTORY_TEMPLATE, alerts=alerts)

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
    if len(alerts) > 50:  # Aumentado para historial más amplio
        alerts = alerts[-50:]  # Últimas 50
    print(f"Alerta del ESP32: {message} - Volt: {volt}")
    return jsonify({"status": "Alerta recibida"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)