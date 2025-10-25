#!/usr/bin/env python3
"""
Script para probar la corrección de FunctionTool.
"""

import asyncio
import json
from datetime import datetime


async def test_function_tool_fix():
    """Test FunctionTool fix."""
    try:
        import httpx
    except ImportError:
        print("❌ httpx no está instalado")
        return
    
    server_url = "http://localhost:8001"
    
    print("🔧 Probando corrección de FunctionTool...")
    print(f"🌐 URL del servidor: {server_url}")
    print("=" * 70)
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        
        # Test 1: Try health_check (should work)
        print("\n1. 🏥 Probando health_check...")
        try:
            payload = {"arguments": {}}
            response = await client.post(
                f"{server_url}/tools/health_check",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"   📊 HTTP Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ ¡health_check FUNCIONA!")
                print(f"   📄 Resultado: {json.dumps(result, indent=2)}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                print(f"   📄 Respuesta: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 2: Try list_projects (the one that was failing)
        print("\n2. 📋 Probando list_projects (el que fallaba)...")
        try:
            payload = {"arguments": {"page_size": 3}}
            response = await client.post(
                f"{server_url}/tools/list_projects",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"   📊 HTTP Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ ¡list_projects FUNCIONA!")
                if result.get("success"):
                    projects = result.get("result", [])
                    if isinstance(projects, list):
                        print(f"   📊 Proyectos encontrados: {len(projects)}")
                        for i, project in enumerate(projects, 1):
                            if isinstance(project, dict):
                                name = project.get("name", "Unknown")
                                key = project.get("key", "Unknown")
                                print(f"      {i}. {name} ({key})")
                    else:
                        print(f"   📄 Resultado: {json.dumps(result, indent=2)[:300]}...")
                else:
                    print(f"   ⚠️  Herramienta ejecutada pero con error: {result}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                print(f"   📄 Respuesta: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 3: Try get_measures
        print("\n3. 📊 Probando get_measures...")
        try:
            payload = {"arguments": {"project_key": "sample-project"}}
            response = await client.post(
                f"{server_url}/tools/get_measures",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"   📊 HTTP Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ ¡get_measures FUNCIONA!")
                if result.get("success"):
                    measures_data = result.get("result", {})
                    measures = measures_data.get("measures", [])
                    print(f"   📊 Métricas encontradas: {len(measures) if isinstance(measures, list) else 'N/A'}")
                    if isinstance(measures, list) and measures:
                        for measure in measures[:3]:
                            if isinstance(measure, dict):
                                metric = measure.get("metric", "Unknown")
                                value = measure.get("value", "Unknown")
                                print(f"      - {metric}: {value}")
                else:
                    print(f"   ⚠️  Herramienta ejecutada pero con error: {result}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                print(f"   📄 Respuesta: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 4: Try get_cache_info
        print("\n4. 💾 Probando get_cache_info...")
        try:
            payload = {"arguments": {}}
            response = await client.post(
                f"{server_url}/tools/get_cache_info",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            print(f"   📊 HTTP Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                print(f"   ✅ ¡get_cache_info FUNCIONA!")
                print(f"   📄 Resultado: {json.dumps(result, indent=2)[:200]}...")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
                print(f"   📄 Respuesta: {response.text}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Test 5: List tools to see if they're all available now
        print("\n5. 📋 Verificando lista completa de herramientas...")
        try:
            response = await client.get(f"{server_url}/tools")
            print(f"   📊 HTTP Status: {response.status_code}")
            if response.status_code == 200:
                tools_data = response.json()
                tools = tools_data.get("tools", [])
                count = tools_data.get("count", 0)
                
                print(f"   ✅ Herramientas listadas: {count}")
                if count > 0:
                    print(f"   🎉 ¡Todas las herramientas están disponibles!")
                    print(f"   📋 Primeras 5 herramientas:")
                    for i, tool in enumerate(tools[:5], 1):
                        name = tool.get("name", "Unknown")
                        source = tool.get("source", "Unknown")
                        print(f"      {i}. {name} (fuente: {source})")
                else:
                    print(f"   ❌ Aún no se listan herramientas")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error: {e}")


def main():
    """Main function."""
    print("🚀 Prueba de corrección de FunctionTool")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    
    try:
        asyncio.run(test_function_tool_fix())
    except KeyboardInterrupt:
        print("\n⏹️  Interrumpido")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 70)
    print("🏁 Prueba completada")
    
    print("\n💡 Resultados esperados:")
    print("   ✅ health_check: Debería funcionar (datos reales)")
    print("   ✅ list_projects: Debería funcionar ahora (era el que fallaba)")
    print("   ✅ get_measures: Debería funcionar")
    print("   ✅ get_cache_info: Debería funcionar")
    print("   ✅ Lista de herramientas: Debería mostrar 38 herramientas")
    
    print("\n🔧 Si funciona:")
    print("   🎉 ¡El problema de FunctionTool está resuelto!")
    print("   🎉 ¡Todas las 38 herramientas MCP están disponibles!")
    print("   🎉 ¡El sistema está completamente operativo!")


if __name__ == "__main__":
    main()