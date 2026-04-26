# Aphrodite MCP Test Guideline

Bu belge, `MCP-Workplace` içerisine ilk defa giren veya sistemi hızlıca test etmek / geliştirmek isteyen biri için hızlı bir başvuru kılavuzudur.

## 🚀 Hızlı Başlangıç (Kurulum ve Çalıştırma)

Sistemi izole bir şekilde kurmak ve LLM (OpenRouter) ile test etmek için aşağıdaki adımları izleyin:

**1. Test Ortamını Kurun**
Terminal üzerinden `MCP-Workplace` klasörüne girin ve kurulum scriptini çalıştırın:
```bash
cd MCP-Workplace
chmod +x setup_test_env.sh
./setup_test_env.sh
```
*(Bu betik otomatik olarak `test_venv` isimli bir izole sanal ortam açar ve `mcp`, `openai`, `httpx` gibi bağımlılıkları yükler.)*

**2. Sanal Ortamı Aktif Edin**
Kurulum bittikten sonra her yeni terminalde şu komutla giriş yapın:
```bash
source test_venv/bin/activate
```

**3. Interactive Chat (Sohbeti) Başlatın**
```bash
python interactive_chat.py
```
Bu komut, hem `aphrodite_mcp.server` sunucusunu başlatır hem de LLM'e (Afrodit'e) bağlanıp bütün araçları dinlemeye alır.

---

## 🛠️ Nasıl Test Edilir? (Örnek Senaryolar)

Sohbet başladığında terminalde Aphrodite ile doğal bir dilde konuşabilirsiniz. Aşağıdaki senaryoları deneyebilirsiniz:

- **Envanter Kontrolü:** 
  - *"Dolabımda (envanterimde) hangi kıyafetler var bana listeleyebilir misin?"*
- **Eşya Ekleme/Çıkarma:**
  - *"Bugün mağazadan Siyah Deri Ceket aldım, envanterime ekle."*
  - *"Geçen gün eklediğimiz beyaz tişörtü dolabımdan siler misin?"*
- **Kamera / Vision Testi:**
  - *"Kamerayı açıp aynada bana bakar mısın, üzerimde hangi kıyafet var?"*
  - *(Not: Kamera mock moddaysa "Test Image" analizini getirecektir, mock iptal ise doğrudan webcam resmini alır.)*
- **Kapanış / Veda (Shutdown Testi):**
  - *"Çıkış yapmak istiyorum, kendini kapat."*
  - *(Yukarıdaki durumda LLM önce `turn_off_screen` aracını çeker, size "Görüşürüz ekranı kapatıyorum" diyerek vedalaşır ve `Ayna kapatıldı.` uyarısıyla script güvenle sonlanır.)*

## 📁 Mimari Yapısı

- `aphrodite_mcp/server.py`: En temel **FastMCP** sunucumuz. `@mcp.tool()` yetenekleri buraya eklenir. `interactive_chat` gibi istemciler bu sunucudan yetenek setini okur.
- `interactive_chat.py`: OpenAI GPT/Qwen SDK'si üzerinden sunucuya bağlanarak tool çağırma (Tool Calling) döngüsünü yapan ana LLM Agent scriptimiz. Test amaçlıdır.
- `aphrodite_mcp/data/user_inventory.json`: Hızlı veritabanı okuma/yazma işlemi yapılan kullanıcı dolabı.
