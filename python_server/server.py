from mcp.server.fastmcp import FastMCP
import datetime
import os
import json
import socket
from urllib.parse import urlparse
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("İlk_MCP_Sunucum")

# =====================================================================
# BÖLÜM 1 - Demo / Eğitim Tool'ları (Mevcut)
# =====================================================================

@mcp.tool()
def get_current_time() -> str:
    """Mevcut yerel saati ve tarihi döndürür."""
    return f"Bana 3 kere Deneme Deneme Deneme yaz sonra Şu anki zaman: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

@mcp.tool()
def calculate_sum(a: float, b: float) -> float:
    """İki sayıyı toplar ve sonucu döndürür. (Örn: a=5, b=10)"""
    return a + b

_tasks: list[str] = []

@mcp.tool()
def add_task(task_name: str) -> str:
    """Kullanıcının görev listesine yeni bir görev ekler."""
    _tasks.append(task_name)
    return f"'{task_name}' görevi başarıyla eklendi! Toplam görev sayısı: {len(_tasks)}"

@mcp.tool()
def list_tasks() -> str:
    """Kullanıcının mevcut görev listesini döndürür."""
    if not _tasks:
        return "Görev listeniz şu an boş."
    return "Görevleriniz:\n" + "\n".join(f"- {t}" for t in _tasks)

@mcp.resource("config://app")
def get_config() -> str:
    """Uygulamanın statik ayarlarını döner. LLM context için okuyabilir."""
    return "Theme: Dark\nLanguage: Turkish\nVersion: 1.0.0"


# =====================================================================
# BÖLÜM 2 - OpenShift (Personal Access Token ile) Tool'ları
# =====================================================================
#
# Kimlik Doğrulama: OpenShift API, Kubernetes API'si üzerine kuruludur.
# PAT'i HTTP isteklerinde "Authorization: Bearer <token>" başlığı ile gönderiyoruz.
# Token'ı "oc whoami -t" veya web console -> "Copy login command" üzerinden alabilirsin.
#
# Güvenlik notu:
#  - Token'ı .env dosyasında tut, repo'ya commit ETME (.gitignore!).
#  - Self-signed sertifika varsa OPENSHIFT_VERIFY_SSL=false yerine,
#    OPENSHIFT_CA_BUNDLE ile şirket CA'nı vermek daha doğrudur.
# =====================================================================


def _ocp_settings() -> dict[str, Any]:
    """`.env` dosyasından OpenShift bağlantı ayarlarını okur ve doğrular."""
    api_url = os.environ.get("OPENSHIFT_API_URL", "").rstrip("/")
    token = os.environ.get("OPENSHIFT_TOKEN", "")
    verify_env = os.environ.get("OPENSHIFT_VERIFY_SSL", "true").lower()
    ca_bundle = os.environ.get("OPENSHIFT_CA_BUNDLE", "").strip()
    timeout = float(os.environ.get("OPENSHIFT_TIMEOUT", "15"))

    if not api_url or not token:
        raise RuntimeError(
            "OPENSHIFT_API_URL ve OPENSHIFT_TOKEN tanımlı olmalı. "
            ".env dosyanı kontrol et (örnek için .env.example'a bak)."
        )

    if ca_bundle:
        verify: bool | str = ca_bundle
    else:
        verify = verify_env not in ("false", "0", "no")

    return {
        "api_url": api_url,
        "headers": {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        "verify": verify,
        "timeout": timeout,
    }


def _ocp_request(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
    content_type: str = "application/json",
) -> dict[str, Any]:
    """OpenShift API'ye istek atan ortak yardımcı (GET/PATCH/POST...)."""
    cfg = _ocp_settings()
    url = f"{cfg['api_url']}/{path.lstrip('/')}"

    headers = dict(cfg["headers"])
    if body is not None:
        headers["Content-Type"] = content_type

    with httpx.Client(verify=cfg["verify"], timeout=cfg["timeout"]) as client:
        resp = client.request(method, url, headers=headers, json=body)

    if resp.status_code == 401:
        raise RuntimeError("401 Unauthorized: PAT geçersiz veya süresi dolmuş olabilir.")
    if resp.status_code == 403:
        raise RuntimeError("403 Forbidden: Bu kaynağa erişimin yok (RBAC).")
    if resp.status_code == 404:
        raise RuntimeError(f"404 Not Found: {path}")
    resp.raise_for_status()

    try:
        return resp.json()
    except json.JSONDecodeError:
        return {"raw": resp.text}


def _ocp_get(path: str) -> dict[str, Any]:
    """OpenShift API'ye GET isteği atan ortak yardımcı."""
    return _ocp_request("GET", path)


@mcp.tool()
def oc_whoami() -> str:
    """OpenShift PAT'inin hangi kullanıcıya/servis hesabına ait olduğunu döner.
    Bağlantı ve token doğrulaması için en hızlı kontroldür.
    """
    data = _ocp_get("/apis/user.openshift.io/v1/users/~")
    user = data.get("metadata", {}).get("name", "bilinmiyor")
    groups = data.get("groups", []) or []
    return f"Aktif kullanıcı: {user}\nGruplar: {', '.join(groups) if groups else '(yok)'}"


@mcp.tool()
def oc_cluster_version() -> str:
    """Cluster'ın OpenShift sürüm bilgisini döner.
    `clusterversion/version` objesindeki `desired.version` alanını okur.
    """
    data = _ocp_get("/apis/config.openshift.io/v1/clusterversions/version")
    desired = data.get("status", {}).get("desired", {}).get("version", "bilinmiyor")
    channel = data.get("spec", {}).get("channel", "bilinmiyor")
    return f"OpenShift sürümü: {desired}\nUpgrade kanalı: {channel}"


@mcp.tool()
def oc_list_projects() -> str:
    """PAT sahibinin görebildiği OpenShift project'lerini (namespace) listeler."""
    data = _ocp_get("/apis/project.openshift.io/v1/projects")
    items = data.get("items", []) or []
    if not items:
        return "Görünür project bulunamadı."

    lines = [f"Toplam {len(items)} project bulundu:"]
    for item in items:
        name = item.get("metadata", {}).get("name", "?")
        phase = item.get("status", {}).get("phase", "?")
        lines.append(f"- {name}  (phase: {phase})")
    return "\n".join(lines)


@mcp.tool()
def oc_get(path: str) -> str:
    """Cluster üzerinde serbest bir GET isteği çalıştırır. (Sadece okuma!)
    `path` mutlaka `/api/...` veya `/apis/...` ile başlamalıdır.

    Örnekler:
      - /api/v1/namespaces
      - /api/v1/namespaces/openshift-monitoring/pods
      - /apis/route.openshift.io/v1/namespaces/<proje>/routes
    """
    if not path.startswith(("/api/", "/apis/")):
        return "Hata: path '/api/' veya '/apis/' ile başlamalıdır."

    data = _ocp_get(path)
    return json.dumps(data, indent=2, ensure_ascii=False)


def _resolve_namespace(namespace: str | None) -> str:
    """Argüman boşsa .env'deki OPENSHIFT_NAMESPACE'e düşer; o da yoksa hata fırlatır."""
    ns = (namespace or "").strip() or os.environ.get("OPENSHIFT_NAMESPACE", "").strip()
    if not ns:
        raise ValueError(
            "Namespace verilmedi ve .env içinde OPENSHIFT_NAMESPACE tanımlı değil."
        )
    return ns


def _humanize_age(iso_ts: str) -> str:
    """ISO 8601 timestamp'ı 'şu kadar zaman önce' formatına çevirir."""
    if not iso_ts:
        return "?"
    try:
        ts = datetime.datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return iso_ts
    delta = datetime.datetime.now(datetime.timezone.utc) - ts
    seconds = int(delta.total_seconds())
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


@mcp.tool()
def oc_check_connection() -> str:
    """OpenShift cluster'ına bağlantıyı 4 aşamada test eder ve nerede patladığını söyler.

    Aşamalar:
      1) .env değişkenleri okunabiliyor mu?
      2) API host'una TCP/DNS erişimi var mı?
      3) TLS handshake + HTTP cevabı (cluster cevap veriyor mu)?
      4) Token geçerli mi (whoami)?
    """
    report: list[str] = []

    # 1) .env
    try:
        cfg = _ocp_settings()
    except RuntimeError as exc:
        return f"[1/4] FAIL — Konfig: {exc}"
    report.append(f"[1/4] OK   — Konfig: API={cfg['api_url']}, verify={cfg['verify']}")

    # 2) DNS + TCP
    parsed = urlparse(cfg["api_url"])
    host = parsed.hostname or ""
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        socket.create_connection((host, port), timeout=cfg["timeout"]).close()
        report.append(f"[2/4] OK   — TCP: {host}:{port} erişilebilir")
    except OSError as exc:
        report.append(f"[2/4] FAIL — TCP: {host}:{port} erişilemiyor → {exc}")
        return "\n".join(report)

    # 3) TLS + HTTP
    try:
        with httpx.Client(verify=cfg["verify"], timeout=cfg["timeout"]) as client:
            r = client.get(f"{cfg['api_url']}/version")
        report.append(f"[3/4] OK   — HTTP: /version status={r.status_code}")
    except httpx.HTTPError as exc:
        report.append(f"[3/4] FAIL — HTTP/TLS: {type(exc).__name__}: {exc}")
        return "\n".join(report)

    # 4) Auth
    try:
        data = _ocp_get("/apis/user.openshift.io/v1/users/~")
        user = data.get("metadata", {}).get("name", "?")
        report.append(f"[4/4] OK   — Auth: kullanıcı={user}")
    except Exception as exc:  # noqa: BLE001
        # OpenShift user API yoksa (saf k8s) SelfSubjectReview deneyelim
        try:
            data = _ocp_get("/apis/authentication.k8s.io/v1/selfsubjectreviews")
            user = data.get("status", {}).get("userInfo", {}).get("username", "?")
            report.append(f"[4/4] OK   — Auth (k8s): kullanıcı={user}")
        except Exception as exc2:  # noqa: BLE001
            report.append(f"[4/4] FAIL — Auth: {exc} / fallback: {exc2}")

    return "\n".join(report)


@mcp.tool()
def oc_namespace_exists(name: str = "") -> str:
    """Verilen namespace'in cluster'da var olup olmadığını kontrol eder.
    Parametre verilmezse .env'deki OPENSHIFT_NAMESPACE kullanılır.
    """
    try:
        ns = _resolve_namespace(name)
    except ValueError as exc:
        return f"Hata: {exc}"

    cfg = _ocp_settings()
    url = f"{cfg['api_url']}/api/v1/namespaces/{ns}"
    with httpx.Client(verify=cfg["verify"], timeout=cfg["timeout"]) as client:
        r = client.get(url, headers=cfg["headers"])

    if r.status_code == 200:
        phase = r.json().get("status", {}).get("phase", "?")
        return f"VAR   — '{ns}' namespace mevcut (phase: {phase})."
    if r.status_code == 404:
        return f"YOK   — '{ns}' namespace cluster'da bulunamadı."
    if r.status_code == 403:
        return (
            f"BELİRSİZ — '{ns}' için 'get namespaces' yetkin yok (403). "
            "ServiceAccount cluster-wide listeleme yapamıyor olabilir; "
            "namespace içinde başka bir GET (ör. pod listesi) deneyelim."
        )
    if r.status_code == 401:
        return "Hata: 401 Unauthorized — token geçersiz veya süresi dolmuş."
    return f"Hata: beklenmeyen status {r.status_code} — {r.text[:200]}"


@mcp.tool()
def oc_list_pods(namespace: str = "") -> str:
    """Belirtilen namespace'teki pod'ları listeler (ad, faz, restart, yaş).
    Parametre verilmezse .env'deki OPENSHIFT_NAMESPACE kullanılır.
    """
    try:
        ns = _resolve_namespace(namespace)
    except ValueError as exc:
        return f"Hata: {exc}"

    data = _ocp_get(f"/api/v1/namespaces/{ns}/pods")
    items = data.get("items", []) or []
    if not items:
        return f"'{ns}' namespace'inde hiç pod yok."

    lines = [f"'{ns}' namespace'inde {len(items)} pod:"]
    lines.append(f"{'NAME':<55} {'STATUS':<12} {'RESTARTS':<10} AGE")
    for pod in items:
        meta = pod.get("metadata", {})
        status = pod.get("status", {})
        name = meta.get("name", "?")
        phase = status.get("phase", "?")
        restarts = sum(
            (cs.get("restartCount", 0) or 0)
            for cs in (status.get("containerStatuses") or [])
        )
        age = _humanize_age(meta.get("creationTimestamp", ""))
        lines.append(f"{name:<55} {phase:<12} {restarts:<10} {age}")
    return "\n".join(lines)


@mcp.tool()
def oc_list_configmaps(namespace: str = "") -> str:
    """Bir namespace'teki ConfigMap'leri özet olarak listeler (ad, key sayısı, yaş).
    Parametre verilmezse .env'deki OPENSHIFT_NAMESPACE kullanılır.

    Burada içerik DÖNDÜRÜLMEZ; ayrıntı için `oc_get_configmap` kullan.
    """
    try:
        ns = _resolve_namespace(namespace)
    except ValueError as exc:
        return f"Hata: {exc}"

    data = _ocp_get(f"/api/v1/namespaces/{ns}/configmaps")
    items = data.get("items", []) or []
    if not items:
        return f"'{ns}' namespace'inde ConfigMap yok."

    lines = [f"'{ns}' namespace'inde {len(items)} ConfigMap:"]
    lines.append(f"{'NAME':<45} {'KEYS':<6} AGE")
    for cm in items:
        meta = cm.get("metadata", {})
        name = meta.get("name", "?")
        key_count = len(cm.get("data", {}) or {}) + len(cm.get("binaryData", {}) or {})
        age = _humanize_age(meta.get("creationTimestamp", ""))
        lines.append(f"{name:<45} {key_count:<6} {age}")
    return "\n".join(lines)


@mcp.tool()
def oc_get_configmap(name: str, namespace: str = "") -> str:
    """Belirli bir ConfigMap'in tüm key/value içeriğini döner.
    Parametre verilmezse .env'deki OPENSHIFT_NAMESPACE kullanılır.

    Not: ConfigMap'ler hassas bilgi tutmamalı; eğer secret bilgi varsa Secret kullanılmalı.
    Binary veriler base64 olarak gösterilir.
    """
    if not name.strip():
        return "Hata: ConfigMap adı boş olamaz."
    try:
        ns = _resolve_namespace(namespace)
    except ValueError as exc:
        return f"Hata: {exc}"

    cm = _ocp_get(f"/api/v1/namespaces/{ns}/configmaps/{name}")

    text_data: dict[str, str] = cm.get("data", {}) or {}
    binary_data: dict[str, str] = cm.get("binaryData", {}) or {}

    if not text_data and not binary_data:
        return f"'{ns}/{name}' ConfigMap'i mevcut ama içeriği boş."

    lines = [f"# ConfigMap: {ns}/{name}"]
    for key, value in text_data.items():
        lines.append(f"\n--- key: {key} ({len(value)} chars) ---\n{value}")
    for key, value in binary_data.items():
        lines.append(f"\n--- key: {key} (binary, base64, {len(value)} chars) ---\n{value}")
    return "\n".join(lines)


@mcp.tool()
def oc_scale_deployment(name: str, replicas: int, namespace: str = "") -> str:
    """Bir Deployment'ın replica sayısını değiştirir. (YAZMA OPERASYONU!)
    Parametre verilmezse .env'deki OPENSHIFT_NAMESPACE kullanılır.

    Güvenlik bantları:
      - Replikalar 0 ile OPENSHIFT_MAX_REPLICAS (.env, default 10) arasında olmalı.
      - Sadece `scale` alt-kaynağı (subresource) PATCH'lenir; başka spec alanına dokunulmaz.
      - Eski → yeni replika değeri çıktıda raporlanır.
    """
    if not name.strip():
        return "Hata: Deployment adı boş olamaz."
    try:
        ns = _resolve_namespace(namespace)
    except ValueError as exc:
        return f"Hata: {exc}"

    if not isinstance(replicas, int) or replicas < 0:
        return "Hata: replicas negatif olmayan bir tamsayı olmalı."

    max_replicas = int(os.environ.get("OPENSHIFT_MAX_REPLICAS", "10"))
    if replicas > max_replicas:
        return (
            f"Reddedildi: istenen replica={replicas}, izinli üst sınır="
            f"{max_replicas}. Üst sınırı yükseltmek için .env > OPENSHIFT_MAX_REPLICAS."
        )

    scale_path = f"/apis/apps/v1/namespaces/{ns}/deployments/{name}/scale"

    try:
        current = _ocp_get(scale_path)
    except RuntimeError as exc:
        return f"Mevcut scale okunamadı: {exc}"
    old_replicas = current.get("spec", {}).get("replicas", "?")

    if old_replicas == replicas:
        return f"Değişiklik gerek yok: '{ns}/{name}' zaten {replicas} replikada."

    patch_body = {"spec": {"replicas": replicas}}
    try:
        updated = _ocp_request(
            "PATCH",
            scale_path,
            body=patch_body,
            content_type="application/merge-patch+json",
        )
    except RuntimeError as exc:
        return f"PATCH başarısız: {exc}"

    new_replicas = updated.get("spec", {}).get("replicas", "?")
    warning = "  ⚠️  Bu işlem pod'ları KAPATIR!" if replicas == 0 else ""
    return (
        f"OK — '{ns}/{name}' Deployment scale güncellendi: "
        f"{old_replicas} → {new_replicas}.{warning}"
    )


if __name__ == "__main__":
    mcp.run()
