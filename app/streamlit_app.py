import os
import sys
from pathlib import Path
from datetime import datetime

import streamlit as st
import pandas as pd

# Make sure we can import the local package even if CWD is app/
THIS_FILE = Path(__file__).resolve()
APP_DIR = THIS_FILE.parent
PROJECT_ROOT = APP_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.modules.utils import ensure_dir, load_env, color_label
from app.modules import storage
from app.modules import llm
from app.modules import scoring


APP_TITLE = "Fashion Trend Spotter"
DB_PATH = os.path.join("data", "trends.db")
UPLOAD_DIR_IMG = os.path.join("data", "images")


def _nice_label(s: str) -> str:
    label = (s or "").replace("-", " ").title()
    return {"Openai": "OpenAI"}.get(label, label)


def _domain(u: str) -> str:
    try:
        from urllib.parse import urlparse
        d = urlparse(u).netloc.lower()
        return d.replace("www.", "")
    except Exception:
        return ""


def _palette_html(colors):
    if not colors:
        return ""
    chips = "".join([
        f'<span style="display:inline-block;width:16px;height:16px;border-radius:8px;'
        f'background:{c};margin-right:6px;border:1px solid rgba(0,0,0,0.1)"></span>' for c in colors[:8]
    ])
    return f'<div style="margin-top:4px;">{chips}</div>'


def _sentiment_badge(val):
    try:
        v = float(val)
    except Exception:
        v = 0.0
    if v >= 0.5:
        text, bg = "Positive", "#DCFCE7"
    elif v >= 0.2:
        text, bg = "Upbeat", "#E7F6FF"
    elif v > -0.2:
        text, bg = "Neutral", "#F3F4F6"
    elif v > -0.5:
        text, bg = "Cautious", "#FEF3C7"
    else:
        text, bg = "Negative", "#FEE2E2"
    return f'<span style="background:{bg};padding:4px 8px;border-radius:999px;font-size:12px;">{text}</span>'


def _chips(items, bg="#EEF2FF"):
    if not items:
        return ""
    pills = "".join([
        f'<span style="background:{bg};padding:3px 8px;border-radius:999px;margin-right:6px;margin-top:4px;display:inline-block;font-size:12px;">{str(i)}</span>'
        for i in items[:6]
    ])
    return f'<div style="margin-top:6px;">{pills}</div>'


def render_header():
    st.markdown(
        """
        <div style="padding: 20px 0 10px 0; border-bottom: 1px solid #e6eaf2;">
          <div style="font-size: 34px; font-weight: 700; color: #111827;">Fashion Trend Spotter</div>
          <div style="font-size: 14px; color: #6b7280;">Curate runway looks from trusted links and turn them into elegant, decision-ready insights.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer():
    st.markdown(
        """
        <div style="margin-top: 24px; padding: 12px 0; border-top: 1px solid #e6eaf2; color:#6b7280; font-size:12px;">
          <span>All data is stored locally in <code>data/trends.db</code>. Optional local AI via Ollama. &copy; Fashion Trend Spotter.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def init():
    ensure_dir("data")
    ensure_dir(UPLOAD_DIR_IMG)
    storage.init_db(DB_PATH)
    load_env()


def page_curate():
    st.subheader("Curate")
    st.caption("Paste links to runway articles or posts. We'll fetch the page, choose the best runway image, extract key details, and analyze them. Or enter an event name to auto-discover sources and past events.")

    try:
        from app.modules import sources as _sources
    except Exception:
        st.info("To enable curation, install: requests, beautifulsoup4, feedparser (then restart the app).")
        return

    event_name = st.text_input("Event name (optional)", placeholder="Chanel Couture Fall-Winter 2025 Paris", help="Used to discover related coverage and previous seasons.")

    urls_text = st.text_area(
        "Paste links (one per line)",
        placeholder="https://magazine.com/fall-winter-runway...\nhttps://brand.com/show...",
        height=140,
        help="Paste one link per line. Mix RSS feeds and article pages — we'll detect each.",
    )
    source_type = st.selectbox("Source type", ["magazine", "social", "other"], index=0, format_func=_nice_label, help="Label the origin for better source analytics.")

    dis_col1, dis_col2, dis_col3 = st.columns([1,1,1])
    with dis_col1:
        discover_now = st.button("Discover Sources", use_container_width=True)
    with dis_col2:
        discover_prev = st.button("Discover Previous Events", use_container_width=True)
    with dis_col3:
        curate_btn = st.button("Curate & Analyze", use_container_width=True)

    if discover_now and event_name:
        try:
            from app.modules.discovery import discover_news_links, discover_reddit_links
            links = discover_news_links(event_name, max_links=15) + discover_reddit_links(event_name, max_links=10)
            if links:
                existing = st.session_state.get("curate_urls", "").strip()
                block = "\n".join(links)
                st.session_state.curate_urls = (existing + ("\n" if existing else "") + block).strip()
                st.experimental_rerun()
            else:
                st.info("No links found yet — try a different phrasing or paste a source.")
        except Exception:
            st.info("Discovery requires internet access; please try manual links if unavailable.")

    if discover_prev and event_name:
        try:
            from app.modules.discovery import generate_previous_event_names, discover_news_links
            names = generate_previous_event_names(event_name, count=3)
            found = []
            for nm in names:
                found.extend(discover_news_links(nm, max_links=10))
            if found:
                existing = st.session_state.get("curate_urls", "").strip()
                block = "\n".join(found)
                st.session_state.curate_urls = (existing + ("\n" if existing else "") + block).strip()
                st.experimental_rerun()
            else:
                st.info("No previous events found via feeds; paste a few articles manually.")
        except Exception:
            st.info("Discovery requires internet access; please try manual links if unavailable.")

    if curate_btn:
        lines = [u.strip() for u in (urls_text or "").splitlines() if u.strip()]
        if not lines:
            st.warning("Please paste at least one link.")
            return
        results_all = []
        prog = st.progress(0)
        for i, u in enumerate(lines, start=1):
            # Detect feed vs article: try parsing as feed first
            is_feed = False
            try:
                import feedparser
                f = feedparser.parse(u)
                if getattr(f, 'entries', None):
                    is_feed = True
            except Exception:
                is_feed = False

            if is_feed:
                # limit=None -> ingest all available items from the feed
                res_list = _sources.ingest_from_rss(DB_PATH, UPLOAD_DIR_IMG, u, limit=None, source_type=source_type, event_name=event_name or None)
                results_all.extend(res_list)
            else:
                res = _sources.ingest_from_url(DB_PATH, UPLOAD_DIR_IMG, u, source_type=source_type, event_name=event_name or None)
                results_all.append(res)
            prog.progress(i / len(lines))

        ok = sum(1 for r in results_all if r.get("ok"))
        st.success(f"Curation complete — {ok}/{len(results_all)} items processed.")

        # Gallery cards
        good = [r for r in results_all if r.get("ok")]
        if good:
            st.markdown("### Gallery")
            cols = st.columns(3)
            for idx, r in enumerate(good):
                col = cols[idx % 3]
                with col:
                    img_path = None
                    if r.get("filename"):
                        img_path = os.path.join(UPLOAD_DIR_IMG, r["filename"])
                    img_url = r.get("image_url")
                    if img_path and os.path.exists(img_path):
                        st.image(img_path, use_container_width=True)
                    elif img_url:
                        st.image(img_url, use_container_width=True)

                    d = _domain(r.get("page_url", ""))
                    href = r.get("page_url") or r.get("image_url") or ""
                    label = d or 'Source'
                    if href:
                        st.markdown(f"**[{label}]({href})**")
                    else:
                        st.markdown(f"**{label}**")
                    # Explain selection logic in user-friendly terms
                    st.caption("Why this image: selected as the page’s lead runway photo. We evaluate Open Graph images and in‑page photos, prefer runway‑keyword paths (runway, show, look), and avoid thumbnails.")
                    # Sentiment badge
                    sent = r.get("sentiment")
                    st.markdown(_sentiment_badge(sent), unsafe_allow_html=True)
                    # Palette chips
                    st.markdown(_palette_html(r.get("palette")), unsafe_allow_html=True)
                    # Tags chips
                    analysis = r.get("analysis") or {}
                    g = analysis.get("garments") or []
                    s = analysis.get("styles") or []
                    if g:
                        st.markdown(_chips(g, bg="#E0E7FF"), unsafe_allow_html=True)
                    if s:
                        st.markdown(_chips(s, bg="#FFE4F1"), unsafe_allow_html=True)

        bad = [r for r in results_all if not r.get("ok")]
        if bad:
            with st.expander("Notes"):
                for b in bad[:10]:
                    st.write("- ", b.get("error"), b.get("page_url") or b.get("image_url"))

    # Quick preset feeds to accelerate ingestion
    try:
        from app.modules.presets import PRESET_FEEDS
    except Exception:
        PRESET_FEEDS = {}
    if PRESET_FEEDS:
        with st.expander("Quick Add: Fashion Feeds"):
            st.caption("Select curated collections of reputable fashion feeds to quickly populate the dataset.")
            cols = st.columns(2)
            chosen = []
            for i, (group, urls) in enumerate(PRESET_FEEDS.items()):
                with cols[i % 2]:
                    if st.checkbox(group, value=(group in ("Editorial", "Streetwear"))):
                        chosen.extend(urls)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Add Selected Feeds to List"):
                    existing = st.session_state.get("curate_urls", "").strip()
                    block = "\n".join(chosen)
                    st.session_state.curate_urls = (existing + ("\n" if existing else "") + block).strip()
                    st.experimental_rerun()
            with c2:
                if st.button("Ingest Selected Feeds Now"):
                    # Use sources module to ingest all items
                    try:
                        from app.modules import sources as _sources
                    except Exception:
                        st.error("Optional ingestion dependencies missing.")
                    else:
                        all_results = []
                        prog = st.progress(0)
                        for i, feed in enumerate(chosen, start=1):
                            res_list = _sources.ingest_from_rss(DB_PATH, UPLOAD_DIR_IMG, feed, limit=None, source_type="magazine")
                            all_results.extend(res_list)
                            prog.progress(i / max(1, len(chosen)))
                        ok2 = sum(1 for r in all_results if r.get("ok"))
                        st.success(f"Ingested {ok2}/{len(all_results)} items from selected feeds.")


def _focus_map():
    return {
        "color": "Colors",
        "garment": "Silhouettes",
        "style": "Styles",
        "designer": "Designers",
        "brand": "Brands",
        "trend": "Trends",
        "catalyst": "Cultural Drivers",
    }


def _focus_label(key: str) -> str:
    return _focus_map().get(key, _nice_label(key))


def page_dashboard():
    st.subheader("Insights")

    query = st.text_input(
        "Ask a question (optional)",
        placeholder="Rank colors by popularity this week",
        help="Natural-language filter. Examples: 'Compare silhouettes this month', 'Show designers by sentiment'.",
    )
    parsed = None
    if query.strip():
        try:
            parsed = llm.interpret_query(query)
        except Exception:
            parsed = None

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            entity_type = st.selectbox("Focus", ["color", "garment", "style", "designer", "brand", "trend", "catalyst"], index=0, format_func=_focus_label, help="What to analyze: colors, silhouettes, styles, designers, brands or cultural drivers.")
        with col2:
            timeframe = st.selectbox("Timeframe", ["all", "week", "month"], index=0, format_func=_nice_label, help="Analyze recent activity (week/month) or all data.")
        with col3:
            event_filter = st.text_input("Event filter (optional)", placeholder="Chanel Couture Fall-Winter 2025", help="Focus analytics on a single event name if provided.")

    if parsed:
        entity_type = parsed.get("entity_type", entity_type)
        timeframe = parsed.get("timeframe", timeframe)

    st.markdown("### Runway Overview")
    agg_df = scoring.aggregate_popularity(DB_PATH, entity_type=entity_type, timeframe=timeframe, event=event_filter or None)
    if agg_df.empty:
        st.info("No data yet. Curate links to see analytics.")
        return

    import plotly.express as px
    total_entities = len(agg_df)
    total_freq = int(agg_df["freq"].sum())
    avg_sent = float(agg_df["avg_sentiment"].mean()) if not agg_df.empty else 0.0
    c1, c2, c3 = st.columns(3)
    c1.metric("Distinct Items", f"{total_entities}")
    c2.metric("Total Mentions (Internal)", f"{total_freq}")
    c3.metric("Avg Sentiment", f"{avg_sent:.2f}")

    def _sentiment_context(val: float) -> str:
        if val >= 0.5:
            return "Strongly positive buzz - standout reception."
        if val >= 0.2:
            return "Generally positive - well received."
        if val > -0.2:
            return "Mixed/neutral - room to shape the narrative."
        if val > -0.5:
            return "Cautious - notable criticism or skepticism."
        return "Negative - consider adjusting styling or messaging."

    st.caption(f"Sentiment guide: {_sentiment_context(avg_sent)}")

    # Prepare friendly labels (Colors -> Name (#hex))
    df_for_display = agg_df.copy()
    if entity_type == "color":
        try:
            df_for_display["label"] = df_for_display["entity_value"].map(color_label)
        except Exception:
            df_for_display["label"] = df_for_display["entity_value"].astype(str)
    else:
        df_for_display["label"] = df_for_display["entity_value"].astype(str)

    spotlight_count = 8
    top_df = df_for_display.head(spotlight_count)
    fig = px.bar(top_df, x="label", y="popularity_score", hover_data=["freq", "avg_sentiment"], title=f"Spotlight — Popular { _focus_label(entity_type) }")
    st.plotly_chart(fig, use_container_width=True)
    try:
        st.dataframe(top_df[["label", "freq", "avg_sentiment", "popularity_score"]].rename(columns={"label": _focus_label(entity_type)}))
    except Exception:
        st.dataframe(top_df)

    # Highlights — quick, non-technical summary
    try:
        leaders = ", ".join(top_df["label"].astype(str).head(3).tolist())
        tone = _sentiment_context(avg_sent)
        st.markdown(f"**Highlights:** {leaders} are leading right now. Overall reception is {tone.lower()}.")
    except Exception:
        pass

    st.markdown("### Trend Over Time")
    ts = scoring.timeseries_popularity(DB_PATH, entity_type=entity_type, timeframe=timeframe, top_n=spotlight_count, event=event_filter or None)
    if not ts.empty:
        ts2 = ts.copy()
        # normalize date labels
        try:
            ts2["date"] = pd.to_datetime(ts2["date"]).dt.date.astype(str)
        except Exception:
            pass
        if entity_type == "color":
            try:
                ts2["label"] = ts2["entity_value"].map(color_label)
            except Exception:
                ts2["label"] = ts2["entity_value"].astype(str)
        else:
            ts2["label"] = ts2["entity_value"].astype(str)

        # Fallback to frequency if popularity_score is all zeros
        y_col = "popularity_score"
        try:
            if float(ts2[y_col].fillna(0).abs().sum()) == 0.0:
                y_col = "freq"
        except Exception:
            pass

        title = f"{'Popularity' if y_col=='popularity_score' else 'Mentions'} Over Time — { _focus_label(entity_type) }"
        fig2 = px.line(ts2, x="date", y=y_col, color="label", title=title)
        fig2.update_traces(mode="lines+markers", marker=dict(size=8))
        fig2.update_layout(xaxis=dict(type="category", categoryorder="category ascending"))
        st.plotly_chart(fig2, use_container_width=True)
        try:
            st.dataframe(ts2[["date", "label", "freq", "avg_sentiment", "popularity_score"]].rename(columns={"label": _focus_label(entity_type)}))
        except Exception:
            st.dataframe(ts2)
    else:
        st.info("No time series available for the current selection.")

    st.markdown("### Style Pairings")
    colA, colB = st.columns(2)
    with colA:
        type_a = st.selectbox("Type A", ["color", "garment", "style", "designer", "brand", "trend"], index=0, key="coA", format_func=_nice_label)
    with colB:
        type_b = st.selectbox("Type B", ["garment", "color", "style", "designer", "brand", "trend"], index=1, key="coB", format_func=_nice_label)
    pairs = scoring.cooccurrence(DB_PATH, type_a, type_b, timeframe=timeframe, top_k=30, event=event_filter or None)
    if not pairs.empty:
        pairs2 = pairs.copy()
        if type_a == "color":
            pairs2["a"] = pairs2["a"].map(color_label)
        if type_b == "color":
            pairs2["b"] = pairs2["b"].map(color_label)
        st.dataframe(pairs2)
        try:
            pv = pairs2.pivot_table(index="a", columns="b", values="freq", fill_value=0)
            pv = pv.iloc[:15, :15]
            fig3 = px.imshow(pv, text_auto=True, aspect="auto", title=f"Pairings — {_nice_label(type_a)} × {_nice_label(type_b)}")
            st.plotly_chart(fig3, use_container_width=True)
        except Exception:
            pass
    else:
        st.info("No co-occurrence data for this selection.")

    st.markdown("### Conversation & Hype")
    try:
        from app.modules import signals
        entities = list(map(str, top_df["entity_value"].tolist()))
        smap = signals.social_mentions_for_entities(entities, timeframe=timeframe)
        social_counts = {k: v.get("count", 0) for k, v in smap.items()}
        internal_freq = {row.entity_value: int(row.freq) for row in top_df.itertuples()}
        hype = signals.hype_index(internal_freq, social_counts)
        hype_rows = []
        for ent in entities:
            hype_rows.append({
                "item": ent,
                "internal_mentions": internal_freq.get(ent, 0),
                "social_mentions": social_counts.get(ent, 0),
                "hype_index": hype.get(ent, 0.0),
            })
        hype_df = pd.DataFrame(hype_rows).sort_values("hype_index", ascending=False)
        figh = px.bar(hype_df, x="item", y="hype_index", hover_data=["internal_mentions", "social_mentions"], title="Hype Index (0-100)")
        st.plotly_chart(figh, use_container_width=True)
        st.dataframe(hype_df)
        st.caption("Hype Index blends internal mentions and social mentions. 70+ indicates strong buzz.")
        # Market appeal score (balanced by sentiment)
        appeal = []
        sent_map = {row.entity_value: float(row.avg_sentiment) for row in top_df.itertuples()}
        for ent in entities:
            hi = hype.get(ent, 0.0) / 100.0
            s = (sent_map.get(ent, 0.0) + 1.0) / 2.0  # map [-1,1] to [0,1]
            score = round((0.6 * hi + 0.4 * s) * 100.0, 1)
            label = ent
            if entity_type == "color":
                label = color_label(ent)
            appeal.append({"item": label, "appeal_score": score})
        appeal_df = pd.DataFrame(appeal).sort_values("appeal_score", ascending=False)
        st.markdown("#### Market Appeal")
        st.dataframe(appeal_df)
        if not appeal_df.empty:
            lead = appeal_df.iloc[0]
            st.caption(f"Most appealing right now: {lead['item']} — a balanced signal of buzz and positivity.")
    except Exception:
        st.info("Social signals require internet access (Reddit search). We'll show them when available.")

    st.markdown("### Sources Breakdown")
    sb = scoring.sources_breakdown(DB_PATH)
    if not sb.empty:
        fig4 = px.bar(sb, x="source", y="count", color="type", barmode="group", title="Items by Source")
        st.plotly_chart(fig4, use_container_width=True)
        st.dataframe(sb)

    csv = agg_df.to_csv(index=False).encode("utf-8")
    st.download_button("Export Current Overview CSV", csv, file_name=f"trend_{entity_type}_{timeframe}.csv", mime="text/csv")


def sidebar_settings():
    st.sidebar.header("Settings")

    backend_options = ["local-heuristic", "ollama", "openai", "auto"]
    env_backend = (os.environ.get("FASHION_TREND_BACKEND") or "local").lower()
    default_idx = {"local": 0, "ollama": 1, "openai": 2, "auto": 3}.get(env_backend, 0)
    backend = st.sidebar.selectbox("AI Backend", backend_options, index=default_idx, format_func=_nice_label, help="Free defaults: Local Heuristics or Ollama.")
    os.environ["FASHION_TREND_BACKEND"] = "local" if backend == "local-heuristic" else backend

    if backend == "openai":
        current_key = os.environ.get("OPENAI_API_KEY")
        new_key = st.sidebar.text_input("OpenAI API Key", value=current_key or "", type="password", help="Only needed if you choose the OpenAI backend.")
        if new_key and new_key != current_key:
            os.environ["OPENAI_API_KEY"] = new_key
            st.sidebar.success("API key set for this session.")
        st.sidebar.caption("Using OpenAI (gpt-4o-mini)")
    elif backend == "ollama":
        st.sidebar.caption("Using Local Ollama (llama3 / llava)")
        text_model = st.sidebar.text_input("Ollama text model", value=os.environ.get("OLLAMA_MODEL_TEXT", "llama3"))
        vision_model = st.sidebar.text_input("Ollama vision model", value=os.environ.get("OLLAMA_MODEL_VISION", "llava"))
        os.environ["OLLAMA_MODEL_TEXT"] = text_model
        os.environ["OLLAMA_MODEL_VISION"] = vision_model
        st.sidebar.info("Requires Ollama running locally. Use 'ollama pull llama3' and 'ollama pull llava'.")
    else:
        st.sidebar.caption("Using Local Heuristics Only (no model calls)")


def main():
    try:
        st.set_page_config(page_title=APP_TITLE, page_icon="👗", layout="wide")
    except Exception:
        st.set_page_config(page_title=APP_TITLE, layout="wide")
    render_header()
    init()
    sidebar_settings()

    tab1, tab2 = st.tabs(["Curate", "Analytics"])
    with tab1:
        page_curate()
    with tab2:
        page_dashboard()

    render_footer()


if __name__ == "__main__":
    main()
