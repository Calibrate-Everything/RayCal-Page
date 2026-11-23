# RayCal project page

Static page with no build step: `index.html`, `assets/css/style.css`, `assets/js/explorer.js`.
Open `index.html` through any static server, e.g. `python3 -m http.server` in this folder.

## Contents
- `assets/figures/`: figures rendered from the submitted paper (re-encoded JPEG, no metadata).
- `assets/results/`: results explorer data, one JPEG sprite per sequence group (`<group>.jpg`, and
  `<group>-dir.jpg` for the error-direction style) and `meta.json` with every row's offset and scores.

## Updating the results
`tools/build_results.py OUT_DIR [WORKERS]` renders `assets/results/` from the benchmark data and the reported runs.
It reads the local data root from the environment variable `RAYCAL_ROOT`.

## Deployment
GitHub Pages from this repository: Settings -> Pages -> Deploy from a branch -> `main`, `/ (root)`.
The page keeps `noindex` until the arXiv version is public; remove that line in `index.html` at release.
Links marked "coming soon" (arXiv, code) are placeholders to fill in at release.
