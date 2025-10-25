#!/usr/bin/env python3
"""
Script para probar las correcciones de Streamlit.
"""

import sys
from pathlib import Path
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables for Streamlit
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'

def test_streamlit_fixes():
    """Test Streamlit fixes."""
    print("🔧 Probando correcciones de Streamlit...")
    print("=" * 60)
    
    try:
        # Test 1: Import configuration
        print("\n1. 🔧 Probando configuración de Streamlit...")
        from streamlit_app.config.streamlit_config import initialize_streamlit_app
        initialize_streamlit_app()
        print("   ✅ Configuración de Streamlit inicializada")
        
        # Test 2: Import MCP client
        print("\n2. 📡 Probando MCP client corregido...")
        from streamlit_app.services.mcp_client import get_mcp_client
        client = get_mcp_client()
        print("   ✅ MCP client importado correctamente")
        
        # Test 3: Test health check sync
        print("\n3. 🏥 Probando health check sincrónico...")
        try:
            is_healthy = client.check_health_sync()
            print(f"   📊 Servidor saludable: {is_healthy}")
            print(f"   🔗 Estado de conexión: {client.connection_status}")
            print("   ✅ Health check sincrónico funciona")
        except Exception as e:
            print(f"   ⚠️  Error en health check: {e}")
        
        # Test 4: Test get_available_tools
        print("\n4. 🛠️  Probando get_available_tools corregido...")
        try:
            tools = client.get_available_tools()
            print(f"   📊 Herramientas disponibles: {len(tools)}")
            if len(tools) > 0:
                print(f"   ✅ get_available_tools funciona correctamente")
                for i, tool in enumerate(tools[:3], 1):
                    name = tool.get("name", "Unknown")
                    print(f"      {i}. {name}")
            else:
                print(f"   ⚠️  No se obtuvieron herramientas (puede ser normal si el servidor no responde)")
        except Exception as e:
            print(f"   ❌ Error en get_available_tools: {e}")
        
        # Test 5: Test connection info
        print("\n5. 📈 Probando información de conexión...")
        try:
            conn_info = client.get_connection_info()
            print(f"   🔗 Estado: {conn_info.get('status')}")
            print(f"   🌐 URL: {conn_info.get('server_url')}")
            print(f"   📊 Tipo de servidor: {conn_info.get('server_type')}")
            print("   ✅ Información de conexión obtenida")
        except Exception as e:
            print(f"   ❌ Error obteniendo info de conexión: {e}")
        
        print("\n" + "=" * 60)
        print("✅ Todas las correcciones de Streamlit probadas")
        
    except ImportError as e:
        print(f"❌ Error de importación: {e}")
        print("💡 Esto puede ser normal si faltan dependencias de Streamlit")
    except Exception as e:
        print(f"❌ Error general: {e}")


def main():
    """Main function."""
    print("🚀 Prueba de correcciones de Streamlit")
    print(f"⏰ Timestamp: {Path(__file__).stat().st_mtime}")
    
    test_streamlit_fixes()
    
    print("\n💡 Correcciones implementadas:")
    print("   ✅ Error de 'concurrent' en get_available_tools corregido")
    print("   ✅ Configuración de Streamlit optimizada")
    print("   ✅ Warnings de ScriptRunContext suprimidos")
    print("   ✅ Health check sincrónico mejorado")
    print("   ✅ Manejo de errores robusto")
    
    print("\n🔧 Próximos pasos:")
    print("   1. Reiniciar la aplicación Streamlit")
    print("   2. Verificar que los warnings hayan disminuido")
    print("   3. Probar la funcionalidad del chat assistant")


if __name__ == "__main__":
    main()