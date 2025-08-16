import os
from flask import Flask, request, jsonify, Response
import time
import random
import requests
from bs4 import BeautifulSoup
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import pytz
import atexit

app = Flask(__name__)

# Configuration de base
app.config['TEMPLATES_AUTO_RELOAD'] = True

# État du lapin
rabbit_state = {
    'ears_position': {'left': 90, 'right': 90},
    'led_color': '#FF0000',
    'message': 'Prêt à fonctionner!',
    'last_action': 'Aucune action récente',
    'tts_playing': False
}
RADIO_FEEDS = {
    'franceinfo': 'https://www.francetvinfo.fr/titres.rss',
    'franceinter': 'https://www.franceinter.fr/rss/a-la-une.xml',
    'bbc': 'http://feeds.bbci.co.uk/news/rss.xml',
    'rtl': 'https://www.rtl.fr/actu/rss'
}

# Modifiez rabbit_state pour ajouter la radio
rabbit_state = {
    # ... [le reste des états] ...,
    'radio_playing': False,
    'current_radio': None
}

# Ajoutez cette fonction
def get_radio_news(feed_name):
    """Récupère les dernières actualités radio"""
    if feed_name not in RADIO_FEEDS:
        return "Radio non configurée"
    
    try:
        feed = feedparser.parse(RADIO_FEEDS[feed_name])
        if not feed.entries:
            return "Pas d'actualités disponibles"
            
        latest_news = []
        for entry in feed.entries[:3]:  # 3 dernières actualités
            title = entry.get('title', 'Sans titre')
            summary = entry.get('summary', '')[:100]  # 100 premiers caractères
            latest_news.append(f"{title}. {summary}")
        
        return "Dernières actualités: " + " ".join(latest_news)
    except Exception as e:
        return f"Erreur radio: {str(e)}"

# Middleware CORS
@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = Response()
        res.headers['Access-Control-Allow-Origin'] = '*'
        res.headers['Access-Control-Allow-Headers'] = '*'
        return res

# Ajoutez cette route API
@app.route('/radio/<feed_name>', methods=['POST'])
def play_radio(feed_name):
    try:
        news = get_radio_news(feed_name)
        rabbit_state['message'] = news
        rabbit_state['radio_playing'] = True
        rabbit_state['current_radio'] = feed_name
        rabbit_state['last_action'] = f"Écoute de {feed_name}"
        
        # Simule la durée d'écoute
        time.sleep(10)  # 10 secondes d'écoute
        rabbit_state['radio_playing'] = False
        
        return jsonify({
            'status': 'success',
            'radio': feed_name,
            'news': news
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Routes API
@app.route('/led', methods=['POST', 'OPTIONS'])
def led():
    try:
        if request.is_json:
            color = request.json.get('color', '#FF0000')
        else:
            color = request.form.get('color', '#FF0000')
        
        # Validation couleur
        if not color.startswith('#'):
            color = '#' + color
        if len(color) not in [4, 7]:  # Format #RGB ou #RRGGBB
            color = '#FF0000'

        rabbit_state['led_color'] = color
        rabbit_state['last_action'] = f"LED changée: {color}"
        
        return jsonify({'status': 'success', 'color': color})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/ears', methods=['POST', 'OPTIONS'])
def ears():
    try:
        if request.is_json:
            left = int(request.json.get('left', 90))
            right = int(request.json.get('right', 90))
        else:
            left = int(request.form.get('left', 90))
            right = int(request.form.get('right', 90))
        
        # Validation angles
        left = max(0, min(180, left))
        right = max(0, min(180, right))

        rabbit_state['ears_position'] = {'left': left, 'right': right}
        rabbit_state['last_action'] = f"Oreilles: G{left}° D{right}°"
        
        return jsonify({'status': 'success', 'left': left, 'right': right})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/tts', methods=['POST', 'OPTIONS'])
def tts():
    try:
        if request.is_json:
            text = request.json.get('text', '')
        else:
            text = request.form.get('text', '')
        
        if not text:
            return jsonify({'status': 'error', 'message': 'Aucun texte fourni'}), 400

        rabbit_state['message'] = text
        rabbit_state['tts_playing'] = True
        rabbit_state['last_action'] = f"Message: {text[:20]}..."
        
        # Simulation durée parole
        time.sleep(len(text) * 0.05)
        rabbit_state['tts_playing'] = False
        
        return jsonify({'status': 'success', 'text': text})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/rfid', methods=['GET'])
def rfid():
    return jsonify({'status': 'no_tag'})

# Interface de contrôle
@app.route('/')
def control_panel():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Contrôle Nabaztag</title>
        <meta charset="UTF-8">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                text-align: center;
            }
            .control-section {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                margin-bottom: 20px;
                background-color: #fafafa;
            }
            h2 {
                color: #3498db;
                margin-top: 0;
                border-bottom: 1px solid #eee;
                padding-bottom: 10px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input[type="color"], 
            input[type="number"], 
            input[type="text"] {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                width: 100%;
                box-sizing: border-box;
            }
            button {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px 15px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                transition: background-color 0.3s;
            }
            button:hover {
                background-color: #2980b9;
            }
            .status {
                background-color: #e8f4fc;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
            }
            .status h2 {
                color: #2c3e50;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Contrôle Nabaztag</h1>
            <div class="control-section">
    <h2>Radio</h2>
    <div class="form-group">
        <label for="radioStation">Station :</label>
        <select id="radioStation">
            <option value="franceinfo">France Info</option>
            <option value="franceinter">France Inter</option>
            <option value="bbc">BBC</option>
            <option value="rtl">RTL</option>
        </select>
    </div>
    <button onclick="playRadio()">Écouter</button>
</div>

<script>
async function playRadio() {
    const station = document.getElementById('radioStation').value;
    try {
        const response = await fetch(`/radio/${station}`, {
            method: 'POST'
        });
        const data = await response.json();
        if (data.status === 'success') {
            updateStatus(`Écoute: ${station}`);
        } else {
            showError(data.message);
        }
    } catch (error) {
        showError('Connexion impossible');
    }
}
</script>
            
            <div class="control-section">
                <h2>Contrôle LED</h2>
                <div class="form-group">
                    <label for="ledColor">Couleur :</label>
                    <input type="color" id="ledColor" value="#FF0000">
                </div>
                <button onclick="setLED()">Appliquer</button>
            </div>
            
            <div class="control-section">
                <h2>Contrôle des oreilles</h2>
                <div class="form-group">
                    <label for="leftEar">Oreille gauche (0-180°) :</label>
                    <input type="number" id="leftEar" min="0" max="180" value="90">
                </div>
                <div class="form-group">
                    <label for="rightEar">Oreille droite (0-180°) :</label>
                    <input type="number" id="rightEar" min="0" max="180" value="90">
                </div>
                <button onclick="moveEars()">Bouger les oreilles</button>
            </div>
            
            <div class="control-section">
                <h2>Synthèse vocale</h2>
                <div class="form-group">
                    <label for="ttsText">Message à prononcer :</label>
                    <input type="text" id="ttsText" placeholder="Entrez votre texte">
                </div>
                <button onclick="speak()">Lire le message</button>
            </div>
            
            <div class="status">
                <h2>État du système</h2>
                <p><strong>Dernière action :</strong> <span id="lastAction">Prêt</span></p>
                <p><strong>Statut :</strong> <span id="status">En attente...</span></p>
            </div>
        </div>

        <script>
            function updateStatus(message) {
                document.getElementById('lastAction').textContent = message;
                document.getElementById('status').textContent = 'OK';
                setTimeout(() => {
                    document.getElementById('status').textContent = 'En attente...';
                }, 2000);
            }

            function showError(message) {
                document.getElementById('status').textContent = 'Erreur: ' + message;
            }

            async function setLED() {
                const color = document.getElementById('ledColor').value;
                try {
                    const response = await fetch('/led', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ color })
                    });
                    const data = await response.json();
                    if (data.status === 'success') {
                        updateStatus(`LED changée: ${color}`);
                    } else {
                        showError(data.message || 'Erreur inconnue');
                    }
                } catch (error) {
                    showError('Connexion au serveur impossible');
                }
            }

            async function moveEars() {
                const left = document.getElementById('leftEar').value;
                const right = document.getElementById('rightEar').value;
                try {
                    const response = await fetch('/ears', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ left, right })
                    });
                    const data = await response.json();
                    if (data.status === 'success') {
                        updateStatus(`Oreilles: G${left}° D${right}°`);
                    } else {
                        showError(data.message || 'Erreur inconnue');
                    }
                } catch (error) {
                    showError('Connexion au serveur impossible');
                }
            }

            async function speak() {
                const text = document.getElementById('ttsText').value;
                if (!text) {
                    showError('Veuillez entrer un message');
                    return;
                }
                try {
                    const response = await fetch('/tts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text })
                    });
                    const data = await response.json();
                    if (data.status === 'success') {
                        updateStatus(`Message: "${text.substring(0, 20)}${text.length > 20 ? '...' : ''}"`);
                    } else {
                        showError(data.message || 'Erreur inconnue');
                    }
                } catch (error) {
                    showError('Connexion au serveur impossible');
                }
            }
        </script>
    </body>
    </html>
    """

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, threaded=True)