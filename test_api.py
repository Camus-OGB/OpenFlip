#!/usr/bin/env python3
"""
Script de test pour vérifier l'API Reader
"""
import requests
import json
import sys

# URL de votre serveur Render
BASE_URL = "https://openflip-xxxx.onrender.com"  # Remplacer par votre URL Render

def test_reader_api(doc_id):
    """Test l'endpoint /api/reader/{doc_id}"""
    print(f"\n🔍 Test API Reader pour: {doc_id}")
    print("=" * 60)
    
    try:
        url = f"{BASE_URL}/api/reader/{doc_id}"
        print(f"GET {url}")
        
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Réponse reçue:")
            print(f"  - ID: {data.get('id')}")
            print(f"  - Titre: {data.get('title')}")
            print(f"  - Pages: {data.get('page_count')}")
            print(f"  - Style: {data.get('style')}")
            
            if data.get('pages'):
                first_page = data['pages'][0]
                print(f"\n📄 Première page:")
                print(f"  - page_num: {first_page.get('page_num')}")
                print(f"  - image_url: {first_page.get('image_url')}")
                print(f"  - image_path: {first_page.get('image_path')}")
                print(f"  - Widgets: {len(first_page.get('widgets', []))}")
                
                # Tester si l'image est accessible
                img_url = first_page.get('image_url')
                if img_url:
                    test_image_url(img_url)
        else:
            print(f"❌ Erreur: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_image_url(img_url):
    """Teste si une image est accessible"""
    print(f"\n🖼️  Test d'accès à l'image: {img_url}")
    
    try:
        response = requests.head(f"{BASE_URL}{img_url}", timeout=5)
        if response.status_code == 200:
            print(f"  ✅ Image accessible ({response.headers.get('content-length')} bytes)")
        else:
            print(f"  ❌ Image introuvable ({response.status_code})")
    except Exception as e:
        print(f"  ❌ Erreur: {e}")

def test_local():
    """Test en local (http://localhost:8000)"""
    print("\n📍 Test EN LOCAL (http://localhost:8000)")
    print("=" * 60)
    
    # Récupérer la liste des flipbooks
    try:
        response = requests.get("http://localhost:8000/api/flipbooks", timeout=5)
        if response.status_code == 200:
            flipbooks = response.json()
            if flipbooks:
                print(f"✅ {len(flipbooks)} flipbooks trouvés")
                first_fb = flipbooks[0]
                print(f"\nPremier flipbook:")
                print(f"  - ID: {first_fb.get('id')}")
                print(f"  - Titre: {first_fb.get('title')}")
                print(f"  - Pages: {first_fb.get('pages')}")
                
                # Tester l'API reader
                test_reader_api(first_fb['id'])
            else:
                print("⚠️  Aucun flipbook trouvé")
        else:
            print(f"❌ Erreur: {response.status_code}")
    except Exception as e:
        print(f"❌ Impossible de se connecter à localhost:8000 ({e})")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        doc_id = sys.argv[1]
        test_reader_api(doc_id)
    else:
        test_local()
