# OpenFlip

Alternative open source à Heyzine. Transformez vos PDFs en flipbooks interactifs avec effets de page réalistes. Auto-hébergeable et gratuit.

![Version](https://img.shields.io/badge/version-1.1.0-purple) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![Docker](https://img.shields.io/badge/docker-ready-green)

## ✨ Fonctionnalités

- 📤 Upload par drag & drop avec titre personnalisé
- 📖 Lecteur hybride avec 5 modes (Standard, Coverflow, Cards, Cube, Slide)
- 🎯 Navigation intelligente (clic, clavier, boutons)
- 🔍 Zoom 0.5x à 2x
- 🔗 Liens interactifs extraits automatiquement du PDF
- 📱 Responsive (desktop, tablette, mobile)
- 🎨 Dimensions A4 cohérentes
- 🏠 Galerie pour gérer les flipbooks
- 🐳 Docker prêt à l'emploi
- 🔒 Données sur votre serveur

## Démarrage rapide

```bash
git clone https://github.com/Camus-OGB/OpenFlip.git
cd openflip
docker compose up -d
```

App disponible à **http://localhost:8000**

## Installation locale

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

## Configuration

Fichier `.env` (optionnel) :

```bash
PORT=8000
MAX_FILE_SIZE=52428800  # 50MB
APP_URL=http://localhost:8000
DATABASE_URL=postgresql://user:pass@host/db  # Production
```

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| ← / → | Page précédente/suivante |
| Space | Page suivante |
| Home / End | Première/dernière page |
| +/- | Zoom in/out |
| F | Plein écran |
| S | Son |

## Commandes Docker

```bash
docker compose up -d          # Démarrer
docker compose logs -f        # Logs
docker compose down           # Arrêter
docker compose up -d --build  # Reconstruire
```

## Stack technique

- **Backend** : FastAPI + Python 3.11
- **Frontend** : HTML/CSS/JS + Tailwind
- **Lecteur** : turn.js + Swiper.js
- **PDF** : PyMuPDF → WebP
- **DB** : SQLite (dev) / PostgreSQL (prod)
- **Container** : Docker

## Structure du projet

```
openflip/
├── app/           # Backend
│   ├── main.py
│   ├── routes.py
│   ├── models.py
│   └── services.py
├── static/        # Frontend
│   ├── index.html
│   ├── upload.html
│   ├── reader.html
│   └── gallery.html
├── storage/       # Fichiers générés
├── Dockerfile
└── requirements.txt
```

## API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/api/upload` | POST | Uploader un PDF |
| `/api/documents` | GET | Liste des flipbooks |
| `/api/documents/{id}` | GET/DELETE | Détails/Supprimer |
| `/reader/{id}` | GET | Lecteur |
| `/gallery` | GET | Galerie |

## Dépannage

| Problème | Solution |
|----------|----------|
| Conversion PDF échouée | Vérifier le PDF, voir logs : `docker compose logs` |
| Permission denied | `chmod 755 storage/` |
| Pages ne s'affichent pas | Vérifier `/app/storage/pages/{id}/` |
| DB lockée | Utiliser PostgreSQL en production |

## Dépendances

- FastAPI, Uvicorn
- PyMuPDF (PDF → WebP)
- Pillow (images)
- SQLModel (DB ORM)
- python-dotenv

## Licence

MIT
