"""
UTRA Data Analysis - Flask Backend
"""
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/ingest', methods=['POST'])
def ingest():
    # TODO: Save raw JSON logs to MongoDB
    pass

@app.route('/runs', methods=['GET'])
def get_runs():
    # TODO: Return list of past runs
    pass

@app.route('/analyze', methods=['POST'])
def analyze():
    # TODO: Send run data to OpenRouter for AI analysis
    pass

if __name__ == '__main__':
    app.run(debug=True, port=5000)
