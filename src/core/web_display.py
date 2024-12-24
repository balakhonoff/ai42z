from flask import Flask, render_template_string
import threading
import webbrowser
from flask_cors import CORS
import os

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>LLM Processor Prompt</title>
    <meta http-equiv="Content-Security-Policy" content="default-src 'self' 'unsafe-inline'">
    <style>
        body {
            font-family: monospace;
            padding: 20px;
            max-width: 1200px;
            margin: 0 auto;
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
        pre {
            white-space: pre-wrap;
            background-color: #2d2d2d;
            padding: 15px;
            border-radius: 5px;
        }
        h1 {
            color: #569cd6;
        }
    </style>
    <script>
        function refreshContent() {
            fetch('http://127.0.0.1:5000/prompt', {
                method: 'GET',
                headers: {
                    'Accept': 'text/plain',
                },
            })
            .then(response => response.text())
            .then(data => {
                document.getElementById('prompt-content').innerHTML = data;
            })
            .catch(error => console.error('Error:', error));
        }
        // Refresh every 2 seconds
        setInterval(refreshContent, 2000);
    </script>
</head>
<body>
    <h1>LLM Processor Prompt</h1>
    <pre id="prompt-content">{{ prompt }}</pre>
</body>
</html>
'''

class PromptDisplay:
    def __init__(self, port=5000):
        self.app = Flask(__name__)
        CORS(self.app, resources={r"/*": {"origins": "*"}})  # More permissive CORS
        self.port = port
        self.current_prompt = ""
        
        @self.app.route('/')
        def home():
            return render_template_string(HTML_TEMPLATE, prompt=self.current_prompt)
            
        @self.app.route('/prompt')
        def get_prompt():
            return self.current_prompt
            
    def update_prompt(self, prompt: str):
        self.current_prompt = prompt
        
    def start(self):
        def run_server():
            # More permissive server configuration
            self.app.run(
                host='127.0.0.1',  # Localhost only
                port=self.port,
                debug=False,
                threaded=True,
                ssl_context=None  # Disable SSL for local development
            )
            
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        
        # Give the server a moment to start
        import time
        time.sleep(1)
        
        # Open in default browser
        webbrowser.open(f'http://127.0.0.1:{self.port}') 