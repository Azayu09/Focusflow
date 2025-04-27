from flask import Flask, request
import subprocess

app = Flask(__name__)
process = None

@app.route('/start', methods=['POST'])
def start_script():
    global process
    if process is None or process.poll() is not None:
        process = subprocess.Popen(['python3', 'attention_debug.py'])
    return 'Started', 200

@app.route('/stop', methods=['POST'])
def stop_script():
    global process
    if process and process.poll() is None:
        process.terminate()
        process = None
    return 'Stopped', 200

if __name__ == '__main__':
    app.run(port=5050)
