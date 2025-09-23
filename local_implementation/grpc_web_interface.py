#!/usr/bin/env python3
"""Simple web interface for AIFS gRPC API exploration."""

import json
import grpc
from flask import Flask, render_template_string, request, jsonify
from aifs.proto import aifs_pb2, aifs_pb2_grpc

app = Flask(__name__)

# gRPC connection
channel = None
stub = None

def connect_grpc(host="localhost", port=50051):
    """Connect to gRPC server."""
    global channel, stub
    try:
        channel = grpc.insecure_channel(f"{host}:{port}")
        stub = aifs_pb2_grpc.AIFSStub(channel)
        return True
    except Exception as e:
        print(f"Failed to connect to gRPC server: {e}")
        return False

# HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AIFS gRPC API Explorer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .method { border: 1px solid #ccc; margin: 10px 0; padding: 15px; }
        .method h3 { margin-top: 0; color: #333; }
        .input-group { margin: 10px 0; }
        .input-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .input-group input, .input-group textarea { width: 100%; padding: 8px; }
        .btn { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
        .btn:hover { background: #0056b3; }
        .result { background: #f8f9fa; padding: 10px; margin-top: 10px; border-left: 4px solid #007bff; }
        .error { border-left-color: #dc3545; background: #f8d7da; }
    </style>
</head>
<body>
    <h1>AIFS gRPC API Explorer</h1>
    
    <div class="method">
        <h3>Health Check</h3>
        <button class="btn" onclick="callHealth()">Check Health</button>
        <div id="health-result" class="result" style="display:none;"></div>
    </div>
    
    <div class="method">
        <h3>List Assets</h3>
        <div class="input-group">
            <label>Limit:</label>
            <input type="number" id="list-limit" value="10">
        </div>
        <div class="input-group">
            <label>Offset:</label>
            <input type="number" id="list-offset" value="0">
        </div>
        <button class="btn" onclick="callListAssets()">List Assets</button>
        <div id="list-result" class="result" style="display:none;"></div>
    </div>
    
    <div class="method">
        <h3>Get Asset</h3>
        <div class="input-group">
            <label>Asset ID:</label>
            <input type="text" id="get-asset-id" placeholder="Enter asset ID">
        </div>
        <div class="input-group">
            <label>
                <input type="checkbox" id="include-data"> Include Data
            </label>
        </div>
        <button class="btn" onclick="callGetAsset()">Get Asset</button>
        <div id="get-result" class="result" style="display:none;"></div>
    </div>
    
    <div class="method">
        <h3>List Namespaces</h3>
        <div class="input-group">
            <label>Limit:</label>
            <input type="number" id="ns-limit" value="10">
        </div>
        <div class="input-group">
            <label>Offset:</label>
            <input type="number" id="ns-offset" value="0">
        </div>
        <button class="btn" onclick="callListNamespaces()">List Namespaces</button>
        <div id="ns-result" class="result" style="display:none;"></div>
    </div>

    <script>
        function showResult(elementId, data, isError = false) {
            const element = document.getElementById(elementId);
            element.style.display = 'block';
            element.className = 'result' + (isError ? ' error' : '');
            element.innerHTML = '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
        }
        
        async function callHealth() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                showResult('health-result', data);
            } catch (error) {
                showResult('health-result', {error: error.message}, true);
            }
        }
        
        async function callListAssets() {
            try {
                const limit = document.getElementById('list-limit').value;
                const offset = document.getElementById('list-offset').value;
                const response = await fetch(`/api/list-assets?limit=${limit}&offset=${offset}`);
                const data = await response.json();
                showResult('list-result', data);
            } catch (error) {
                showResult('list-result', {error: error.message}, true);
            }
        }
        
        async function callGetAsset() {
            try {
                const assetId = document.getElementById('get-asset-id').value;
                const includeData = document.getElementById('include-data').checked;
                const response = await fetch(`/api/get-asset/${assetId}?include_data=${includeData}`);
                const data = await response.json();
                showResult('get-result', data);
            } catch (error) {
                showResult('get-result', {error: error.message}, true);
            }
        }
        
        async function callListNamespaces() {
            try {
                const limit = document.getElementById('ns-limit').value;
                const offset = document.getElementById('ns-offset').value;
                const response = await fetch(`/api/list-namespaces?limit=${limit}&offset=${offset}`);
                const data = await response.json();
                showResult('ns-result', data);
            } catch (error) {
                showResult('ns-result', {error: error.message}, true);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/health')
def api_health():
    """Health check API endpoint."""
    try:
        if not stub:
            return jsonify({"error": "Not connected to gRPC server"}), 500
        
        # Note: This would need proper authentication in a real implementation
        response = {"message": "Health check endpoint - implement actual gRPC call"}
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/list-assets')
def api_list_assets():
    """List assets API endpoint."""
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        if not stub:
            return jsonify({"error": "Not connected to gRPC server"}), 500
        
        # Note: This would need proper authentication in a real implementation
        response = {
            "message": "List assets endpoint",
            "limit": limit,
            "offset": offset,
            "note": "Implement actual gRPC call with authentication"
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-asset/<asset_id>')
def api_get_asset(asset_id):
    """Get asset API endpoint."""
    try:
        include_data = request.args.get('include_data', 'false').lower() == 'true'
        
        if not stub:
            return jsonify({"error": "Not connected to gRPC server"}), 500
        
        response = {
            "message": "Get asset endpoint",
            "asset_id": asset_id,
            "include_data": include_data,
            "note": "Implement actual gRPC call with authentication"
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/list-namespaces')
def api_list_namespaces():
    """List namespaces API endpoint."""
    try:
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        if not stub:
            return jsonify({"error": "Not connected to gRPC server"}), 500
        
        response = {
            "message": "List namespaces endpoint",
            "limit": limit,
            "offset": offset,
            "note": "Implement actual gRPC call with authentication"
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def main():
    """Main function."""
    print("Starting AIFS gRPC Web Interface...")
    
    # Try to connect to gRPC server
    if connect_grpc():
        print("✅ Connected to gRPC server")
    else:
        print("⚠️  Could not connect to gRPC server - some features may not work")
    
    print("🌐 Web interface available at: http://localhost:5000")
    print("📖 This provides a simple web interface to explore your gRPC API")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == "__main__":
    main()
