# RayCal project page (anonymous, for review)

Static page with no build step: `index.html`, `assets/css/style.css`, `assets/js/explorer.js`.
Open `index.html` through any static server, e.g. `python3 -m http.server` in this folder.

## Contents
- `assets/figures/`: figures rendered from the submitted paper (re-encoded JPEG, no metadata).
- `assets/results/`: results explorer data, one JPEG sprite per sequence group (`<group>.jpg`, and
  `<group>-dir.jpg` for the error-direction style) and `meta.json` with every row's offset and scores.

## Updating the results
`tools/build_results.py OUT_DIR [WORKERS]` renders `assets/results/` from the benchmark data and the reported runs.
It reads the local data root from the environment variable `RAYCAL_ROOT`.

## Keeping the page anonymous
- No author names, affiliations, logos, repository or video links, analytics, cookies or third-party fonts/scripts.
- Do not commit machine paths or user names (job scripts and logs are ignored by `.gitignore`).
- Commit with an anonymous identity: `git config user.name anonymous; git config user.email anonymous@example.com`.
- Before deploying, check: `grep -rIl -i -e "<your name>" -e "<your lab>" -e "/home/" -e "/groups/" .`
- Deploy for review through an anonymizing host (e.g. anonymous.4open.science, which can serve a repository's
  GitHub Pages under an anonymous URL) and put only that URL in the supplementary material.
