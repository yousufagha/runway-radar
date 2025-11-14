# Fashion Trend Spotter

Identify rising and declining fashion elements by combining runway image analytics with social media and editorial text intelligence.

## Pipelines overview
- **Image pipeline**: detector-led garment spotting, CLIP-style visual embeddings, palette extraction, runway metadata coordination.
- **Text pipeline**: corpus loaders, cleaning routines, transformer + VADER sentiment scoring, frequency tracking of garments, colours, designers and aesthetics.
- **Trend scoring**: popularity index, mention-driven adoption curves, rising-vs-declining rankings for styles, colours and brands.
- **Visual outputs**: palette bars, brand/garment mention charts, sentiment/mention line plots, interactive dashboards via matplotlib and plotly.

## Repository layout
```
docs/           – detailed context and assistant prompts
notebooks/      – exploratory notebooks and reports
src/            – reusable modules for image, text, scoring and visualisation pipelines
requirements.txt – dependency pin list
```

## Setup
1. `python -m venv .venv` and activate the virtual environment (`.\.venv\Scripts\Activate.ps1` on PowerShell).
2. `pip install -r requirements.txt`
3. Launch notebooks once created: `jupyter notebook` (then open `notebooks/00_project_overview.ipynb`).
