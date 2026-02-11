"""
Project management API endpoints.

Handles loading, saving, and converting between YAML and JSON.
"""

try:
    from flask import Blueprint, request, jsonify
except Exception:
    # Allow importing this module in test environments without Flask installed.
    class _StubBlueprint:
        def route(self, *args, **kwargs):
            def _dec(f):
                return f
            return _dec

    Blueprint = lambda *args, **kwargs: _StubBlueprint()
    request = None

    def jsonify(x, **kwargs):
        return x
import yaml
from typing import Any, Dict

from ypack.config import PackageConfig
from ypack.converters.nsis_sections import _should_use_recursive

bp = Blueprint('project', __name__, url_prefix='/api/project')


def config_to_dict(config: PackageConfig) -> Dict[str, Any]:
    """
    Convert PackageConfig to a dictionary suitable for JSON serialization.
    """
    if config._raw_dict:
        # If the raw dict is present (config was constructed from user YAML),
        # return a *copy* augmented with any UI-friendly flags (currently
        # `recursive` for file entries detected from source patterns).
        import copy
        raw = copy.deepcopy(config._raw_dict)
        files_raw = raw.get('files', [])
        files_out = []
        for item in files_raw:
            # Normalise many accepted input shapes into a dict form
            if isinstance(item, str):
                src = item
                dst = "$INSTDIR"
                out_item = {"source": src, "destination": dst}
            elif isinstance(item, dict):
                src = item.get("source", "")
                dst = item.get("destination", "$INSTDIR")
                out_item = {k: v for k, v in item.items() if k != "source" and k != "destination"}
                out_item["source"] = src
                out_item["destination"] = dst
            else:
                src = str(item)
                out_item = {"source": src, "destination": "$INSTDIR"}

            if isinstance(src, str) and _should_use_recursive(src):
                out_item["recursive"] = True
            files_out.append(out_item)
        raw['files'] = files_out
        return raw
    
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
            # Detect recursive source patterns ("**") and expose a `recursive` flag
            # to the UI so it can render directory-copy semantics.
            if isinstance(f.source, str) and _should_use_recursive(f.source):
                result['files'].append({
                    'source': f.source,
                    'destination': f.destination,
                    'recursive': True,
                })
            else:
                result['files'].append({
                    'source': f.source,
                    'destination': f.destination,
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


@bp.route('/convert', methods=['POST'])
def convert_project():
    """Convert configuration to an installer script (e.g. NSIS).

    Accepts either a full `config` dict or raw `yaml_content`. Optional
    parameter `format` selects the target backend (default: "nsis").
    """
    data = request.get_json() or {}
    fmt = data.get('format', 'nsis')
    yaml_content = data.get('yaml_content')
    config_dict = None

    if yaml_content:
        try:
            config_dict = yaml.safe_load(yaml_content)
            if config_dict is None:
                return jsonify({'script': '', 'error': 'YAML is empty'}), 400
        except yaml.YAMLError as e:
            return jsonify({'script': '', 'error': f'YAML syntax error: {str(e)}'}), 400
    else:
        config_dict = data.get('config', {})

    if not config_dict:
        return jsonify({'script': '', 'error': 'Empty configuration'}), 400

    try:
        # Build a PackageConfig to ensure the config is valid
        pkg = PackageConfig.from_dict(config_dict)
    except Exception as e:
        return jsonify({'script': '', 'error': f'Config error: {str(e)}'}), 400

    # Perform conversion using the registered converter for the format
    try:
        from ypack.converters import get_converter_class

        Converter = get_converter_class(fmt)
        converter = Converter(pkg, config_dict)
        script = converter.convert()
        return jsonify({'script': script, 'format': fmt})
    except ValueError as e:
        return jsonify({'script': '', 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'script': '', 'error': f'Conversion error: {str(e)}'}), 500