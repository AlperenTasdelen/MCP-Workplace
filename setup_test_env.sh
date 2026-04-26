#!/bin/bash
echo "=========================================="
echo "Aphrodite MCP Test Environment Kurulumu"
echo "=========================================="

echo "[1/4] VENV oluşturuluyor (test_venv)..."
python3 -m venv test_venv

echo "[2/4] Sanal ortam aktive ediliyor..."
source test_venv/bin/activate

echo "[3/4] Gerekli bağımlılıklar yükleniyor..."
pip install --upgrade pip
pip install openai httpx mcp python-dotenv

echo "=========================================="
echo "✅ Kurulum Tamamlandı!"
echo " "
echo "Sistemi test etmek için sırasıyla şu komutları girin:"
echo "1) source test_venv/bin/activate"
echo "2) python interactive_chat.py"
echo "=========================================="
