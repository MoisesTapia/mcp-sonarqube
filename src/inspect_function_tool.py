#!/usr/bin/env python3
"""
Script para inspeccionar los atributos de FunctionTool de FastMCP.
"""

import asyncio
import json
from datetime import datetime


async def inspect_function_tool():
    """Inspect FunctionTool attributes."""
    try:
        import httpx
    except ImportError:
        print("❌ httpx no está instalado")
        return
    
    server_url = "http://localhost:8001"
    
    print("🔍 Inspeccionando FunctionTool...")
    print(f"🌐 URL del servidor: {server_url}")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        
        # Get debug info to see FunctionTool structure
        print("\n1. 🔧 Obteniendo información de debug...")
        try:
            response = await client.get(f"{server_url}/debug/mcp")
            if response.status_code == 200:
                debug_data = response.json()
                
                # Show tool manager info
                tm_info = debug_data.get('tool_manager_info', {})
                if tm_info:
                    print(f"   📊 Tool Manager encontrado")
                    tools_keys = tm_info.get('_tools_keys', [])
                    if tools_keys:
                        first_tool = tools_keys[0]
                        print(f"   🎯 Primera herramienta: {first_tool}")
                        
                        # Now let's try to get more detailed info about FunctionTool
                        print(f"\n2. 🔍 Intentando obtener atributos de FunctionTool...")
                        
                        # We need to modify the debug endpoint to show FunctionTool attributes
                        # For now, let's see what we can infer from the error
                        
            else:
                print(f"   ❌ Debug failed: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error en debug: {e}")


def main():
    """Main function."""
    print("🚀 Inspección de FunctionTool")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    
    try:
        asyncio.run(inspect_function_tool())
    except KeyboardInterrupt:
        print("\n⏹️  Interrumpido")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print("🏁 Inspección completada")
    
    print("\n💡 Basándome en los logs, el problema es:")
    print("   - FunctionTool se encuentra correctamente")
    print("   - Pero tool_obj.func no existe o no es callable")
    print("   - Necesitamos encontrar el atributo correcto")
    
    print("\n🔧 Posibles atributos a probar:")
    print("   - tool_obj.function")
    print("   - tool_obj.handler") 
    print("   - tool_obj.callback")
    print("   - tool_obj._func")
    print("   - tool_obj._function")
    print("   - await tool_obj(...)")  # Puede ser que el objeto mismo sea callable de forma async


if __name__ == "__main__":
    main()