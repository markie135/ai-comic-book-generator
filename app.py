from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import streamlit as st

import ai_client
from pipeline import GenerationConfig, generate_story_draft, generate_style_draft, run_pipeline


st.set_page_config(page_title="AI Comic Book Generator", page_icon="📖", layout="wide")


DEFAULT_STYLE = "Retro handgeinkte zwart-wit mangastijl"
DEFAULT_CHARACTER_SHEET = """\
# Karakterblad

## Hoofdpersonage
- Naam: (bijv. Finn)
- Leeftijd: (bijv. 13-15)
- Uiterlijk: (bijv. donker warrig haar, witte blouse, donkere bretels)

## Dier / Partner
- Naam: (bijv. kitten)
- Uiterlijk: (bijv. zwart-wit, zwarte rug, witte borst en poten)

## Setting
- (bijv. oud stadje, bakstenen straten, bakkerij, boekwinkel)

## Consistentieregels
- Kleding en proporties identiek per pagina
- Stel terugkerende props vast (bijv. bretels, houten krat)
"""
GENRES = ["Slice of Life", "Avontuur", "Fantasy", "Mysterieuze feel-good", "Drama"]
TONES = ["Warm", "Opbeurend", "Hoopvol", "Rustig", "Komedisch licht"]
_DEFAULT_CHAR_SHEET_PATH = "character-sheets/pilot_boy_kitten_character_sheet.md"


# ---------------------------------------------------------------------------
# Session state initialisatie
# ---------------------------------------------------------------------------

def _load_default_char_sheet() -> str:
    path = Path(_DEFAULT_CHAR_SHEET_PATH)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return DEFAULT_CHARACTER_SHEET


_defaults: dict = {
    "story_text_area": "",
    "style_text_area": DEFAULT_STYLE,
    "live_logs": [],
    "generated_books": [],
    "generated_pdfs": [],
    "generation_done": False,
    "character_sheet_text": _load_default_char_sheet(),
}
for _key, _val in _defaults.items():
    if _key not in st.session_state:
        st.session_state[_key] = _val


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------

def _on_generate_story_click() -> None:
    seed = st.session_state.get("story_text_area", "")
    genre = st.session_state.get("_genre_sel", "Slice of Life")
    tone = st.session_state.get("_tone_sel", "Warm")
    draft = generate_story_draft(genre=genre, tone=tone, seed=seed)
    st.session_state.story_text_area = draft


def _on_generate_style_click() -> None:
    hint = st.session_state.get("style_text_area", "")
    draft = generate_style_draft(DEFAULT_STYLE, setting_hint=hint)
    st.session_state.style_text_area = draft


def _on_save_char_sheet() -> None:
    new_text = st.session_state.get("_char_sheet_editor", "")
    path = Path(_DEFAULT_CHAR_SHEET_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    st.session_state.character_sheet_text = new_text
    st.toast("Karakterblad opgeslagen.", icon="✅")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("We gaan een strip maken 📖")
st.caption("Van story idea naar complete pilot-output met consistente prompts, assets en PDF.")

col_ai1, col_ai2, col_ai3 = st.columns([1, 1, 4])
with col_ai1:
    if ai_client.has_openai():
        st.success("OpenAI ✓", icon="🤖")
    else:
        st.warning("OpenAI niet geconfigureerd", icon="⚠️")
with col_ai2:
    if ai_client.has_replicate():
        st.success("Replicate ✓", icon="🖼️")
    else:
        st.warning("Replicate niet geconfigureerd", icon="⚠️")

st.divider()

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_story, tab_style, tab_chars, tab_settings = st.tabs(
    ["Verhaal", "Style & Setting", "Karakterblad", "Instellingen"]
)

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
        disabled=not ai_client.has_openai(),
        help="Vereist OPENAI_API_KEY in .env" if not ai_client.has_openai() else "",
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
        disabled=not ai_client.has_openai(),
        help="Vereist OPENAI_API_KEY in .env" if not ai_client.has_openai() else "",
    )

with tab_chars:
    st.subheader("Karakterblad / Story Bible")
    st.caption(
        "Dit karakterblad wordt gebruikt als consistentiereferentie in alle pagina-prompts. "
        f"Opgeslagen als `{_DEFAULT_CHAR_SHEET_PATH}`."
    )
    st.text_area(
        "Karakterblad (Markdown)",
        value=st.session_state.character_sheet_text,
        height=480,
        key="_char_sheet_editor",
    )
    st.button(
        "Karakterblad Opslaan",
        use_container_width=True,
        on_click=_on_save_char_sheet,
        type="secondary",
    )

with tab_settings:
    st.subheader("Instellingen")

    col_left, col_right = st.columns(2)
    with col_left:
        title = st.text_input("Titel", value="De Kitten die een Vriend vond")
        num_books = st.selectbox("Aantal boeken", options=[1, 3, 5], index=0)
        num_pages = st.slider("Aantal pagina's per boek", min_value=8, max_value=120, value=10, step=1)

    with col_right:
        genre = st.selectbox("Genre", options=GENRES, index=0, key="_genre_sel")
        tone = st.selectbox("Toon", options=TONES, index=0, key="_tone_sel")
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


# ---------------------------------------------------------------------------
# Generatie
# ---------------------------------------------------------------------------

if start:
    st.session_state.live_logs = []
    st.session_state.generated_books = []
    st.session_state.generated_pdfs = []
    st.session_state.generation_done = False

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

    log_box = st.empty()
    progress_bar = st.progress(0, text="Pipeline starten...")
    total_steps = int(num_books) * int(num_pages)
    completed_steps = [0]

    def ui_log(message: str) -> None:
        st.session_state.live_logs.append(message)
        log_box.code("\n".join(st.session_state.live_logs[-150:]), language="text")
        if ": prompt" in message or ": afbeelding" in message or ": Replicate" in message:
            completed_steps[0] = min(completed_steps[0] + 1, total_steps)
            pct = int(completed_steps[0] / max(total_steps, 1) * 100)
            progress_bar.progress(pct, text=f"Stap {completed_steps[0]} / {total_steps}")

    with st.spinner("Pipeline draait..."):
        outputs = run_pipeline(config, log=ui_log)

    progress_bar.progress(100, text="Klaar!")

    project_slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-") or "comic-book"
    pdf_dir = Path(config.pdfs_root) / project_slug
    found_pdfs = sorted(pdf_dir.glob("*.pdf")) if pdf_dir.exists() else []

    st.session_state.generated_books = [str(p) for p in outputs]
    st.session_state.generated_pdfs = [str(p) for p in found_pdfs]
    st.session_state.generation_done = True


# ---------------------------------------------------------------------------
# Output sectie
# ---------------------------------------------------------------------------

if st.session_state.generation_done:
    st.success(f"Generatie afgerond — {len(st.session_state.generated_books)} boek(en) klaar.")

    if st.session_state.generated_pdfs:
        st.subheader("Download PDF's")
        for pdf_path_str in st.session_state.generated_pdfs:
            pdf_path = Path(pdf_path_str)
            if pdf_path.exists():
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        label=f"Download {pdf_path.name}",
                        data=f.read(),
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        use_container_width=True,
                    )

    st.subheader("Preview gegenereerde pagina's")
    for book_path_str in st.session_state.generated_books:
        images_dir = Path(book_path_str) / "images"
        if not images_dir.exists():
            continue

        page_images = sorted(images_dir.glob("page_*.png"))
        if not page_images:
            page_images = sorted(images_dir.glob("page_*_placeholder.svg"))

        if page_images:
            st.write(f"**{Path(book_path_str).name}**")
            cols = st.columns(min(len(page_images), 5))
            for idx, img_path in enumerate(page_images):
                with cols[idx % 5]:
                    if img_path.suffix == ".png":
                        st.image(str(img_path), caption=img_path.stem, use_container_width=True)
                    else:
                        st.code(img_path.read_text(encoding="utf-8")[:300] + "...", language="xml")


# ---------------------------------------------------------------------------
# Live log
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Live log")
if st.session_state.live_logs:
    st.code("\n".join(st.session_state.live_logs[-150:]), language="text")
else:
    st.caption("Nog geen logs.")
