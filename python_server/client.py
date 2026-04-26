"""Interaktif Gemini + MCP chat arayüzü.

Kullanım:
    cd python_server
    ./venv/bin/python client.py

Komutlar (chat içinde):
    /tools   — yüklenmiş MCP tool'larını listele
    /clear   — konuşma geçmişini sıfırla
    /exit    — çıkış (Ctrl+C de iş görür)
"""

import asyncio
import json
import os
import sys
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.5-flash"
MAX_TOOL_ITERATIONS = 8

# ANSI renkler — minimal, ekstra paket yok
C_USER = "\033[36m"
C_AI = "\033[32m"
C_TOOL = "\033[33m"
C_RESULT = "\033[90m"
C_ERR = "\033[31m"
C_DIM = "\033[2m"
C_BOLD = "\033[1m"
C_RESET = "\033[0m"

SYSTEM_PROMPT = """Sen, kullanıcının OpenShift cluster'ını yönetmesine yardım eden bir asistansın.
Türkçe yanıt ver.

Elindeki tool'ların (oc_*) hepsi cluster ile konuşur. Şu prensiplere uy:

1) Eğer kullanıcının mesajı cluster/devops ile ilgili DEĞİLSE, tool ÇAĞIRMA;
   normal sohbet et veya soruyu cevapla. Tool'ları "her ihtimale karşı" kullanma.

2) Cluster işlemleri için uygun tool'u çağır. Daha önce çağırdığın tool'un
   sonucunu hatırla; aynı bilgiyi tekrar tekrar isteme.

3) YAZMA tool'larında (örn. oc_scale_deployment) dikkatli ol:
   - Kullanıcı net bir komut verdiyse uygula ve sonucu raporla.
   - Belirsiz/riskli görünüyorsa önce kullanıcıdan onay iste.

4) Eğer bir tool sonucunda hata varsa (401/403/404 vs.) kullanıcıya nedenini
   sade Türkçe açıkla; mümkünse RBAC/URL/token açısından öneri sun.

5) Cevabını kısa ve net tut. Uzun JSON dökümlerini özetle, tüm metni yapıştırma.
"""


def banner(tool_count: int, namespace: str) -> None:
    print(f"\n{C_BOLD}{'=' * 64}{C_RESET}")
    print(f"{C_BOLD}  OpenShift MCP Chat — Gemini ({MODEL_NAME}){C_RESET}")
    print(f"  Yüklenen tool sayısı : {tool_count}")
    print(f"  Varsayılan namespace : {namespace or '(tanımsız)'}")
    print(f"  Komutlar             : /tools  /clear  /exit")
    print(f"{C_BOLD}{'=' * 64}{C_RESET}\n")


def fmt_args(args: dict[str, Any]) -> str:
    """Tool argümanlarını tek satırda, gerektiğinde kısaltarak basar."""
    if not args:
        return ""
    parts = []
    for key, value in args.items():
        rendered = json.dumps(value, ensure_ascii=False)
        if len(rendered) > 60:
            rendered = rendered[:57] + "..."
        parts.append(f"{key}={rendered}")
    return ", ".join(parts)


def render_tool_call(name: str, args: dict[str, Any]) -> None:
    print(f"{C_TOOL}  → tool: {name}({fmt_args(args)}){C_RESET}")


def render_tool_result(text: str, max_lines: int = 12, max_chars: int = 800) -> None:
    """Sonucu KISALTILMIŞ olarak ekrana basar; LLM'e tam metin gönderilir."""
    display = text
    lines = display.splitlines()
    if len(lines) > max_lines:
        display = "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} satır gizlendi]"
    if len(display) > max_chars:
        display = display[:max_chars] + f"... [+{len(display) - max_chars} karakter]"
    indented = "\n".join(f"    {ln}" for ln in display.splitlines())
    print(f"{C_RESULT}{indented}{C_RESET}")


def list_tools_cmd(openai_tools: list[dict[str, Any]]) -> None:
    print(f"\n{C_BOLD}Yüklenmiş tool'lar:{C_RESET}")
    for entry in openai_tools:
        fn = entry["function"]
        desc = (fn.get("description") or "").splitlines()[0]
        print(f"  • {C_TOOL}{fn['name']}{C_RESET} — {desc}")
    print()


async def chat_loop(
    session: ClientSession,
    client: AsyncOpenAI,
    openai_tools: list[dict[str, Any]],
) -> None:
    base_messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages: list[Any] = list(base_messages)

    while True:
        try:
            user_input = input(f"{C_USER}You> {C_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGörüşürüz!")
            return

        if not user_input:
            continue
        cmd = user_input.lower()
        if cmd in ("/exit", "/quit", "/bye"):
            print("Görüşürüz!")
            return
        if cmd == "/tools":
            list_tools_cmd(openai_tools)
            continue
        if cmd == "/clear":
            messages = list(base_messages)
            print(f"{C_DIM}(geçmiş temizlendi){C_RESET}\n")
            continue

        messages.append({"role": "user", "content": user_input})

        for iteration in range(MAX_TOOL_ITERATIONS):
            try:
                response = await client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=messages,
                    tools=openai_tools,
                )
            except Exception as exc:  # noqa: BLE001
                print(f"{C_ERR}Gemini çağrısı başarısız: {exc}{C_RESET}\n")
                # Bozuk son user mesajını çıkar ki tekrar deneme bozulmasın
                if messages and messages[-1].get("role") == "user":
                    messages.pop()
                break

            msg = response.choices[0].message
            messages.append(msg)

            if not msg.tool_calls:
                content = msg.content or "(boş cevap)"
                print(f"{C_AI}AI> {content}{C_RESET}\n")
                break

            if msg.content:
                print(f"{C_DIM}AI (düşünce): {msg.content}{C_RESET}")

            for tc in msg.tool_calls:
                name = tc.function.name
                try:
                    args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}

                render_tool_call(name, args)

                try:
                    tool_result = await session.call_tool(name, arguments=args)
                    if tool_result.content and hasattr(tool_result.content[0], "text"):
                        result_text = tool_result.content[0].text  # type: ignore[union-attr]
                    else:
                        result_text = "(boş içerik)"
                except Exception as exc:  # noqa: BLE001
                    result_text = f"[Tool hatası] {type(exc).__name__}: {exc}"

                render_tool_result(result_text)

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": name,
                        "content": result_text,
                    }
                )
        else:
            print(f"{C_ERR}Tool çağrısı limiti ({MAX_TOOL_ITERATIONS}) aşıldı, döngü kesildi.{C_RESET}\n")


async def main() -> None:
    if not GEMINI_API_KEY:
        print(f"{C_ERR}GEMINI_API_KEY .env içinde tanımlı değil.{C_RESET}")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[os.path.join(script_dir, "server.py")],
    )

    print(f"{C_DIM}MCP sunucusu başlatılıyor...{C_RESET}")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools_response = await session.list_tools()
            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                }
                for tool in mcp_tools_response.tools
            ]

            client = AsyncOpenAI(
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                api_key=GEMINI_API_KEY,
            )

            banner(
                tool_count=len(openai_tools),
                namespace=os.environ.get("OPENSHIFT_NAMESPACE", ""),
            )

            await chat_loop(session, client, openai_tools)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGörüşürüz!")
