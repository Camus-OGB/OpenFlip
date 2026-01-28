# OpenFlip

**Open source alternative to Heyzine.** Transform your PDFs into interactive flipbooks with realistic page-turning effects. Self-hostable and free.

![OpenFlip](https://img.shields.io/badge/version-1.1.0-purple) ![License](https://img.shields.io/badge/license-MIT-green) ![Python](https://img.shields.io/badge/python-3.8+-blue) ![Docker](https://img.shields.io/badge/docker-ready-green)

## ✨ Features

- 📤 **Drag & drop upload** with custom title input
- 📖 **Hybrid reader** with multiple viewing modes:
  - **Standard** (turn.js) - Realistic double-page flipbook effect
  - **Coverflow** - 3D carousel view
  - **Cards** - Stacked cards effect
  - **Cube** - 3D cube transition
  - **Slide/Fade** - Smooth crossfade transition
- 🎯 **Smart navigation**:
  - Click-based (left/right halves of page)
  - Keyboard shortcuts (arrows, space, home/end)
  - Navigation buttons in control bar
  - One page advance at a time
- 🔍 **Zoom** in/out (0.5x to 2x)
- 🔗 **Interactive widgets** - Clickable links with visible text
- 📱 **Fully responsive** - Desktop, tablet, mobile
- 🎨 **Consistent display** - Fixed A4-like dimensions for all PDFs
- 🏠 **Gallery** - Browse and manage all flipbooks
- 🐳 **Docker-ready** - Deploy in one command
- 🔒 **Privacy-first** - Your files stay on your server

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

## Recent Improvements (v1.1.0)

- ✨ Fixed A4 page dimensions for consistent display across all PDFs
- 🎯 Improved navigation with click-based page turning
- 🔘 Added prev/next buttons for easier navigation
- 🔗 Links now display their text directly on flipbook pages
- ⚡ Fixed Swiper navigation to advance exactly one page at a time
- 🔊 Optimized audio system (flip-1.mp3, flip-4.mp3)
- 📐 Better centering and responsive layout

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ← / ↑ | Previous page |
| → / ↓ / Space | Next page |
| Home | First page |
| End | Last page |
| +/= | Zoom in |
| - | Zoom out |
| 0 | Reset zoom |
| F | Fullscreen |
| S | Toggle sound |

## Mouse Navigation

- **Left half of page** - Click to go to previous page
- **Right half of page** - Click to go to next page
- **Prev/Next buttons** - Use navigation buttons in control bar

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
