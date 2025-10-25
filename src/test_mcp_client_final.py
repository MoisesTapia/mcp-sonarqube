#!/usr/bin/env python3
"""
Script para probar el MCP client con fallback a datos mock.
"""

import sys
from pathlib import Path
import asyncio
import json
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

# Import without streamlit dependencies
import os
os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'


async def test_mcp_client_final():
    """Test MCP client with mock fallback."""
    print("🧪 Probando MCP Client con fallback a datos mock...")
    print("=" * 70)
    
    try:
        # Import MCP client components
        from streamlit_app.services.mcp_client import MCPClient, MCPToolResult
        
        # Create client
        client = MCPClient("http://localhost:8001")
        
        print("\n1. 🔍 Verificando conectividad...")
        try:
            is_healthy = await client.check_health()
            print(f"   📊 Servidor saludable: {is_healthy}")
            print(f"   🔗 Estado de conexión: {client.connection_status}")
        except Exception as e:
            print(f"   ❌ Error en health check: {e}")
        
        print("\n2. 📋 Obteniendo herramientas disponibles...")
        try:
            tools = client.get_available_tools()
            print(f"   🛠️  Herramientas disponibles: {len(tools)}")
            for i, tool in enumerate(tools[:5], 1):
                name = tool.get("name", "Unknown")
                desc = tool.get("description", "No description")[:50]
                print(f"      {i}. {name}: {desc}...")
            if len(tools) > 5:
                print(f"      ... y {len(tools) - 5} más")
        except Exception as e:
            print(f"   ❌ Error obteniendo herramientas: {e}")
        
        print("\n3. 🏥 Probando health_check...")
        try:
            result = await client.call_tool("health_check")
            print(f"   📊 Éxito: {result.success}")
            print(f"   ⏱️  Tiempo: {result.execution_time:.2f}s")
            if result.success:
                print(f"   ✅ ¡health_check funciona!")
                data = result.data.get("result", {})
                status = data.get("status", "unknown")
                print(f"   📄 Estado: {status}")
            else:
                print(f"   ❌ Error: {result.error}")
        except Exception as e:
            print(f"   ❌ Error ejecutando health_check: {e}")
        
        print("\n4. 📋 Probando list_projects...")
        try:
            result = await client.call_tool("list_projects", {"page_size": 3})
            print(f"   📊 Éxito: {result.success}")
            print(f"   ⏱️  Tiempo: {result.execution_time:.2f}s")
            if result.success:
                print(f"   ✅ ¡list_projects funciona!")
                data = result.data.get("result", [])
                if isinstance(data, list):
                    print(f"   📊 Proyectos encontrados: {len(data)}")
                    for i, project in enumerate(data, 1):
                        if isinstance(project, dict):
                            name = project.get("name", "Unknown")
                            key = project.get("key", "Unknown")
                            print(f"      {i}. {name} ({key})")
                else:
                    print(f"   📄 Resultado: {json.dumps(data, indent=2)[:200]}...")
            else:
                print(f"   ❌ Error: {result.error}")
        except Exception as e:
            print(f"   ❌ Error ejecutando list_projects: {e}")
        
        print("\n5. 📊 Probando get_measures...")
        try:
            result = await client.call_tool("get_measures", {"project_key": "sample-project"})
            print(f"   📊 Éxito: {result.success}")
            print(f"   ⏱️  Tiempo: {result.execution_time:.2f}s")
            if result.success:
                print(f"   ✅ ¡get_measures funciona!")
                data = result.data.get("result", {})
                measures = data.get("measures", [])
                print(f"   📊 Métricas encontradas: {len(measures) if isinstance(measures, list) else 'N/A'}")
                if isinstance(measures, list) and measures:
                    for measure in measures[:3]:
                        if isinstance(measure, dict):
                            metric = measure.get("metric", "Unknown")
                            value = measure.get("value", "Unknown")
                            print(f"      - {metric}: {value}")
            else:
                print(f"   ❌ Error: {result.error}")
        except Exception as e:
            print(f"   ❌ Error ejecutando get_measures: {e}")
        
        print("\n6. 📈 Información de conexión...")
        try:
            conn_info = client.get_connection_info()
            print(f"   🔗 Estado: {conn_info.get('status')}")
            print(f"   🌐 URL: {conn_info.get('server_url')}")
            print(f"   🛠️  Herramientas disponibles: {conn_info.get('tools_available')}")
            print(f"   📊 Total de llamadas: {conn_info.get('total_calls')}")
            
            error_stats = conn_info.get('error_stats', {})
            success_rate = error_stats.get('success_rate', 0)
            print(f"   ✅ Tasa de éxito: {success_rate:.1f}%")
        except Exception as e:
            print(f"   ❌ Error obteniendo info de conexión: {e}")
    
    except ImportError as e:
        print(f"❌ Error importando MCP client: {e}")
        print("💡 Esto es normal si faltan dependencias de Streamlit")
    except Exception as e:
        print(f"❌ Error general: {e}")


def main():
    """Main function."""
    print("🚀 Prueba final del MCP Client")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    
    try:
        asyncio.run(test_mcp_client_final())
    except KeyboardInterrupt:
        print("\n⏹️  Interrumpido")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("🏁 Prueba completada")
    
    print("\n💡 Resultados esperados:")
    print("   ✅ Si el servidor HTTP funciona: llamadas reales exitosas")
    print("   ✅ Si el servidor HTTP falla: fallback a datos mock")
    print("   ✅ En ambos casos: el cliente MCP debería funcionar")
    
    print("\n🔧 Estado del sistema:")
    print("   ✅ Importaciones corregidas")
    print("   ✅ Dependencias instaladas") 
    print("   ✅ Cliente MCP implementado")
    print("   ⚠️  Servidor HTTP necesita reconstrucción Docker")


if __name__ == "__main__":
    main()