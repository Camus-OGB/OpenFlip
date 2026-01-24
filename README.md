# OpenFlip

**Open source alternative to Heyzine.** Transform your PDFs into interactive flipbooks with realistic page-turning effects. Self-hostable and free.

![OpenFlip](https://img.shields.io/badge/version-1.0.0-purple) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- 📤 **Drag & drop upload** with custom title input
- 📖 **Hybrid reader** with multiple effects:
  - **Flipbook** (turn.js) - realistic page turn
  - **Slide** - horizontal sliding
  - **Fade** - crossfade transition
  - **Coverflow** - 3D carousel
  - **Cards** - stacked cards effect
- 🔍 **Zoom** in/out
- ⌨️ **Keyboard & touch navigation** (swipe support)
- 📱 **Responsive** - desktop, tablet, mobile
- 🏠 **Gallery page** to browse all flipbooks
- 🐳 **Docker-ready** - deploy in one command
- 🔒 **Privacy-first** - your files stay on your server

## Quick Start

```bash
git clone https://github.com/Camus-OGB/OpenFlip.git
cd openflip
docker compose up -d
```

App available at **http://localhost:8000**

## Configuration

Create a `.env` file at root (optional):

```bash
PORT=8000
MAX_FILE_SIZE=52428800  # 50MB
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ← ↑ | Previous page |
| → ↓ Space | Next page |
| Home | First page |
| End | Last page |
| + / - | Zoom in/out |
| F | Fullscreen |

## Docker Commands

```bash
docker compose up -d          # Start
docker compose logs -f        # View logs
docker compose down           # Stop
docker compose up -d --build  # Rebuild
```

## Tech Stack

- **Backend**: FastAPI + Python 3.11
- **Frontend**: HTML/CSS/JS + Tailwind CSS
- **Flipbook**: turn.js + Swiper.js (hybrid)
- **PDF Conversion**: pdf2image + Poppler
- **Container**: Docker

## Project Structure

```
openflip/
├── app/                  # Python module
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configuration
│   ├── models.py         # Document store
│   ├── routes.py         # API routes
│   └── services.py       # PDF conversion
├── static/               # Frontend
│   ├── index.html        # Homepage
│   ├── upload.html       # PDF upload (2-step)
│   ├── gallery.html      # All flipbooks
│   └── reader.html       # Hybrid flipbook reader
├── storage/              # Generated files
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage |
| `/upload` | GET | Upload page |
| `/gallery` | GET | Gallery page |
| `/reader/{id}` | GET | Flipbook reader |
| `/api/upload` | POST | Upload PDF (with optional title) |
| `/api/documents` | GET | List all flipbooks |
| `/api/documents/{id}` | GET | Get flipbook details |

## License

MIT
