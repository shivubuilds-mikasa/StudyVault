<div align="center">

![StudyVault animated header](assets/studyvault-motion.gif)

# StudyVault

**A focused, animated home for a CSE semester library.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-9b761c?style=flat-square)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-9b761c?style=flat-square)](https://fastapi.tiangolo.com/)
[![Responsive](https://img.shields.io/badge/Layout-phone%20%7C%20tablet%20%7C%20desktop-c9a33b?style=flat-square)](#responsive-by-design)

</div>

StudyVault organizes modules, past papers, mid-semester materials, and exam dates in one lightweight interface. The local version keeps your files on your own computer.

## What’s inside

- A cinematic dashboard with subject summaries and exam runway
- Subject library, PYQ explorer, and exam timetable
- Inline PDF preview, slide-text preview, and separate downloads
- Scroll reveals, pointer light, card depth, magnetic controls, and subtle interaction sparks
- Phone-first bottom navigation, tablet layouts, and reduced-motion support
- FastAPI backend with a small local SQLite index

## Run locally

Use Python 3.10 or later. From the project root:

```powershell
python -m pip install -r 05_Web_Application/requirements.txt
Set-Location 05_Web_Application
python -m uvicorn server:app --host 127.0.0.1 --port 8765
```

Then open [http://127.0.0.1:8765](http://127.0.0.1:8765). Keep your course materials in the matching `01_Subjects/<subject>/Modules`, `PYQs`, and `Mid_Sem` folders; use **Manage files → Rescan library** after adding files.

## Responsive by design

At phone widths the navigation becomes a thumb-friendly bottom dock, stats use a compact two-column layout, and filters scroll horizontally. Tablet widths keep the sidebar while balancing the content grid. Safe-area insets and touch input are handled, and hover-only effects stay off touch screens.

## Motion with care

The UI uses local CSS and a small amount of delegated JavaScript. It respects `prefers-reduced-motion`, avoids animation libraries, and keeps scroll work frame-limited.

## Deploy a public demo

[![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/shivubuilds-mikasa/StudyVault)

The included `render.yaml` creates a free Singapore web service from this repository. It runs the FastAPI app with the empty library that is in the public repo. It does not contain your study files or local database. Free Render services spin down after 15 minutes without traffic, so the first visit after a quiet period may take a little longer.

## Your files stay yours

The public repository contains application source and the animated README artwork only. It intentionally excludes course documents, backups, the SQLite index, file inventories, and verification records. The app has no login, so run it locally with your own library. A public deployment must remain an empty demo unless you separately choose a protected hosting setup for your files.

## Stack

Python · FastAPI · SQLite · HTML · CSS · JavaScript
