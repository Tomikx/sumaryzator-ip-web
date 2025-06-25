import ipaddress
import os
import sys
import importlib # Dodano import modułu importlib

# --- WAŻNA KOREKTA ŁADOWANIA MODUŁU IPADDRESS ---
# Problem: Mimo Pythona 3.9+, ładuje się zewnętrzny pakiet 'ipaddress' (wersja 1.0)
#          zamiast wbudowanego modułu, co powoduje brak common_network.
# Rozwiązanie: Sprawdź, czy załadowany moduł to problematyczny backport.
#              Jeśli tak, usuń go z sys.modules i spróbuj załadować wbudowany.
if hasattr(ipaddress, '__version__') and ipaddress.__version__ == '1.0':
    print("WARNING: Detected problematic 'ipaddress' module version 1.0. Attempting to reload built-in module.")
    try:
        # Usuń problematyczny moduł z bufora sys.modules
        if 'ipaddress' in sys.modules:
            del sys.modules['ipaddress']
        # Załaduj ponownie moduł ipaddress
        ipaddress = importlib.import_module('ipaddress')
        print("INFO: Successfully reloaded 'ipaddress' module.")
    except Exception as e:
        print(f"ERROR: Failed to reload 'ipaddress' module: {e}")
        # Jeśli ponowne załadowanie się nie powiedzie, to dalej będziemy mieć problem.
# --- KONIEC KOREKTY ---


from flask import Flask, request, render_template_string

app = Flask(__name__)

# HTML template for the user interface
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
        .options-group {
            margin-bottom: 20px;
            padding: 10px;
            border: 1px solid #eee;
            border-radius: 4px;
            background-color: #f9f9f9;
        }
        .options-group label {
            display: inline-block;
            font-weight: normal;
            margin-bottom: 0;
            cursor: pointer;
        }
        .options-group input[type="checkbox"] {
            margin-right: 5px;
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
        .python-info { /* Style for Python version info */
            text-align: center;
            margin-top: 10px;
            font-size: 0.8em;
            color: #555;
        }
        footer {
            text-align: center;
            margin-top: 30px;
            font-size: 0.9em;
            color: #777;
        }
        .debug-info { /* Style for debug info */
            background-color: #ffe0b2; /* Light orange */
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            border: 1px solid #ffcc80;
            font-size: 0.85em;
            text-align: left;
        }
        .debug-info h4 {
            margin-top: 0;
            color: #e65100; /* Dark orange */
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

            <div class="options-group">
                <input type="checkbox" id="aggressive_mode" name="aggressive_mode" value="true" {% if aggressive_mode_checked %}checked{% endif %}>
                <label for="aggressive_mode">Agresywna sumaryzacja (znajdź najmniejszy wspólny supernet)</label><br>
                <span style="font-size: 0.85em; color: #666;">(Może obejmować puste przestrzenie między podanymi sieciami, zwracając jeden lub dwa bloki dla wszystkich wpisów.)</span>
            </div>

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
    <div class="debug-info">
        <h4>Informacje diagnostyczne:</h4>
        <p>Wersja Pythona: <code>{{ python_version_info }}</code></p>
        <p>Czy `ipaddress.common_network` istnieje?: <code>{{ common_network_exists }}</code></p>
        <p>Ścieżka do modułu `ipaddress`: <code>{{ ipaddress_file_path }}</code></p>
        <p>Wersja modułu `ipaddress` (jeśli dostępna): <code>{{ ipaddress_version }}</code></p>
        <p>Zawartość `sys.modules['ipaddress']`: <code>{{ sys_modules_ipaddress }}</code></p>
        <p><code>sys.path</code>:</p>
        <pre>{{ sys_path_info }}</pre>
    </div>
    <footer>
        <p>Powered by Flask & Python ipaddress library</p>
    </footer>
</body>
</html>
"""

def summarize_networks_logic(ip_networks_list, aggressive_mode_enabled=False):
    """
    Logic for summarizing IP addresses or networks in CIDR format.
    The function returns a list of summarized networks, a list of errors, and a list of warnings.
    """
    summarized_results = []
    errors = []
    warnings = []
    parsed_networks_ipv4 = []
    parsed_networks_ipv6 = []
    
    # Flag to track if any non-empty lines were provided in input
    has_valid_input_lines = False

    for entry in ip_networks_list:
        entry = entry.strip()
        if not entry:
            continue
        
        has_valid_input_lines = True # Found a non-empty line

        try:
            if '/' in entry:
                # If it contains '/', treat as a CIDR network
                network_obj = ipaddress.ip_network(entry, strict=False)
            else:
                # If it doesn't contain '/', treat as a single IP address (host)
                ip_addr = ipaddress.ip_address(entry)
                if ip_addr.version == 4:
                    # For IPv4, add /32
                    network_obj = ipaddress.ip_network(str(ip_addr) + '/32', strict=False)
                elif ip_addr.version == 6:
                    # For IPv6, add /128
                    network_obj = ipaddress.ip_network(str(ip_addr) + '/128', strict=False)
                else:
                    warnings.append(f"Unsupported IP version: '{entry}'. Skipping.")
                    continue
            
            if network_obj.version == 4:
                parsed_networks_ipv4.append(network_obj)
            elif network_obj.version == 6:
                parsed_networks_ipv6.append(network_obj)

        except ValueError:
            warnings.append(f"Invalid IP/network format or invalid address: '{entry}'. Skipping.")
            continue
    
    if not parsed_networks_ipv4 and not parsed_networks_ipv6:
        # If input was not empty, but nothing could be parsed
        if has_valid_input_lines and not errors and not warnings:
            errors.append("No valid entries for summarization.")
        return [], errors, warnings

    if aggressive_mode_enabled:
        # AGGRESSIVE SUMMARIZATION LOGIC
        # common_network(*iterable) is safe even for a list with 1 element.
        # Requires Python 3.9+ for the common_network function.
        try: # Added general try-except block for aggressive logic
            # Sprawdzamy czy common_network istnieje przed wywołaniem, po ewentualnym przeładowaniu modułu
            if not hasattr(ipaddress, 'common_network'):
                errors.append("Error: 'ipaddress.common_network' function is not available in the loaded 'ipaddress' module. Despite Python 3.9+, a module conflict persists. Contact support or try a different environment.")
                # We return here as this is a critical error for aggressive mode
                return [], errors, warnings

            if parsed_networks_ipv4:
                try:
                    supernet_v4 = ipaddress.common_network(*parsed_networks_ipv4)
                    summarized_results.append(str(supernet_v4))
                except ValueError as e:
                    errors.append(f"IPv4 aggressive summarization error (common_network): {e}. Ensure all addresses are valid and belong to the same IP version.")
                except TypeError as e:
                    errors.append(f"Internal type error during IPv4 aggressive summarization: {e}")


            if parsed_networks_ipv6:
                try:
                    supernet_v6 = ipaddress.common_network(*parsed_networks_ipv6)
                    summarized_results.append(str(supernet_v6))
                except ValueError as e:
                    errors.append(f"IPv6 aggressive summarization error (common_network): {e}. Ensure all addresses are valid and belong to the same IP version.")
                except TypeError as e:
                    errors.append(f"Internal type error during IPv6 aggressive summarization: {e}")
        except Exception as e:
            # Final catch for any other unexpected errors in aggressive mode
            errors.append(f"Unexpected error in aggressive summarization mode: {e}.")


    else:
        # STANDARD SUMMARIZATION LOGIC (using collapse_addresses)
        if parsed_networks_ipv4:
            parsed_networks_ipv4.sort() # IMPORTANT: Ensure sorted for collapse_addresses
            collapsed_v4 = list(ipaddress.collapse_addresses(parsed_networks_ipv4))
            summarized_results.extend([str(s) for s in collapsed_v4])

        if parsed_networks_ipv6:
            parsed_networks_ipv6.sort() # IMPORTANT: Ensure sorted for collapse_addresses
            collapsed_v6 = list(ipaddress.collapse_addresses(parsed_networks_ipv6))
            summarized_results.extend([str(s) for s in collapsed_v6])

    # Sort final results for consistent display (e.g., IPv4 before IPv6, then by value)
    # This also handles cases where one of the lists (IPv4/IPv6) was empty.
    summarized_results.sort(key=ipaddress.ip_network)
    
    return summarized_results, errors, warnings

@app.route('/', methods=['GET', 'POST'])
def index():
    summarized_networks = []
    user_input = ""
    errors = []
    warnings = []
    aggressive_mode_checked = False
    
    # Get Python version information
    python_version_info = sys.version
    
    # Check if common_network attribute exists in ipaddress module
    common_network_exists = hasattr(ipaddress, 'common_network')

    # Get the file path of the loaded ipaddress module
    ipaddress_file_path = getattr(ipaddress, '__file__', 'Unknown path (ipaddress module has no __file__ attribute)')
    
    # Get the version of the ipaddress module (if available)
    # Standard library modules usually don't have __version__
    ipaddress_version = getattr(ipaddress, '__version__', 'Undefined')

    # Get the representation of the ipaddress module from sys.modules
    # Use repr() to see the full object representation
    sys_modules_ipaddress = repr(sys.modules.get('ipaddress', 'ipaddress module not found in sys.modules'))
    
    # Get sys.path information
    sys_path_info = "\n".join(sys.path)


    if request.method == 'POST':
        user_input = request.form['networks']
        networks_from_form = user_input.splitlines()
        # Check if the 'aggressive_mode' checkbox was checked
        aggressive_mode_checked = 'aggressive_mode' in request.form
        
        summarized_networks, errors, warnings = summarize_networks_logic(
            networks_from_form, 
            aggressive_mode_enabled=aggressive_mode_checked
        )

    return render_template_string(HTML_TEMPLATE, 
                                  summarized_networks=summarized_networks,
                                  user_input=user_input,
                                  errors=errors,
                                  warnings=warnings,
                                  aggressive_mode_checked=aggressive_mode_checked,
                                  python_version_info=python_version_info,
                                  common_network_exists=common_network_exists,
                                  ipaddress_file_path=ipaddress_file_path,
                                  ipaddress_version=ipaddress_version,
                                  sys_modules_ipaddress=sys_modules_ipaddress,
                                  sys_path_info=sys_path_info)

if __name__ == '__main__':
    # Running the Flask server
    # 'host='0.0.0.0'' allows access from outside (e.g., from local network)
    # 'port=int(os.environ.get('PORT', 5000))' allows dynamic port setting by hosting provider
    # 'debug=True' is good for development, but ALWAYS set to False in production!
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
