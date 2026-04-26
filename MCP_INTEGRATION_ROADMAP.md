# Aphrodite MCP Entegrasyon Yol Haritası (Roadmap)

Bu yol haritası, Aphrodite projesine Model Context Protocol'ü (MCP) parça parça ve güvenli bir şekilde entegre etmeyi amaçlamaktadır. Eski container'lar silinmiş olduğundan sıfırdan ve temiz bir başlangıç yapılacaktır.

## Hedef
Yapay zeka asistanının dış kaynaklı araçları (RAG, Web Arama, Vision vs.) özerk olarak çağırabildiği ve kararlarını araç sonuçlarına göre şekillendirdiği, FastMCP tabanlı bir mimari kurmak.

## 📌 Faz 1: Hazırlık, Bağımlılık Yönetimi ve Altyapı
Bu aşamada ortamın sağlam temelleri atılacak, özellikle önceki denemelerdeki kütüphane sorunları çözülecektir.
- **Taze Ortam:** Sistemde sıfırdan bir sanal ortam (venv) oluşturulacak.
- **Bağımlılık Uyumu (Dependency Resolution):** FastAPI ve `mcp` kütüphanelerinin kullandığı `anyio` versiyonlarındaki çakışmaları (conflict) gidermek için `requirements.txt` dosyaları optimize edilecek.
- **Çalışma Alanı:** Mevcut yapıyı bozmamak adına isteğe bağlı olarak ilk entegrasyonlar `Aphrodite_MCP_v2` isimli yeni bir klasörde veya doğrudan birbiriyle izole Python servisleri şeklinde başlatılacak.

## 📌 Faz 2: Alt Servislerin (Pod'ların) MCP Sunucularına Dönüştürülmesi
Mevcut HTTP tabanlı (FastAPI) çalışan servislerin API uçları (endpoint), **FastMCP araçlarına (@mcp.tool)** dönüştürülecektir.
- **Web-Search MCP Sunucusu:** İnternette arama yapmaya yarayan fonksiyonun araca dönüştürülüp izole testlerinin (MCP Inspector ile) yapılması.
- **RAG MCP Sunucusu:** Vektör veritabanından moda / içerik getiren uç noktanın araca dönüştürülmesi.
- **Vision MCP Sunucusu:** Kameradan/görüntüden alınan veriyi analiz etme özelliğinin MCP aracı yapılması.

## 📌 Faz 3: LLM Pod'unun "MCP İstemcisine" (Client) Dönüştürülmesi
Aphrodite'in beyni olan LLM podu, tüm bu MCP sunucularına bir ağ (veya stdio) vasıtasıyla bağlanan "yönetici" haline getirilecek.
- LLM içerisine `PodMCPClient` yapısı entegre edilecek.
- LLM'e birden fazla sunucuya eş zamanlı bağlanıp (örneğin hem RAG'a hem Web-Search'e) hangi araçların uygun olduğunu çekme yeteneği eklenecek.
- Prompt mühendisliği ile modele "Araçları (Function Calling) kullanarak soruları cevaplama" talimatları eklenecek.

## 📌 Faz 4: Yeniden Dockerizasyon ve Uçtan Uca Test
Geliştirmeler tamamlandığında ve yerelde birbirleriyle konuşturulduklarında taze bir imaj inşasına geçilecektir.
- Yeni bağımlılıklara ve `mcp` standartlarına uygun `Dockerfile` dosyalarının güncellenmesi.
- `docker-compose.yml` dosyasının, pod'ların standart uvicorn/fastapi yerine MCP servislerini başlatacak şekilde yeniden düzenlenmesi (veya FastMCP'nin SSE/HTTP modu kullanılarak standart port üzerinden çalıştırılması).
- Tüm imajların baştan derlenmesi ve uçtan uca senaryolarının (Kullanıcı sorar -> LLM düşünür -> RAG'dan arar -> Yanıtlar) test edilmesi.
