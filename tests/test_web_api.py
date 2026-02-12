"""
Test script for YPack Web UI API.
"""

import pytest
requests = pytest.importorskip("requests")
import json

BASE_URL = "http://127.0.0.1:5000"

def test_health():
    """Test health endpoint."""
    print("Testing /api/health...")
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.json()}")
    print()

def test_schema():
    """Test schema endpoint."""
    print("Testing /api/schema...")
    response = requests.get(f"{BASE_URL}/api/schema")
    print(f"  Status: {response.status_code}")
    schema = response.json()
    print(f"  Schema keys: {list(schema.keys())}")
    print()

def test_enums():
    """Test enums endpoint."""
    print("Testing /api/schema/enums...")
    response = requests.get(f"{BASE_URL}/api/schema/enums")
    print(f"  Status: {response.status_code}")
    enums = response.json()
    print(f"  Available enums: {list(enums.keys())}")
    print()

def test_new_project():
    """Test new project creation."""
    print("Testing /api/project/new...")
    response = requests.post(
        f"{BASE_URL}/api/project/new",
        json={"name": "TestApp"}
    )
    print(f"  Status: {response.status_code}")
    data = response.json()
    print(f"  App name: {data['config']['app']['name']}")
    print()

def test_validate_yaml():
    """Test YAML validation."""
    print("Testing /api/validate/yaml...")
    yaml_content = """
app:
  name: "TestApp"
  version: "1.0.0"
install:
  install_dir: "$PROGRAMFILES64\\TestApp"
"""
    response = requests.post(
        f"{BASE_URL}/api/validate/yaml",
        json={"yaml_content": yaml_content}
    )
    print(f"  Status: {response.status_code}")
    data = response.json()
    print(f"  Valid: {data['valid']}")
    print()

def test_save_load():
    """Test save and load project."""
    print("Testing /api/project/save + /api/project/load...")
    
    # Create config
    config = {
        "app": {
            "name": "MyApp",
            "version": "2.0.0",
            "publisher": "Test Co."
        },
        "install": {
            "install_dir": "$PROGRAMFILES64\\MyApp"
        },
        "files": ["MyApp.exe", "config.yaml"]
    }
    
    # Save to YAML
    response = requests.post(
        f"{BASE_URL}/api/project/save",
        json={"config": config}
    )
    print(f"  Save status: {response.status_code}")
    yaml_content = response.json()['yaml_content']
    print(f"  YAML length: {len(yaml_content)} chars")
    
    # Load back
    response = requests.post(
        f"{BASE_URL}/api/project/load",
        json={"yaml_content": yaml_content}
    )
    print(f"  Load status: {response.status_code}")
    loaded = response.json()
    print(f"  Loaded app name: {loaded['config']['app']['name']}")
    print()


def test_convert():
    """Test conversion endpoint (/api/project/convert)."""
    print("Testing /api/project/convert...")

    config = {
        "app": {
            "name": "MyApp",
            "version": "1.0.0",
            "publisher": "Test Co."
        },
        "install": {
            "install_dir": "$PROGRAMFILES64\\MyApp"
        },
        "files": ["MyApp.exe"]
    }

    response = requests.post(
        f"{BASE_URL}/api/project/convert",
        json={"config": config, "format": "nsis"}
    )
    print(f"  Status: {response.status_code}")
    assert response.status_code == 200
    data = response.json()
    script = data.get('script', '')
    print(f"  Script length: {len(script)} chars")
    assert script
    # Basic sanity checks for NSIS-like output
    assert '!define' in script or 'Name "' in script or 'OutFile' in script
    print()


def test_visual_persistence():
    """Test that visual components are persisted into YAML via /project/save and restored by /project/load."""
    print("Testing visual persistence: /api/project/save -> /api/project/load...")

    config = {
        "app": {"name": "MyApp", "version": "1.0.0", "publisher": "Test Co."},
        "install": {"install_dir": "$PROGRAMFILES64\\MyApp"},
        "files": ["MyApp.exe"],
        "visual": {
            "components": [
                {"type": "file", "props": {"source": "MyApp.exe"}}
            ]
        }
    }

    # Save to YAML
    response = requests.post(f"{BASE_URL}/api/project/save", json={"config": config})
    assert response.status_code == 200
    yaml_content = response.json().get('yaml_content', '')
    assert 'visual' in yaml_content

    # Load back
    response = requests.post(f"{BASE_URL}/api/project/load", json={"yaml_content": yaml_content})
    assert response.status_code == 200
    data = response.json()
    assert data.get('valid') is True
    loaded_config = data.get('config', {})
    assert 'visual' in loaded_config
    comps = loaded_config.get('visual', {}).get('components', [])
    assert len(comps) == 1
    assert comps[0]['type'] == 'file'
    assert comps[0]['props']['source'] == 'MyApp.exe'
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("YPack Web UI API Test Suite")
    print("=" * 60)
    print()
    
    try:
        test_health()
        test_schema()
        test_enums()
        test_new_project()
        test_validate_yaml()
        test_save_load()
        
        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
