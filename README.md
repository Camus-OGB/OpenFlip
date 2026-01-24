# OpenFlip

Transformez vos PDF en flipbooks interactifs avec effet de page tournée réaliste. Open source et auto-hébergeable.

![OpenFlip](https://img.shields.io/badge/version-1.0.0-purple) ![License](https://img.shields.io/badge/license-MIT-green)

## Fonctionnalités

- 📤 **Upload drag & drop** de fichiers PDF
- 📖 **Flipbook interactif** avec animation de page tournée (turn.js)
- 🔍 **Zoom** avant/arrière
- 📄 **Mode d'affichage** : single ou double page
- ✏️ **Titre personnalisable** pour chaque flipbook
- ⌨️ **Navigation clavier** et tactile (swipe)
- 📱 **Responsive** : desktop, tablette, mobile
- 🏠 **Galerie** des derniers flipbooks sur la page d'accueil
- 🐳 **Docker-ready** : déploiement en une commande

## Démarrage rapide

```bash
git clone https://github.com/openflip/openflip.git
cd openflip
docker compose up -d
```

L'application sera disponible sur **http://localhost:8000**

## Configuration

Créez un fichier `.env` à la racine (optionnel) :

```bash
PORT=8000
MAX_FILE_SIZE=52428800  # 50MB
```

## Raccourcis clavier

| Touche | Action |
|--------|--------|
| ← ↑ | Page précédente |
| → ↓ Espace | Page suivante |
| Home | Première page |
| End | Dernière page |
| + / - | Zoom avant/arrière |
| D | Mode single/double |
| F | Plein écran |

## Commandes Docker

```bash
docker compose up -d          # Démarrer
docker compose logs -f        # Voir les logs
docker compose down           # Arrêter
docker compose up -d --build  # Rebuild
```

## Stack technique

- **Backend** : FastAPI + Python 3.11
- **Frontend** : HTML/CSS/JS + Tailwind CSS + turn.js
- **Conversion PDF** : pdf2image + Poppler
- **Conteneurisation** : Docker

## Structure du projet

```
openflip/
├── app/                  # Module Python
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── models.py         # Store documents
│   ├── routes.py         # Routes API
│   └── services.py       # Conversion PDF
├── static/               # Frontend
│   ├── index.html        # Page d'accueil + galerie
│   ├── upload.html       # Upload PDF
│   └── reader.html       # Lecteur flipbook
├── storage/              # PDFs et images générées
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/` | GET | Page d'accueil |
| `/upload` | GET | Page d'upload |
| `/reader/{id}` | GET | Lecteur flipbook |
| `/api/upload` | POST | Upload PDF |
| `/api/documents` | GET | Liste des flipbooks |
| `/api/documents/{id}` | GET | Détails d'un flipbook |
