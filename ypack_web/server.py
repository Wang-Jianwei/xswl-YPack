"""
YPack Web UI Server.

Flask application providing REST API and serving the frontend.
"""

import os
from flask import Flask, send_from_directory
from flask_cors import CORS

from ypack_web.api import schema, validate, project, variables


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                static_folder='static',
                static_url_path='')
    
    # Enable CORS for development
    CORS(app)
    
    # Load config
    if test_config is None:
        app.config.from_mapping(
            SECRET_KEY='dev',
            JSON_AS_ASCII=False,  # Support Unicode in JSON responses
            JSON_SORT_KEYS=False,  # Preserve key order
        )
    else:
        app.config.from_mapping(test_config)
    
    # Register blueprints
    app.register_blueprint(schema.bp)
    app.register_blueprint(validate.bp)
    app.register_blueprint(project.bp)
    app.register_blueprint(variables.bp)
    
    # Serve frontend
    @app.route('/')
    def index():
        return send_from_directory(app.static_folder, 'index.html')
    
    # Health check
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'version': '0.1.0'}
    
    return app


def main():
    """Start the development server."""
    import argparse
    
    parser = argparse.ArgumentParser(description='YPack Web UI Server')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Host to bind to (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to bind to (default: 5000)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode')
    
    args = parser.parse_args()
    
    app = create_app()
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║              YPack Web UI Server v0.1.0                   ║
╚═══════════════════════════════════════════════════════════╝

🚀 Server running at: http://{args.host}:{args.port}

📝 API Endpoints:
   GET  /api/health              - Health check
   GET  /api/schema              - JSON Schema
   GET  /api/schema/enums        - Enum values
   POST /api/validate/yaml       - Validate YAML
   POST /api/validate/config     - Validate config dict
   POST /api/project/new         - New project
   POST /api/project/load        - Load from YAML
   POST /api/project/save        - Save to YAML
   GET  /api/variables/builtin   - Built-in variables

Press Ctrl+C to stop the server.
""")
    
    app.run(
        host=args.host,
        port=args.port,
        debug=args.debug
    )


if __name__ == '__main__':
    main()
