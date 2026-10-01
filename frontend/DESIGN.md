# Rapport Frontend Design System

## Aesthetic & Vision
Rapport is designed as a calm, personal CRM interface tailored for consultants and freelancers. Inspired by Linear and Notion's lighter, focused workspace surfaces:
- **Tone:** Professional, clear, non-distracting, warm neutral palette.
- **Accent Color:** Warm Indigo/Amber (`#4f46e5` primary accent, `#d97706` warm amber risk highlight).
- **Typography:** Inter / Clean System Sans Scale (`sans-serif`), featuring subtle hierarchy, tabular figures for scores, and crisp contrast.
- **Theme:** Light mode by default with full Dark Mode support (`dark` class toggle on `<html>`), persisted in `localStorage`.

## Design Choices
1. **Client Avatars:** Simple colored initial badges using deterministic color hashes per client name. No external image dependencies.
2. **Icons:** Lucide React icons sized consistently (16px / 20px).
3. **Interactive States:** Every button and card includes distinct `:hover`, `:focus-visible`, `:active`, and `:disabled` states.
4. **Async & Feedback:** Explicit loading skeletons, inline spinners, retryable error alert banners, and visual confirmations.
