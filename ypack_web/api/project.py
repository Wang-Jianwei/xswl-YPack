"""
Project management API endpoints.

Handles loading, saving, and converting between YAML and JSON.
"""

from flask import Blueprint, request, jsonify
import yaml
from typing import Any, Dict

from ypack.config import PackageConfig

bp = Blueprint('project', __name__, url_prefix='/api/project')


def config_to_dict(config: PackageConfig) -> Dict[str, Any]:
    """
    Convert PackageConfig to a dictionary suitable for JSON serialization.
    """
    if config._raw_dict:
        return config._raw_dict
    
    result = {
        'app': {
            'name': config.app.name,
            'version': config.app.version,
            'publisher': config.app.publisher,
            'description': config.app.description,
            'install_icon': config.app.install_icon,
            'uninstall_icon': config.app.uninstall_icon,
            'license': config.app.license,
        },
        'install': {}
    }
    
    if config.files:
        result['files'] = []
        for f in config.files:
            if isinstance(f.source, str) and f.destination == "$INSTDIR" and not f.recursive:
                result['files'].append(f.source)
            else:
                result['files'].append({
                    'source': f.source,
                    'destination': f.destination,
                    'recursive': f.recursive
                })
    
    return result


@bp.route('/new', methods=['POST'])
def new_project():
    data = request.get_json() or {}
    name = data.get('name', 'MyApp')
    
    config_dict = {
        'app': {
            'name': name,
            'version': '1.0.0',
            'publisher': '',
            'description': '',
        },
        'install': {
            'install_dir': f'$PROGRAMFILES64\\{name}',
        }
    }
    
    return jsonify({'config': config_dict})


@bp.route('/load', methods=['POST'])
def load_project():
    data = request.get_json()
    yaml_content = data.get('yaml_content', '')
    
    if not yaml_content:
        return jsonify({
            'config': {},
            'valid': False,
            'errors': [{'message': 'Empty YAML content'}]
        }), 400
    
    try:
        config_dict = yaml.safe_load(yaml_content)
        
        if config_dict is None:
            return jsonify({
                'config': {},
                'valid': False,
                'errors': [{'message': 'YAML is empty'}]
            }), 400
        
        config = PackageConfig.from_dict(config_dict)
        
        return jsonify({
            'config': config_dict,
            'valid': True,
            'errors': []
        })
        
    except yaml.YAMLError as e:
        return jsonify({
            'config': {},
            'valid': False,
            'errors': [{
                'message': f'YAML syntax error: {str(e)}'
            }]
        }), 400
    except Exception as e:
        return jsonify({
            'config': {},
            'valid': False,
            'errors': [{
                'message': f'Error loading project: {str(e)}'
            }]
        }), 400


@bp.route('/save', methods=['POST'])
def save_project():
    data = request.get_json()
    config = data.get('config', {})
    
    if not config:
        return jsonify({
            'yaml_content': '',
            'error': 'Empty configuration'
        }), 400
    
    try:
        yaml_content = yaml.dump(
            config,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
            indent=2
        )
        
        return jsonify({
            'yaml_content': yaml_content
        })
        
    except Exception as e:
        return jsonify({
            'yaml_content': '',
            'error': f'Error converting to YAML: {str(e)}'
        }), 500