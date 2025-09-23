#!/usr/bin/env python3
"""
AIFS gRPC Web UI

Provides a Swagger-like web interface for exploring and testing the AIFS gRPC API.
"""

import json
import grpc
import asyncio
from typing import Dict, List, Any
from flask import Flask, render_template, request, jsonify, send_from_directory
import grpc_reflection
from grpc_reflection.v1alpha import reflection
from aifs.proto import aifs_pb2, aifs_pb2_grpc
from aifs.server import AIFSServicer, HealthServicer, IntrospectServicer
from aifs.asset import AssetManager
import os
import tempfile
import base64


class GRPCWebUI:
    """Web UI for gRPC API exploration and testing."""
    
    def __init__(self, server_host: str = "localhost", server_port: int = 50051):
        self.server_host = server_host
        self.server_port = server_port
        self.app = Flask(__name__)
        self.setup_routes()
        
        # Create gRPC channel
        self.channel = grpc.insecure_channel(f"{server_host}:{server_port}")
        
        # Create service stubs
        self.aifs_stub = aifs_pb2_grpc.AIFSStub(self.channel)
        self.health_stub = aifs_pb2_grpc.HealthStub(self.channel)
        self.introspect_stub = aifs_pb2_grpc.IntrospectStub(self.channel)
    
    def setup_routes(self):
        """Setup Flask routes."""
        
        @self.app.route('/')
        def index():
            return render_template('grpc_ui.html')
        
        @self.app.route('/api/services')
        def get_services():
            """Get list of available gRPC services."""
            try:
                # Try to get services via reflection
                reflection_stub = reflection.ReflectionStub(self.channel)
                services_response = reflection_stub.ListServices(aifs_pb2.DESCRIPTOR.services_by_name['Health'].full_name)
                services = list(services_response.service)
            except:
                # Fallback to known services
                services = [
                    "aifs.v1.AIFS",
                    "aifs.v1.Health", 
                    "aifs.v1.Introspect",
                    "aifs.v1.Admin",
                    "aifs.v1.Metrics",
                    "aifs.v1.Format"
                ]
            
            return jsonify({"services": services})
        
        @self.app.route('/api/methods/<service_name>')
        def get_methods(service_name: str):
            """Get methods for a specific service."""
            methods = {
                "aifs.v1.AIFS": [
                    {"name": "PutAsset", "input_type": "PutAssetRequest", "output_type": "PutAssetResponse", "streaming": "client"},
                    {"name": "GetAsset", "input_type": "GetAssetRequest", "output_type": "GetAssetResponse", "streaming": "unary"},
                    {"name": "DeleteAsset", "input_type": "DeleteAssetRequest", "output_type": "DeleteAssetResponse", "streaming": "unary"},
                    {"name": "ListAssets", "input_type": "ListAssetsRequest", "output_type": "ListAssetsResponse", "streaming": "unary"},
                    {"name": "VectorSearch", "input_type": "VectorSearchRequest", "output_type": "VectorSearchResponse", "streaming": "unary"},
                    {"name": "CreateSnapshot", "input_type": "CreateSnapshotRequest", "output_type": "CreateSnapshotResponse", "streaming": "unary"},
                    {"name": "GetSnapshot", "input_type": "GetSnapshotRequest", "output_type": "GetSnapshotResponse", "streaming": "unary"},
                    {"name": "SubscribeEvents", "input_type": "SubscribeEventsRequest", "output_type": "SubscribeEventsResponse", "streaming": "server"},
                    {"name": "ListNamespaces", "input_type": "ListNamespacesRequest", "output_type": "ListNamespacesResponse", "streaming": "unary"},
                    {"name": "GetNamespace", "input_type": "GetNamespaceRequest", "output_type": "GetNamespaceResponse", "streaming": "unary"},
                    {"name": "VerifyAsset", "input_type": "VerifyAssetRequest", "output_type": "VerifyAssetResponse", "streaming": "unary"},
                    {"name": "VerifySnapshot", "input_type": "VerifySnapshotRequest", "output_type": "VerifySnapshotResponse", "streaming": "unary"}
                ],
                "aifs.v1.Health": [
                    {"name": "Check", "input_type": "HealthCheckRequest", "output_type": "HealthCheckResponse", "streaming": "unary"}
                ],
                "aifs.v1.Introspect": [
                    {"name": "GetInfo", "input_type": "IntrospectRequest", "output_type": "IntrospectResponse", "streaming": "unary"}
                ],
                "aifs.v1.Admin": [
                    {"name": "CreateNamespace", "input_type": "CreateNamespaceRequest", "output_type": "CreateNamespaceResponse", "streaming": "unary"},
                    {"name": "PruneSnapshot", "input_type": "PruneSnapshotRequest", "output_type": "PruneSnapshotResponse", "streaming": "unary"},
                    {"name": "ManagePolicy", "input_type": "ManagePolicyRequest", "output_type": "ManagePolicyResponse", "streaming": "unary"}
                ],
                "aifs.v1.Metrics": [
                    {"name": "GetMetrics", "input_type": "MetricsRequest", "output_type": "MetricsResponse", "streaming": "unary"}
                ],
                "aifs.v1.Format": [
                    {"name": "FormatStorage", "input_type": "FormatRequest", "output_type": "FormatResponse", "streaming": "unary"}
                ]
            }
            
            return jsonify({"methods": methods.get(service_name, [])})
        
        @self.app.route('/api/call', methods=['POST'])
        def call_method():
            """Call a gRPC method."""
            try:
                data = request.json
                service_name = data.get('service')
                method_name = data.get('method')
                request_data = data.get('request', {})
                auth_token = data.get('auth_token')
                
                # Create metadata with auth token if provided
                metadata = []
                if auth_token:
                    metadata.append(('authorization', f'Bearer {auth_token}'))
                
                # Get the appropriate stub
                if service_name == "aifs.v1.AIFS":
                    stub = self.aifs_stub
                elif service_name == "aifs.v1.Health":
                    stub = self.health_stub
                elif service_name == "aifs.v1.Introspect":
                    stub = self.introspect_stub
                else:
                    return jsonify({"error": f"Unknown service: {service_name}"}), 400
                
                # Get the method
                method = getattr(stub, method_name)
                
                # Create request object
                if method_name == "PutAsset":
                    # Special handling for streaming
                    request_obj = aifs_pb2.PutAssetRequest()
                    if 'kind' in request_data:
                        request_obj.kind = getattr(aifs_pb2.AssetKind, request_data['kind'])
                    if 'metadata' in request_data:
                        request_obj.metadata.update(request_data['metadata'])
                    if 'chunks' in request_data:
                        for chunk_data in request_data['chunks']:
                            chunk = request_obj.chunks.add()
                            chunk.data = base64.b64decode(chunk_data)
                    
                    # Call streaming method
                    response = method(iter([request_obj]), metadata=metadata)
                else:
                    # Create request object dynamically
                    request_class = getattr(aifs_pb2, data.get('request_type', f'{method_name}Request'))
                    request_obj = request_class()
                    
                    # Fill request object
                    for key, value in request_data.items():
                        if hasattr(request_obj, key):
                            if key == 'kind' and hasattr(aifs_pb2.AssetKind, value):
                                setattr(request_obj, key, getattr(aifs_pb2.AssetKind, value))
                            elif key == 'metadata' and isinstance(value, dict):
                                getattr(request_obj, key).update(value)
                            elif key == 'parents' and isinstance(value, list):
                                for parent_data in value:
                                    parent = getattr(request_obj, key).add()
                                    for pkey, pvalue in parent_data.items():
                                        if hasattr(parent, pkey):
                                            setattr(parent, pkey, pvalue)
                            else:
                                setattr(request_obj, key, value)
                    
                    # Call method
                    response = method(request_obj, metadata=metadata)
                
                # Convert response to dict
                response_dict = {}
                for field in response.DESCRIPTOR.fields:
                    value = getattr(response, field.name)
                    if field.type == field.TYPE_MESSAGE:
                        if field.label == field.LABEL_REPEATED:
                            response_dict[field.name] = [self._message_to_dict(item) for item in value]
                        else:
                            response_dict[field.name] = self._message_to_dict(value)
                    elif field.type == field.TYPE_BYTES:
                        response_dict[field.name] = base64.b64encode(value).decode('utf-8')
                    else:
                        response_dict[field.name] = value
                
                return jsonify({"response": response_dict})
                
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/api/examples/<method_name>')
        def get_examples(method_name: str):
            """Get example requests for a method."""
            examples = {
                "PutAsset": {
                    "kind": "BLOB",
                    "metadata": {
                        "description": "Example asset",
                        "author": "user@example.com"
                    },
                    "chunks": [
                        base64.b64encode(b"Hello, AIFS!").decode('utf-8')
                    ]
                },
                "GetAsset": {
                    "asset_id": "your_asset_id_here",
                    "include_data": True
                },
                "ListAssets": {
                    "limit": 10,
                    "offset": 0
                },
                "VectorSearch": {
                    "query_embedding": base64.b64encode(b"dummy_embedding_data").decode('utf-8'),
                    "k": 5,
                    "filter": {
                        "kind": "BLOB"
                    }
                },
                "CreateSnapshot": {
                    "namespace": "default",
                    "asset_ids": ["asset1", "asset2"],
                    "metadata": {
                        "description": "Example snapshot"
                    }
                }
            }
            
            return jsonify({"example": examples.get(method_name, {})})
    
    def _message_to_dict(self, message) -> Dict[str, Any]:
        """Convert protobuf message to dictionary."""
        result = {}
        for field in message.DESCRIPTOR.fields:
            value = getattr(message, field.name)
            if field.type == field.TYPE_MESSAGE:
                if field.label == field.LABEL_REPEATED:
                    result[field.name] = [self._message_to_dict(item) for item in value]
                else:
                    result[field.name] = self._message_to_dict(value)
            elif field.type == field.TYPE_BYTES:
                result[field.name] = base64.b64encode(value).decode('utf-8')
            else:
                result[field.name] = value
        return result
    
    def run(self, host: str = "0.0.0.0", port: int = 8080, debug: bool = False):
        """Run the web UI."""
        print(f"🚀 Starting AIFS gRPC Web UI on http://{host}:{port}")
        print(f"📡 Connected to gRPC server at {self.server_host}:{self.server_port}")
        self.app.run(host=host, port=port, debug=debug)


def create_html_template():
    """Create the HTML template for the web UI."""
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIFS gRPC API Explorer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .service-section { margin-bottom: 30px; border: 1px solid #ddd; border-radius: 5px; }
        .service-header { background: #f8f9fa; padding: 15px; border-bottom: 1px solid #ddd; cursor: pointer; }
        .service-content { padding: 20px; display: none; }
        .method { margin-bottom: 20px; padding: 15px; border: 1px solid #eee; border-radius: 5px; }
        .method-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .method-name { font-weight: bold; color: #2c3e50; }
        .method-type { background: #3498db; color: white; padding: 2px 8px; border-radius: 3px; font-size: 12px; }
        .request-form { margin-top: 15px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 3px; }
        .form-group textarea { height: 100px; font-family: monospace; }
        .btn { background: #3498db; color: white; padding: 10px 20px; border: none; border-radius: 3px; cursor: pointer; }
        .btn:hover { background: #2980b9; }
        .response { margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 3px; }
        .response pre { margin: 0; white-space: pre-wrap; }
        .error { color: #e74c3c; }
        .success { color: #27ae60; }
        .loading { color: #f39c12; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 AIFS gRPC API Explorer</h1>
            <p>Interactive API testing and exploration tool</p>
        </div>
        
        <div id="services-container">
            <div class="loading">Loading services...</div>
        </div>
    </div>

    <script>
        let services = [];
        let methods = {};

        // Load services
        async function loadServices() {
            try {
                const response = await fetch('/api/services');
                const data = await response.json();
                services = data.services;
                renderServices();
            } catch (error) {
                document.getElementById('services-container').innerHTML = '<div class="error">Failed to load services: ' + error.message + '</div>';
            }
        }

        // Render services
        function renderServices() {
            const container = document.getElementById('services-container');
            container.innerHTML = '';

            services.forEach(service => {
                const serviceDiv = document.createElement('div');
                serviceDiv.className = 'service-section';
                serviceDiv.innerHTML = `
                    <div class="service-header" onclick="toggleService('${service}')">
                        <h3>${service}</h3>
                        <span>▼</span>
                    </div>
                    <div class="service-content" id="content-${service}">
                        <div class="loading">Loading methods...</div>
                    </div>
                `;
                container.appendChild(serviceDiv);
                loadMethods(service);
            });
        }

        // Toggle service visibility
        function toggleService(service) {
            const content = document.getElementById(`content-${service}`);
            const header = content.previousElementSibling;
            const arrow = header.querySelector('span');
            
            if (content.style.display === 'none') {
                content.style.display = 'block';
                arrow.textContent = '▼';
            } else {
                content.style.display = 'none';
                arrow.textContent = '▶';
            }
        }

        // Load methods for a service
        async function loadMethods(service) {
            try {
                const response = await fetch(`/api/methods/${service}`);
                const data = await response.json();
                methods[service] = data.methods;
                renderMethods(service, data.methods);
            } catch (error) {
                document.getElementById(`content-${service}`).innerHTML = '<div class="error">Failed to load methods: ' + error.message + '</div>';
            }
        }

        // Render methods for a service
        function renderMethods(service, methods) {
            const content = document.getElementById(`content-${service}`);
            content.innerHTML = '';

            methods.forEach(method => {
                const methodDiv = document.createElement('div');
                methodDiv.className = 'method';
                methodDiv.innerHTML = `
                    <div class="method-header">
                        <span class="method-name">${method.name}</span>
                        <span class="method-type">${method.streaming}</span>
                    </div>
                    <div class="request-form">
                        <div class="form-group">
                            <label>Request JSON:</label>
                            <textarea id="request-${service}-${method.name}" placeholder='{"key": "value"}'></textarea>
                        </div>
                        <div class="form-group">
                            <label>Auth Token (optional):</label>
                            <input type="text" id="auth-${service}-${method.name}" placeholder="Bearer token">
                        </div>
                        <button class="btn" onclick="callMethod('${service}', '${method.name}')">Call Method</button>
                        <button class="btn" onclick="loadExample('${service}', '${method.name}')" style="background: #95a5a6;">Load Example</button>
                    </div>
                    <div id="response-${service}-${method.name}" class="response" style="display: none;"></div>
                `;
                content.appendChild(methodDiv);
            });
        }

        // Load example request
        async function loadExample(service, method) {
            try {
                const response = await fetch(`/api/examples/${method}`);
                const data = await response.json();
                const textarea = document.getElementById(`request-${service}-${method}`);
                textarea.value = JSON.stringify(data.example, null, 2);
            } catch (error) {
                console.error('Failed to load example:', error);
            }
        }

        // Call a gRPC method
        async function callMethod(service, method) {
            const requestText = document.getElementById(`request-${service}-${method}`).value;
            const authToken = document.getElementById(`auth-${service}-${method}`).value;
            const responseDiv = document.getElementById(`response-${service}-${method}`);
            
            responseDiv.style.display = 'block';
            responseDiv.innerHTML = '<div class="loading">Calling method...</div>';

            try {
                let requestData = {};
                if (requestText.trim()) {
                    requestData = JSON.parse(requestText);
                }

                const response = await fetch('/api/call', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        service: service,
                        method: method,
                        request: requestData,
                        auth_token: authToken
                    })
                });

                const data = await response.json();
                
                if (response.ok) {
                    responseDiv.innerHTML = `
                        <div class="success">✅ Success</div>
                        <pre>${JSON.stringify(data.response, null, 2)}</pre>
                    `;
                } else {
                    responseDiv.innerHTML = `
                        <div class="error">❌ Error: ${data.error}</div>
                    `;
                }
            } catch (error) {
                responseDiv.innerHTML = `
                    <div class="error">❌ Error: ${error.message}</div>
                `;
            }
        }

        // Initialize
        loadServices();
    </script>
</body>
</html>
    """
    
    with open(os.path.join(template_dir, 'grpc_ui.html'), 'w') as f:
        f.write(html_content)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AIFS gRPC Web UI")
    parser.add_argument("--server-host", default="localhost", help="gRPC server host")
    parser.add_argument("--server-port", type=int, default=50051, help="gRPC server port")
    parser.add_argument("--host", default="0.0.0.0", help="Web UI host")
    parser.add_argument("--port", type=int, default=8080, help="Web UI port")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    # Create HTML template
    create_html_template()
    
    # Start web UI
    ui = GRPCWebUI(args.server_host, args.server_port)
    ui.run(args.host, args.port, args.debug)


if __name__ == "__main__":
    main()
