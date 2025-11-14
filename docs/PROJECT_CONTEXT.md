# Fashion Trend Spotter Context

## Goal
- Identify fashion elements that are trending or declining by combining runway imagery with social, editorial and entertainment text signals.
- Deliver a unified signal that surfaces colours, garments, designers and aesthetics with popularity and momentum scores.
- Support rapid reasoning by both humans and GPT assistants through clear documentation and modular code.

## Image analysis
- Source runway and fashion show imagery across seasons and designers.
- Detect garments (skirts, coats, dresses, suits, trousers, gloves) using YOLOv8 or Detectron2 models.
- Extract CLIP/DeepFashion style embeddings covering silhouettes (puffed sleeves, mini vs maxi, oversized cuts) and textures (denim, silk, leather, metallic, neutrals).
- Derive dominant colour palettes per look for palette bar plots and runway colour summaries.
- Align imagery with event metadata to trace mention surges around key shows.

## Text and sentiment analysis
- Ingest articles, reviews, captions, comments, blogs, lyrics and posts via loaders for JSON, CSV and APIs.
- Normalise text (lowe-case, whitespace cleanup, optional emoji/hashtag handling) for downstream models.
- Detect mentions of colours, garments, designers, brands, named aesthetics and cultural catalysts (celebrity outfits, viral sounds, TV/film references).
- Apply transformer-based sentiment (BERT variants) alongside VADER for baseline scoring.
- Track mention frequencies per trend element and over time windows to fuel adoption curves.

## Trend scoring and ranking
- Compute Popularity Index as sentiment-weighted frequency, e.g., `sentiment × log(1 + mentions)`.
- Monitor rising and declining trajectories via deltas in mention counts and sentiment, supporting adoption curve inference.
- Rank colours, garments, designers, textures and aesthetics by scores, momentum and sentiment.
- Store intermediate analytics (counts, sentiment averages, ranks) ready for visual outputs or reporting layers.

## Visualisation output
- Line charts showing sentiment and mention spikes before, during and after major events.
- Bar charts for brand mentions, garment popularity and adoption shifts.
- Palette bars summarising runway colour dominance using extracted colour coordinates.
- Matplotlib/Plotly dashboards for stakeholders to explore sentiment vs frequency dynamics.
