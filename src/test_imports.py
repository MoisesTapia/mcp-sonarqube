#!/usr/bin/env python3
"""
Script para probar las importaciones de las herramientas MCP.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test importing MCP tools."""
    print("🔍 Probando importaciones de herramientas MCP...")
    
    try:
        print("1. Importando ProjectTools...")
        from mcp_server.tools.projects import ProjectTools
        print("   ✅ ProjectTools importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando ProjectTools: {e}")
    
    try:
        print("2. Importando MeasureTools...")
        from mcp_server.tools.measures import MeasureTools
        print("   ✅ MeasureTools importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando MeasureTools: {e}")
    
    try:
        print("3. Importando SecurityTools...")
        from mcp_server.tools.security import SecurityTools
        print("   ✅ SecurityTools importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando SecurityTools: {e}")
    
    try:
        print("4. Importando IssueTools...")
        from mcp_server.tools.issues import IssueTools
        print("   ✅ IssueTools importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando IssueTools: {e}")
    
    try:
        print("5. Importando QualityGateTools...")
        from mcp_server.tools.quality_gates import QualityGateTools
        print("   ✅ QualityGateTools importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando QualityGateTools: {e}")
    
    try:
        print("6. Importando SonarQubeClient...")
        from sonarqube_client import SonarQubeClient
        print("   ✅ SonarQubeClient importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando SonarQubeClient: {e}")
    
    try:
        print("7. Importando utils...")
        from utils import get_logger
        print("   ✅ utils importado correctamente")
    except Exception as e:
        print(f"   ❌ Error importando utils: {e}")
    
    try:
        print("8. Probando FastMCP...")
        from fastmcp import FastMCP
        app = FastMCP("Test")
        print("   ✅ FastMCP funciona correctamente")
        
        # Test registering a simple tool
        @app.tool()
        async def test_tool() -> str:
            """Test tool."""
            return "Hello from test tool"
        
        print("   ✅ Herramienta de prueba registrada")
        
        # Check if tools are stored
        print(f"   🔍 Atributos de FastMCP: {[attr for attr in dir(app) if not attr.startswith('__')]}")
        
        # Try to find where tools are stored
        for attr_name in ['_tools', 'tools', '_tool_registry', 'tool_registry', '_handlers', 'handlers']:
            if hasattr(app, attr_name):
                attr_value = getattr(app, attr_name)
                print(f"   📋 {attr_name}: {type(attr_value)} - {attr_value}")
        
    except Exception as e:
        print(f"   ❌ Error con FastMCP: {e}")

if __name__ == "__main__":
    test_imports()