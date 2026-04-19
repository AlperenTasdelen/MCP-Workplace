# Model Context Protocol (MCP) Rehberi

Bu dosya, Model Context Protocol (MCP) konseptlerini öğrenmek, test etmek ve kendi Büyük Dil Modellerinize (LLM) dış dünyayla iletişim kurma yeteneği kazandırmak için derlenmiş kapsamlı bir rehberdir.

## MCP Nedir?

Model Context Protocol (MCP), Anthropic öncülüğünde geliştirilen, yapay zeka modellerinin (Claude, vb.) harici veri kaynaklarına, API'lere ve devops çalıştırılabilir araçlarına (tools) güvenli, standart ve çift yönlü bir şekilde bağlanmasını sağlayan açık kaynaklı bir protokoldür. 
Tıpkı USB-Type-C'nin bilgisayarlarla farklı cihazları bağlayan standart bir arabirim olması gibi, MCP de yapay zeka modellerini dış araçlara bağlar.

## Temel Kavramlar

MCP mimarisinde "Sunucular" (Servers) yapay zeka istemcilerine (Clients — örneğin Claude Desktop veya Cursor IDE) üç temel bileşen sunar:

1. **Araçlar (Tools):** Yapay zekanın **aktif olarak çalıştırabileceği** fonksiyonlardır. Dış sistemlerle etkileşime girmek (örn. web araması yapmak, SQL sorgusu çalıştırmak, dosya düzenlemek) için kullanılır.
2. **Kaynaklar (Resources):** Yapay zekanın **okuyabileceği** veri setleridir. Konfigürasyon dosyaları, sistem logları veya statik API yanıtları gibi bağlam (context) verilerini modele sunar.
3. **İstemler (Prompts):** Kullanıcıların belirli bir görevi başlatmasını kolaylaştıran, modüler ve parametrik prompt şablonlarıdır.

## Mimarideki Roller

- **MCP Host:** İstemci asistanını (LLM) çalıştıran uygulamadır (örn. Claude Desktop veya Cursor IDE).
- **MCP Client:** Host içerisindeki iletişim katmanıdır. Sunucuyla protokol standartlarında mesajlaşır.
- **MCP Server:** *Sizin yazdığınız yapıdır.* İstediğiniz herhangi bir özel fonksiyonu (Tools), veriyi (Resources) veya şablonu (Prompts) barındıran yerel/uzak arka plan servisidir.

---

## MCP Sunucusu Geliştirmek (Örnekler)

MCP sunucularını NodeJS (TypeScript) veya Python kullanarak geliştirebilirsiniz, her iki dilin de resmi SDK desteği çok güçlüdür.

### 1. Python ile Temel Bir Tool Geliştirmek (FastMCP)

Python için en pratik yol **FastMCP** kütüphanesini (FastAPI benzeri yapıyı) kullanmaktır.

**Kurulum:**
```bash
pip install "mcp[cli]"
```

**Örnek (server.py):**
```python
from mcp.server.fastmcp import FastMCP

# Sunucuyu (Server) başlatıyoruz
mcp = FastMCP("HavaDurumuSunucusu")

# @mcp.tool dekoratörü ile LLM'in kullanabileceği bir "Araç" (Tool) tanımlıyoruz.
# Fonksiyonun docstring'i modeli yönlendirdiği için çok kritik ve detaylı olmalıdır!
@mcp.tool()
def get_weather(city: str) -> str:
    """Verilen şehrin mevcut hava durumunu döndürür."""
    # Normal şartlarda buraya gerçek bir API çağrısı gelir (örn. OpenWeather)
    return f"{city} şehrinde hava durumu güneşli ve 25°C."

if __name__ == "__main__":
    # Sunucuyu standart input/output (stdio) ile çalıştırır.
    mcp.run()
```

### 2. TypeScript / Node.js ile Geliştirmek

Büyük çaplı araçlar yazarken, TypeScript SDK'yı veri yapıları (Zod kullanarak) ve tipleri zorunlu kıldığı için endüstri standardı olarak düşünebiliriz.

**Kurulum:**
```bash
npm install @modelcontextprotocol/sdk zod
```

**Örnek (index.ts):**
```typescript
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { CallToolRequestSchema, ListToolsRequestSchema } from "@modelcontextprotocol/sdk/types.js";

// Sunucu nesnesini oluştur
const server = new Server({
  name: "selamlama-sunucusu",
  version: "1.0.0",
}, {
  capabilities: { tools: {} },
});

// Aracı (Tool) yapay zekaya tanıt/listele
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [{
    name: "selamla",
    description: "Kullanıcıya ismini kullanarak resmi bir karşılama metni oluşturur.",
    inputSchema: {
      type: "object",
      properties: { name: { type: "string", description: "Kullanıcının ismi" } },
      required: ["name"],
    },
  }],
}));

// Yapay zekanın aracı çağırdığında ne yapacağını (Handler) tanımla
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  if (request.params.name === "selamla") {
    const name = String(request.params.arguments?.name);
    return { content: [{ type: "text", text: `Merhaba ${name}, sana nasıl yardımcı olabilirim?` }] };
  }
  throw new Error("Araç bulunamadı!");
});

// İletişimi başlat
const transport = new StdioServerTransport();
await server.connect(transport);
```

---

## Sunucuyu Test Etme ve Çalıştırma (MCP Inspector)

Geliştirdiğiniz MCP sunucusunu her seferinde Claude Desktop'u kapat/aç yaparak denemek yerine, resmi UI testi olan **MCP Inspector**'ı kullanabilirsiniz. Tarayıcıda açılan bu arayüz doğrudan yazdığınız tool'lara bağlanır ve parametre testleri yapabilmenizi sağlar.

**Python Sunucusu İçin:**
```bash
npx @modelcontextprotocol/inspector python server.py
```

**NodeJS Sunucusu İçin:**
```bash
npx @modelcontextprotocol/inspector node index.js
```
*(Yukarıdaki komutları terminalinizde çalıştırdığınızda Inspector arayüzü sizin için bir web sayfasında açılacaktır.)*

## LLM'e Asıl Entegrasyon

Eğer bir MCP sunucunuz sağlıklı şekilde çalışıyorsa; Claude Desktop konfigürasyonunuza (genelde `~/Library/Application Support/Claude/claude_desktop_config.json`) bu sunucuyu tanıtırsınız.

Örnek Bir Konfigürasyon:
```json
{
  "mcpServers": {
    "benim-yerel-hava-durumum": {
      "command": "python",
      "args": ["/Users/alperentasdelen/Desktop/MCP-Workplace/server.py"]
    }
  }
}
```
Ardından Claude'a girip: *"Ankara'da hava nasıl?"* diye sorduğunuzda Claude artık bu python dosyasını çalıştıracak (aracı tetikleyecek) ve sonucu size cevap olarak getirecektir.

## Çalışma Ortamı (Bu Repo) İçin Önerilen Bir Sonraki Adım

1. Bu dosyanın buluğunduu dizinde `python_mcp_server` adlı bir klasör açın.
2. Bir sanal ortam (venv) oluşturun ve `mcp` paketini yükleyin.
3. İçine bir uygulamanıza/hayatınıza uygun (veritabanınızdan kullanıcı getiren veya notlarınızı arayan) bir fonksiyon yazarak `FastMCP` ile süsleyin.
4. `MCP Inspector` ile deneyin!
