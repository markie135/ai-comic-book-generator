from __future__ import annotations

from datetime import datetime
from pathlib import Path

import streamlit as st

from pipeline import GenerationConfig, generate_story_draft, generate_style_draft, run_pipeline


st.set_page_config(page_title="AI Comic Book Generator", page_icon="📖", layout="wide")


DEFAULT_STYLE = "Retro handgeinkte zwart-wit mangastijl"
GENRES = ["Slice of Life", "Avontuur", "Fantasy", "Mysterieuze feel-good", "Drama"]
TONES = ["Warm", "Opbeurend", "Hoopvol", "Rustig", "Komedisch licht"]


if "story_text" not in st.session_state:
    st.session_state.story_text = ""
if "style_text" not in st.session_state:
    st.session_state.style_text = DEFAULT_STYLE
if "live_logs" not in st.session_state:
    st.session_state.live_logs = []
if "story_text_area" not in st.session_state:
    st.session_state.story_text_area = st.session_state.story_text
if "style_text_area" not in st.session_state:
    st.session_state.style_text_area = st.session_state.style_text


def _on_generate_story_click() -> None:
    seed = st.session_state.get("story_text_area", "")
    draft = generate_story_draft(genre="Slice of Life", tone="Warm", seed=seed)
    st.session_state.story_text = draft
    st.session_state.story_text_area = draft


def _on_generate_style_click() -> None:
    hint = st.session_state.get("style_text_area", "")
    draft = generate_style_draft(DEFAULT_STYLE, setting_hint=hint)
    st.session_state.style_text = draft
    st.session_state.style_text_area = draft


st.title("We gaan een strip maken 📖")
st.caption("Van story idea naar complete pilot-output met consistente prompts, assets en PDF.")


tab_story, tab_style, tab_settings = st.tabs(["Verhaal", "Style & Setting", "Instellingen"])


with tab_story:
    st.subheader("Verhaal")
    st.text_area(
        "Schrijf je eigen verhaal of laat AI een draft maken",
        height=320,
        key="story_text_area",
        placeholder=(
            "Voorbeeld: Finn vindt een kitten in een regenachtige steeg en leert met hulp van de buurt\n"
            "wat echte zorgzaamheid betekent."
        ),
    )

    st.button(
        "AI Verhaal Genereren",
        use_container_width=True,
        on_click=_on_generate_story_click,
    )


with tab_style:
    st.subheader("Style & Setting")
    st.text_area(
        "Beschrijf visuele stijl, setting en sfeer",
        height=250,
        key="style_text_area",
        placeholder="Retro stadje, handgeinkte zwart-wit manga, zachte ochtendmist, warme buurtvibe.",
    )

    st.button(
        "AI Style Genereren",
        use_container_width=True,
        on_click=_on_generate_style_click,
    )


with tab_settings:
    st.subheader("Instellingen")

    col_left, col_right = st.columns(2)
    with col_left:
        title = st.text_input("Titel", value="De Kitten die een Vriend vond")
        num_books = st.selectbox("Aantal boeken", options=[1, 3, 5], index=0)
        num_pages = st.slider("Aantal pagina's per boek", min_value=8, max_value=120, value=10, step=1)

    with col_right:
        genre = st.selectbox("Genre", options=GENRES, index=0)
        tone = st.selectbox("Toon", options=TONES, index=0)
        style_base = st.text_input("Basistijl", value=DEFAULT_STYLE)

    extra_style_notes = st.text_area(
        "Extra style notes",
        value="Behoud karakterconsistentie in kapsel, kleding, kitten-markering en decor details.",
        height=120,
    )

    uploaded_refs = st.file_uploader(
        "Upload karakter referentie afbeeldingen",
        type=["png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
    )

    start = st.button("START GENEREREN", type="primary", use_container_width=True)


st.subheader("Live log")
log_box = st.empty()
log_box.code("\n".join(st.session_state.live_logs[-150:]) or "Nog geen logs.", language="text")


if start:
    st.session_state.live_logs = []

    upload_dir = Path("images") / "uploaded-references" / datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_dir.mkdir(parents=True, exist_ok=True)

    saved_ref_paths: list[str] = []
    for file in uploaded_refs or []:
        target = upload_dir / file.name
        target.write_bytes(file.read())
        saved_ref_paths.append(str(target))

    story_text = st.session_state.get("story_text_area", "").strip()
    style_text = st.session_state.get("style_text_area", "").strip()
    resolved_style = style_text or style_base

    config = GenerationConfig(
        title=title,
        num_books=int(num_books),
        num_pages=int(num_pages),
        genre=genre,
        tone=tone,
        style=style_base,
        story_text=story_text,
        style_notes=f"{resolved_style}\n{extra_style_notes}".strip(),
        reference_images=saved_ref_paths,
    )

    def ui_log(message: str) -> None:
        st.session_state.live_logs.append(message)
        log_box.code("\n".join(st.session_state.live_logs[-150:]), language="text")

    with st.spinner("Pipeline draait..."):
        outputs = run_pipeline(config, log=ui_log)

    output_lines = [str(path) for path in outputs]
    st.success("Generatie afgerond.")
    st.write("Gegenereerde boeken:")
    for line in output_lines:
        st.write(f"- {line}")
