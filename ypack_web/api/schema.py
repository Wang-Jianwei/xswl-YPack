"""
Schema API endpoints.

Provides JSON Schema and enum values for frontend validation.
"""

from flask import Blueprint, jsonify
from ypack.schema import CONFIG_SCHEMA

bp = Blueprint('schema', __name__, url_prefix='/api/schema')


@bp.route('', methods=['GET'])
def get_schema():
    """Get the complete JSON Schema for YAML configuration."""
    return jsonify(CONFIG_SCHEMA)


@bp.route('/enums', methods=['GET'])
def get_enums():
    """Get all enum values for dropdown selections."""
    enums = {
        'registry_hive': ['HKLM', 'HKCU', 'HKCR', 'HKU', 'HKCC'],
        'registry_type': ['string', 'expand', 'dword'],
        'registry_view': ['auto', '32', '64'],
        'env_scope': ['system', 'user'],
        'existing_install_mode': [
            'prompt_uninstall',
            'auto_uninstall',
            'overwrite',
            'abort',
            'none'
        ],
        'log_level': ['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        'languages': [
            'English',
            'French',
            'German',
            'Spanish',
            'Portuguese',
            'BrazilianPortuguese',
            'Russian',
            'Polish',
            'Czech',
            'Hungarian',
            'Turkish',
            'SimplifiedChinese',
            'TraditionalChinese',
            'Japanese',
            'Korean'
        ]
    }
    return jsonify(enums)
