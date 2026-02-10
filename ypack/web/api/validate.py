"""
Validation API endpoints.

Validates YAML content and configuration structures.
"""

from flask import Blueprint, request, jsonify
import yaml
from jsonschema import ValidationError

from ypack.schema import validate_config

bp = Blueprint('validate', __name__, url_prefix='/api/validate')


@bp.route('/yaml', methods=['POST'])
def validate_yaml():
    """
    Validate YAML syntax and structure.
    
    Request:
        {
            "yaml_content": "app:\\n  name: MyApp\\n  ..."
        }
    
    Response:
        {
            "valid": true/false,
            "errors": [
                {
                    "line": 10,
                    "column": 5,
                    "message": "Invalid field 'xyz'",
                    "path": "install.registry_entries[0].hive"
                }
            ]
        }
    """
    data = request.get_json()
    yaml_content = data.get('yaml_content', '')
    
    if not yaml_content:
        return jsonify({
            'valid': False,
            'errors': [{
                'line': 1,
                'column': 1,
                'message': 'Empty YAML content',
                'path': ''
            }]
        })
    
    errors = []
    
    # Step 1: Parse YAML syntax
    try:
        config_dict = yaml.safe_load(yaml_content)
        if config_dict is None:
            return jsonify({
                'valid': False,
                'errors': [{
                    'line': 1,
                    'column': 1,
                    'message': 'YAML is empty or only contains comments',
                    'path': ''
                }]
            })
    except yaml.YAMLError as e:
        error_info = {
            'line': getattr(e, 'problem_mark', None).line + 1 if hasattr(e, 'problem_mark') else 1,
            'column': getattr(e, 'problem_mark', None).column + 1 if hasattr(e, 'problem_mark') else 1,
            'message': str(e),
            'path': ''
        }
        return jsonify({
            'valid': False,
            'errors': [error_info]
        })
    
    # Step 2: Validate against JSON Schema
    try:
        validate_config(config_dict)
        return jsonify({
            'valid': True,
            'errors': []
        })
    except ValidationError as e:
        # Extract validation error details
        path = '.'.join(str(p) for p in e.path) if e.path else ''
        error_info = {
            'line': 1,  # JSON Schema doesn't provide line numbers
            'column': 1,
            'message': e.message,
            'path': path
        }
        return jsonify({
            'valid': False,
            'errors': [error_info]
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [{
                'line': 1,
                'column': 1,
                'message': f'Validation error: {str(e)}',
                'path': ''
            }]
        })


@bp.route('/config', methods=['POST'])
def validate_config_endpoint():
    """
    Validate configuration dictionary.
    
    Request:
        {
            "config": {
                "app": {"name": "MyApp", "version": "1.0"},
                "install": {...}
            }
        }
    
    Response:
        {
            "valid": true/false,
            "errors": [...]
        }
    """
    data = request.get_json()
    config = data.get('config', {})
    
    if not config:
        return jsonify({
            'valid': False,
            'errors': [{
                'message': 'Empty configuration',
                'path': ''
            }]
        })
    
    try:
        validate_config(config)
        return jsonify({
            'valid': True,
            'errors': []
        })
    except ValidationError as e:
        path = '.'.join(str(p) for p in e.path) if e.path else ''
        return jsonify({
            'valid': False,
            'errors': [{
                'message': e.message,
                'path': path
            }]
        })
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [{
                'message': str(e),
                'path': ''
            }]
        })
