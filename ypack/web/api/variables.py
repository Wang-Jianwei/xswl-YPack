"""
Variables API endpoints.

Provides built-in variable definitions for the frontend.
"""

from flask import Blueprint, jsonify
from ypack.variables import VariableRegistry

bp = Blueprint('variables', __name__, url_prefix='/api/variables')


@bp.route('/builtin', methods=['GET'])
def get_builtin_variables():
    """
    Get all built-in variables.
    
    Response:
        {
            "variables": [
                {
                    "name": "$INSTDIR",
                    "description": "Installation directory",
                    "example": "C:\\Program Files\\MyApp"
                },
                ...
            ]
        }
    """
    registry = VariableRegistry()
    
    variables = []
    for var_name, var_def in registry.variables.items():
        variables.append({
            'name': var_name,
            'description': var_def.description,
            'example': var_def.fallback or ''
        })
    
    return jsonify({'variables': variables})
