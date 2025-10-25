#!/usr/bin/env python3
"""
Script para debuggear el registro de herramientas MCP.
"""

import asyncio
import json
from datetime import datetime


async def debug_mcp_registration():
    """Debug MCP tool registration."""
    try:
        import httpx
    except ImportError:
        print("❌ httpx no está instalado. Instala con: pip install httpx")
        return
    
    server_url = "http://localhost:8001"
    
    print("🔍 Debuggeando registro de herramientas MCP...")
    print(f"🌐 URL del servidor: {server_url}")
    print("=" * 80)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        
        # Test 1: Get detailed debug info
        print("\n1. 🔧 Obteniendo información detallada de debug...")
        try:
            response = await client.get(f"{server_url}/debug/mcp")
            print(f"   📊 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                debug_data = response.json()
                print(f"   ✅ Debug info obtenida")
                
                # Show FastMCP app info
                print(f"\n   📱 Información de FastMCP App:")
                print(f"      Tipo: {debug_data.get('app_type')}")
                print(f"      Existe: {debug_data.get('app_exists')}")
                
                # Show get_tools info
                if 'get_tools_count' in debug_data:
                    count = debug_data['get_tools_count']
                    keys = debug_data.get('get_tools_keys', [])
                    print(f"\n   🛠️  get_tools() resultado:")
                    print(f"      Cantidad: {count}")
                    if keys:
                        print(f"      Herramientas: {keys}")
                        print(f"   🎉 ¡HERRAMIENTAS ENCONTRADAS!")
                    else:
                        print(f"      ⚠️  Sin herramientas en get_tools()")
                elif 'get_tools_error' in debug_data:
                    print(f"\n   ❌ Error en get_tools(): {debug_data['get_tools_error']}")
                
                # Show tool manager info
                if 'tool_manager_info' in debug_data:
                    tm_info = debug_data['tool_manager_info']
                    print(f"\n   🔧 Información del Tool Manager:")
                    print(f"      Tipo: {tm_info.get('type')}")
                    
                    for attr in ['tools', '_tools', 'registry', '_registry']:
                        if f"{attr}_length" in tm_info:
                            length = tm_info[f"{attr}_length"]
                            keys = tm_info.get(f"{attr}_keys", [])
                            print(f"      {attr}: {length} elementos")
                            if keys:
                                print(f"        Keys: {keys}")
                                if length > 0:
                                    print(f"   🎉 ¡HERRAMIENTAS ENCONTRADAS EN {attr}!")
                elif 'tool_manager_error' in debug_data:
                    print(f"\n   ❌ Error en tool manager: {debug_data['tool_manager_error']}")
                
                # Show tool locations
                tool_locations = debug_data.get('tool_locations', {})
                if tool_locations:
                    print(f"\n   📍 Ubicaciones de herramientas verificadas:")
                    for location, info in tool_locations.items():
                        length = info.get('length', 'unknown')
                        sample = info.get('sample', 'no sample')
                        print(f"      {location}: {length} elementos")
                        if sample and sample != "serialization error":
                            print(f"        Muestra: {sample}")
                        if isinstance(length, int) and length > 0:
                            print(f"   🎉 ¡HERRAMIENTAS ENCONTRADAS EN {location}!")
                
            else:
                print(f"   ❌ Error en debug: HTTP {response.status_code}")
                print(f"   📄 Respuesta: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error en debug: {e}")
        
        # Test 2: Check if server is properly initialized
        print("\n2.🏥Verificando inicialización del servidor...")
        try:
            response = await client.get(f"{server_url}/health")
            if response.status_code == 200:
                health_data = response.json()
                print(f"   ✅ Servidor saludable: {health_data.get('status')}")
                print(
                    f"🔗 SonarQube conectado: {health_data.get('sonarqube_connected')}"
                )
                
                if health_data.get('sonarqube_connected'):
                    print(
                        f"✅SonarQube está conectado - las herramientas deberían funcionar"
                    )
                else:
                    print(
                        f"⚠️SonarQube no conectado - puede afectar el registro de herramientas"
                    )
            else:
                print(f"   ❌ Servidor no saludable: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error verificando salud: {e}")

        # Test 3: Try to list tools again with more detail
        print("\n3. 📋 Intentando listar herramientas con más detalle...")
        try:
            response = await client.get(f"{server_url}/tools")
            print(f"   📊 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                tools_data = response.json()
                tools = tools_data.get("tools", [])
                count = tools_data.get("count", 0)
                
                print(f"   📊 Herramientas reportadas: {count}")
                
                if count > 0:
                    print(f"   🎉 ¡ÉXITO! Herramientas encontradas:")
                    for i, tool in enumerate(tools, 1):
                        name = tool.get("name", "Unknown")
                        source = tool.get("source", "Unknown")
                        tool_type = tool.get("type", "Unknown")
                        print(f"      {i:2d}. {name} (de {source}, tipo: {tool_type})")
                else:
                    print(f"   ⚠️  Aún no se reportan herramientas")
                    debug_info = tools_data.get("debug", {})
                    if debug_info:
                        print(f"   🔍 Debug adicional:")
                        for key, value in debug_info.items():
                            print(f"      {key}: {value}")
            else:
                print(f"   ❌ Error listando herramientas: HTTP {response.status_code}")
                print(f"   📄 Respuesta: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error listando herramientas: {e}")
        
        # Test 4: Check server logs or errors
        print("\n4. 📝 Verificando posibles errores de inicialización...")
        
        # Try to access a known endpoint that should exist
        try:
            response = await client.get(f"{server_url}/ready")
            print(f"   📊 Readiness check: HTTP {response.status_code}")
            if response.status_code == 200:
                ready_data = response.json()
                print(f"   ✅ Servidor listo: {ready_data.get('status')}")
            else:
                print(f"   ⚠️  Servidor no listo: {response.text}")
        except Exception as e:
            print(f"   ❌ Error en readiness check: {e}")

def main():
    """Main function."""
    print("🚀 Debuggeando registro de herramientas MCP")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    
    try:
        asyncio.run(debug_mcp_registration())
    except KeyboardInterrupt:
        print("\n⏹️  Debug interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error ejecutando debug: {e}")
    
    print("\n" + "=" * 80)
    print("🏁 Debug completado")
    print("\n💡 Posibles causas si no hay herramientas:")
    print("   1. ❌ Error en importaciones de clases de herramientas")
    print("   2. ❌ Error en inicialización de SonarQubeClient")
    print("   3. ❌ Error en registro de herramientas en FastMCP")
    print("   4. ❌ FastMCP no está almacenando herramientas donde esperamos")
    print("   5. ❌ Servidor MCP no completó la inicialización")
    print("\n🔧 Próximos pasos si no hay herramientas:")
    print("   1. Verificar logs del servidor MCP")
    print("   2. Probar importaciones manualmente")
    print("   3. Verificar configuración de SonarQube")
    print("   4. Reiniciar servidor MCP completamente")

if __name__ == "__main__":
    main()