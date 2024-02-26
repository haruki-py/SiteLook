from flask import Flask, render_template, redirect, request, session
from flask_cors import CORS
from threading import Thread
import requests
import json
from werkzeug.serving import make_ssl_devcert

app = Flask('')
CORS(app)  # This will allow the frontend to make requests to the backend

# Replace these values with your own
CLIENT_ID = '1122457639226441829'
CLIENT_SECRET = 'UXzDUBCkbSKro4QGmaBEAZwd56XuyGBG'
REDIRECT_URI = 'https://dono-03.danbot.host:3114/callback'

# This variable will store the user's access token
access_token = None

# Set up Flask sessions to store data securely
app.secret_key = 'YOUR_SECRET_KEY_HERE'

@app.before_request
def force_https():
    if not request.is_secure:
        url = request.url.replace('http://', 'https://', 1)
        code = 301
        return redirect(url, code=code)
    


@app.route('/addMonitor', methods=['POST'])
def add_monitor():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")

    monitor = request.get_json()
    with open('websites.json', 'r+') as f:
        websites = json.load(f)
        user_websites = websites.get(str(user_id), [])
        user_websites.append(monitor)
        websites[str(user_id)] = user_websites
        f.seek(0)
        json.dump(websites, f)
        f.truncate()

    return jsonify(success=True)

@app.route('/removeMonitor', methods=['POST'])
def remove_monitor():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify(success=False, message="User not logged in")

    monitor_index = request.get_json().get('index')
    with open('websites.json', 'r+') as f:
        websites = json.load(f)
        user_websites = websites.get(str(user_id), [])
        user_websites = [m for m in user_websites if m.get('index') != monitor_index]
        websites[str(user_id)] = user_websites
        f.seek(0)
        json.dump(websites, f)
        f.truncate()

    return jsonify(success=True)


@app.route('/')
def main():
    # Render the index template
    return render_template('index.html')

@app.route('/login')
def login():
    # Redirect the user to the Discord login page
    url = f'https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify'
    return redirect(url)

@app.route('/callback')
def callback():
    global access_token
    # Exchange the code for an access token
    code = request.args.get('code')
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'scope': 'identify'
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    response_json = response.json()
    access_token = response_json['access_token']
    
    # Use the access token to get the user's ID and store it in the session
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    response = requests.get('https://discord.com/api/users/@me', headers=headers)
    response_json = response.json()
    user_id = response_json['id']
    session['user_id'] = user_id
    
    # Redirect the user to the dashboard
    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    # Get the user's ID from the session
    user_id = session.get('user_id')
    
    # Load the websites.json file and get the list of websites for this user
    with open('websites.json', 'r') as f:
        websites = json.load(f)
    user_websites = websites.get(str(user_id), [])
    
    # Render the dashboard template with the list of websites
    return render_template('dashboard.html', websites=user_websites)

def run():
   
   # Create a self-signed certificate and store it in ssl.crt and ssl.key files
   make_ssl_devcert('./ssl', host='dono-03.danbot.host')
   
   # Run the app with SSL context
   app.run(host="0.0.0.0", port=3114, ssl_context=('ssl.crt', 'ssl.key'))

def keep_alive():
   server = Thread(target=run)
   server.start()