# Auto Code Docs Portal (GitHub Pages)

This directory contains a static, multi-language product documentation portal for Auto Code.
It is intentionally focused on the real application: desktop workflows, backend entrypoints,
runtime modes, provider compatibility, operations, and roadmap status.

The portal also builds an inline Markdown reader from repository documentation so GitHub Pages can
render Markdown files directly instead of sending readers away to raw links.

## Included Languages

- English
- Russian
- French

## Local Preview

```bash
node site/scripts/build-docs-data.mjs
cd site
python -m http.server 4173
```

Open `http://localhost:4173`.

## Deployment

Deployment is handled by `.github/workflows/docs-site-pages.yml`.
The workflow regenerates `site/assets/data/docs-data.js` and uploads this `site/`
directory as the Pages artifact.
