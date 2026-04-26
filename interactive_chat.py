import asyncio
import os
import sys
import time

from openai import AsyncOpenAI
from dotenv import load_dotenv

# Run as: python -m interactive_chat

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv()

# We will use simple subprocess to communicate with the MCP server
import subprocess
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    print("Aphrodite MCP Interactive Test Chat başlatılıyor...")
    
    # Start the fastmcp server via stdio
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "aphrodite_mcp.server"],
        env=os.environ.copy()
    )

    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_api_key:
        print("HATA: OPENROUTER_API_KEY environment variable bulunamadı!")
        return

    llm = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_api_key
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # Initialize connection
            await session.initialize()
            print("MCP Sunucusuna bağlanıldı!")

            # Fetch tools
            tools_response = await session.list_tools()
            tools = tools_response.tools
            print(f"Alınan araçlar: {[t.name for t in tools]}")

            # Convert MCP tools to OpenAI tool format
            openai_tools = []
            for t in tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                })

            messages = [
                {
                    "role": "system", 
                    "content": "Sen Aphrodite AI Asistanısın. Kullanıcıya moda, stil ve alışveriş konusunda yardımcı olursun. Ayrıca kullanıcının envanterini yönetebilir ve kamera ile kullanıcının giysilerini görebilirsin. Duruma göre gerekli araçları kullan."
                }
            ]

            shutdown_requested = False
            
            print("\nSohbet başladı! (Çıkmak için 'q' veya 'quit' yazın)")
            while not shutdown_requested:
                user_input = input("\nSen: ")
                if user_input.lower() in ['q', 'quit', 'exit']:
                    break
                
                messages.append({"role": "user", "content": user_input})

                print("Afrodit düşünüyor...")
                start_time = time.time()
                # Call LLM
                response = await llm.chat.completions.create(
                    model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct"),
                    messages=messages,
                    tools=openai_tools,
                    temperature=0.7
                )

                response_message = response.choices[0].message
                
                # Model sometimes generates a response AND calls a tool
                if response_message.content:
                    duration = time.time() - start_time
                    print(f"\nAphrodite ({duration:.1f} sn): {response_message.content}")
                
                # Check for tool calls
                if response_message.tool_calls:
                    messages.append(response_message.model_dump(exclude_none=True))
                    
                    for tool_call in response_message.tool_calls:
                        print(f"🛠️ Araç çağrılıyor: {tool_call.function.name}")
                        print(f"   Parametreler: {tool_call.function.arguments}")
                        
                        try:
                            args = json.loads(tool_call.function.arguments)
                            tool_result = await session.call_tool(tool_call.function.name, args)
                            # tool_result.content is a list of TextContent objects
                            result_text = "\n".join([c.text for c in tool_result.content if getattr(c, 'type', '') == 'text'])
                            
                            print(f"   Sonuç: {result_text}")
                            
                            if "[SYSTEM_SHUTDOWN_SIGNAL]" in result_text:
                                shutdown_requested = True
                                result_text = "Sistem kapanıyor. Kullanıcıya son bir kez veda et ve ekranın kapanacağını belirt."
                                
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result_text,
                                "name": tool_call.function.name
                            })
                            
                        except Exception as e:
                            error_msg = f"Araç çalıştırılırken hata: {str(e)}"
                            print(f"   {error_msg}")
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": error_msg,
                                "name": tool_call.function.name
                            })

                    # Get the final response after tool execution
                    print("Afrodit sonuçları yorumluyor...")
                    final_response = await llm.chat.completions.create(
                        model=os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-72b-instruct"),
                        messages=messages,
                        temperature=0.7
                    )
                    
                    # Check if choices exists and is not empty
                    if getattr(final_response, "choices", None) and len(final_response.choices) > 0:
                        final_text = final_response.choices[0].message.content or "Sistem Kapanıyor..."
                    else:
                        final_text = "Görüşmek üzere, kendimi kapatıyorum."
                        
                    duration = time.time() - start_time
                    messages.append({"role": "assistant", "content": final_text})
                    print(f"\nAphrodite ({duration:.1f} sn): {final_text}")
                    
                    if shutdown_requested:
                        print("\n🔌 Aphrodite (Sistem): Ayna/Sistem güvenli bir şekilde kapatıldı.")
                        return

                elif getattr(response_message, "tool_calls", None) is None and not getattr(response_message, "content", None):
                    pass # Empty message


if __name__ == "__main__":
    asyncio.run(main())
