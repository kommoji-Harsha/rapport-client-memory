# Rapport Frontend

Rapport is a client-memory agent for freelancers and consultants. The frontend is built as a warm, personal CRM interface inspired by Linear and Notion's clean, light surfaces.

## Features
- **Client Switcher:** Select synthetic client profiles with colored initial avatars.
- **Reply Workbench:** Paste incoming messages with sample message chips, Memory ON/OFF toggling, and side-by-side Compare View.
- **Response Result:** Editable draft reply, Client Brief with clickable source citations, Risk Flags cards, and model status indicators.
- **Source Drawer:** Slide-over modal displaying complete memory details and Hindsight per-arm recall scores (`final`, `reranker`, `semantic`, `keyword`).
- **Memory Panel:** Recalled history list and consolidated behavior patterns ("Observations" tab calling `/api/memory/observations`).
- **Feedback Loop:** "Went well" / "Pushback" outcome buttons wired to `/api/feedback`.
- **History Import:** Paste old threads/notes for history retention via `/api/import`.
- **Diagnostics:** `CrossClientSanityBadge` verifying strict tag isolation.
- **Learning Curve Page:** Task 3 evaluation placeholder layout.

## Getting Started

### Installation
```bash
npm install
```

### Development Server
```bash
npm run dev
```

### Type Checking
```bash
npm run typecheck
```

### Running Tests
```bash
npm test
```

### Production Build
```bash
npm run build
```
