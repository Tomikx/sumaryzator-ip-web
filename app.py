import ipaddress
import os
from flask import Flask, request, render_template_string

app = Flask(__name__)

# Szablon HTML dla interfejsu użytkownika
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sumaryzator Sieci IP</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f4f4f4;
            color: #333;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: #fff;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
        }
        h1 {
            color: #0056b3;
            text-align: center;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        textarea {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
            min-height: 150px;
            font-family: monospace;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
        }
        button:hover {
            background-color: #0056b3;
        }
        h2 {
            margin-top: 30px;
            color: #0056b3;
            text-align: center;
        }
        pre {
            background-color: #e9e9e9;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        .error {
            color: red;
            font-weight: bold;
            margin-top: 10px;
        }
        .warning {
            color: orange;
            font-weight: bold;
            margin-top: 10px;
        }
        footer {
            text-align: center;
            margin-top: 30px;
            font-size: 0.9em;
            color: #777;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Sumaryzator Sieci IP</h1>
        <p>Wprowadź adresy IP lub sieci (CIDR) w poniższym polu tekstowym, jeden na linię. Obsługiwane są zarówno adresy IPv4, jak i IPv6.</p>
        <form method="POST">
            <label for="networks">Adresy IP / Sieci:</label>
            <textarea id="networks" name="networks" placeholder="Np.:
192.168.1.0/24
192.168.2.0/24
192.168.1.1
2001:db8::/32
2001:db8:1::/48
">{{ user_input }}</textarea>
            <button type="submit">Sumaryzuj</button>
        </form>

        {% if errors %}
            <div class="error">
                <h3>Wystąpiły błędy:</h3>
                <ul>
                    {% for error in errors %}
                        <li>{{ error }}</li>
                    {% endfor %}
                </ul>
            </div>
        {% endif %}

        {% if warnings %}
            <div class="warning">
                <h3>Ostrzeżenia:</h3>
                <ul>
                    {% for warning in warnings %}
                        <li>{{ warning }}</li>
                    {% endfor %}
                </ul>
            </div>
        {% endif %}

        {% if summarized_networks %}
            <h2>Zsumowane sieci</h2>
            <pre>{{ '\n'.join(summarized_networks) }}</pre>
        {% elif user_input and not errors %}
            <h2>Brak sieci do sumaryzacji lub wszystkie wpisy były nieprawidłowe.</h2>
        {% endif %}
    </div>
    <footer>
        <p>Powered by Flask & Python ipaddress library</p>
    </footer>
</body>
</html>
"""

def summarize_networks_logic(ip_networks_list):
    """
    Logika sumaryzacji adresów IP lub sieci w formacie CIDR.
    Funkcja zwraca listę zsumowanych sieci, listę błędów i listę ostrzeżeń.
    """
    if not ip_networks_list:
        return [], [], []

    parsed_networks = []
    errors = []
    warnings = []
    
    # Flaga do śledzenia, czy wprowadzono jakiekolwiek niepuste linie
    has_valid_input_lines = False

    for entry in ip_networks_list:
        entry = entry.strip()
        if not entry:
            continue
        
        has_valid_input_lines = True # Znaleziono niepustą linię

        try:
            if '/' in entry:
                # Jeśli zawiera '/', traktuj jako sieć CIDR
                parsed_networks.append(ipaddress.ip_network(entry, strict=False))
            else:
                # Jeśli nie zawiera '/', traktuj jako pojedynczy adres IP (host)
                ip_addr = ipaddress.ip_address(entry)
                if ip_addr.version == 4:
                    # Dla IPv4, dodaj /32
                    parsed_networks.append(ipaddress.ip_network(str(ip_addr) + '/32', strict=False))
                elif ip_addr.version == 6:
                    # Dla IPv6, dodaj /128
                    parsed_networks.append(ipaddress.ip_network(str(ip_addr) + '/128', strict=False))
        except ValueError:
            warnings.append(f"Nieprawidłowy format IP/sieci lub nieprawidłowy adres: '{entry}'. Pomijam.")
            continue
    
    if not parsed_networks:
        # Jeśli nie było żadnych prawidłowych wpisów do parsowania, ale input był
        if has_valid_input_lines and not errors and not warnings:
            errors.append("Brak prawidłowych wpisów do sumaryzacji.")
        return [], errors, warnings

    # WAŻNA ZMIANA: Posortuj listę przed sumaryzacją
    # ipaddress.collapse_addresses działa najlepiej na posortowanych danych
    parsed_networks.sort() 

    # Użycie ipaddress.collapse_addresses do sumaryzacji
    summarized = list(ipaddress.collapse_addresses(parsed_networks))
    
    return [str(s) for s in summarized], errors, warnings

@app.route('/', methods=['GET', 'POST'])
def index():
    summarized_networks = []
    user_input = ""
    errors = []
    warnings = []

    if request.method == 'POST':
        user_input = request.form['networks']
        networks_from_form = user_input.splitlines()
        summarized_networks, errors, warnings = summarize_networks_logic(networks_from_form)

    return render_template_string(HTML_TEMPLATE, 
                                  summarized_networks=summarized_networks,
                                  user_input=user_input,
                                  errors=errors,
                                  warnings=warnings)

if __name__ == '__main__':
    # Uruchomienie serwera Flask
    # 'host='0.0.0.0'' pozwala na dostęp z zewnątrz (np. z sieci lokalnej)
    # 'port=int(os.environ.get('PORT', 5000))' pozwala na dynamiczne ustawienie portu przez hosting
    # 'debug=True' jest dobre do rozwoju, ale ZAWSZE ustaw na False w środowisku produkcyjnym!
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
