# legacy
from flask import Flask, render_template_string
from threading import Thread, Lock
import webbrowser
import logging

app = Flask(__name__)
messages = []  # Store messages persistently
messages_lock = Lock()  # Thread-safe operations

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>LLM Monitor</title>
    <style>
        body { font-family: monospace; margin: 20px; background: #f0f0f0; }
        .container { max-width: 1200px; margin: 0 auto; }
        .message { margin: 10px 0; padding: 15px; background: white; border-radius: 5px; }
        .system { border-left: 4px solid #4CAF50; }
        .user { border-left: 4px solid #2196F3; }
        .assistant { border-left: 4px solid #FF9800; }
        pre { white-space: pre-wrap; margin: 0; }
    </style>
    <script>
        let previousData = [];
        
        function updateMessages() {
            fetch('/get_messages')
                .then(response => response.json())
                .then(data => {
                    // Only update if there are messages and they're different from previous
                    if (data.length > 0 && JSON.stringify(data) !== JSON.stringify(previousData)) {
                        const container = document.getElementById('messages');
                        container.innerHTML = '';
                        data.forEach(msg => {
                            const div = document.createElement('div');
                            div.className = `message ${msg.role}`;
                            div.innerHTML = `<strong>${msg.role}:</strong><pre>${msg.content}</pre>`;
                            container.appendChild(div);
                        });
                        previousData = data;
                    }
                });
        }
        setInterval(updateMessages, 1000);
    </script>
</head>
<body>
    <div class="container">
        <h1>LLM Interaction Monitor</h1>
        <div id="messages"></div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/get_messages')
def get_messages():
    with messages_lock:
        return messages.copy()

def add_message(role: str, content: str):
    with messages_lock:
        messages.append({"role": role, "content": content})

def clear_messages():
    with messages_lock:
        messages.clear()

def run_flask():
    # Disable Flask's logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Disable Flask's internal messages
    app.logger.disabled = True
    
    # Run Flask without debug messages
    app.run(port=5050, debug=False)

def start_monitor():
    thread = Thread(target=run_flask, daemon=True)
    thread.start()
    webbrowser.open('http://localhost:5050') 