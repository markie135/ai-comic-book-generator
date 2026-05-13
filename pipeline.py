from __future__ import annotations

import json
import random
import re
import shutil
import textwrap
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterable

import ai_client


LogFn = Callable[[str], None]


@dataclass
class GenerationConfig:
    title: str
    num_books: int
    num_pages: int
    genre: str
    tone: str
    style: str
    story_text: str
    style_notes: str
    output_root: str = "outputs"
    stories_root: str = "stories"
    prompts_root: str = "prompts"
    images_root: str = "images"
    pdfs_root: str = "pdfs"
    character_sheet_path: str = "character-sheets/pilot_boy_kitten_character_sheet.md"
    reference_images: list[str] = field(default_factory=list)


DEFAULT_PILOT_STORY = (
    "Op een frisse ochtend in een oud stadje vindt Finn, een jongen met donker warrig haar "
    "in witte blouse en bretels, een klein kitten verstopt onder een marktkraam. "
    "Hij neemt het bange diertje mee op een rustige tocht door steegjes, boekwinkels en "
    "een zonnig binnenplein. Onderweg leert Finn dat zorgzaamheid ook betekent dat je hulp "
    "durft te vragen. Wanneer een regenbui alles ingewikkeld maakt, vindt het tweetal steun "
    "bij buurtbewoners. Aan het eind ontdekken Finn en het kitten een warm thuisgevoel: "
    "niet perfect, wel echt."
)


def run_pipeline(config: GenerationConfig, log: LogFn = print) -> list[Path]:
    created_books: list[Path] = []
    _ensure_core_dirs(config)
    _log(log, f"Pipeline gestart: {config.num_books} boek(en), {config.num_pages} pagina's per boek")

    for book_index in range(1, config.num_books + 1):
        created_book = _generate_single_book(config, book_index, log)
        created_books.append(created_book)

    _log(log, "Pipeline afgerond.")
    return created_books


def generate_story_draft(genre: str, tone: str, seed: str = "") -> str:
    seed_text = seed.strip()

    if ai_client.has_openai():
        system = (
            "Je bent een creatieve strip-scenarioschrijver. Schrijf in het Nederlands. "
            "Schrijf een korte verhaaldraft van maximaal 150 woorden voor een 10-pagina strip."
        )
        user = (
            f"Genre: {genre}\nToon: {tone}\n"
            + (f"Beginidee: {seed_text}\n" if seed_text else "")
            + "Schrijf een emotioneel verhaal over een jongen die een kitten vindt in een oud stadje."
        )
        result = ai_client.generate_text(system, user, max_tokens=300)
        if result and not result.startswith("[OpenAI fout"):
            return result

    # Fallback: template
    if seed_text:
        return (
            f"{seed_text}\n\n"
            f"Uitwerking: In dit {genre.lower()} verhaal met een {tone.lower()} toon verschuift "
            "de focus van onzekerheid naar verbondenheid, met kleine menselijke momenten als kern."
        )
    return DEFAULT_PILOT_STORY


def generate_style_draft(base_style: str, setting_hint: str = "") -> str:
    hint = setting_hint.strip() or "retro buurt met bakstenen straten"

    if ai_client.has_openai():
        system = (
            "Je bent een visual director voor een zwart-wit retro mangastrip. "
            "Beschrijf in het Nederlands in max 80 woorden de visuele stijl."
        )
        user = f"Basistijl: {base_style}\nSetting hint: {hint}"
        result = ai_client.generate_text(system, user, max_tokens=150)
        if result and not result.startswith("[OpenAI fout"):
            return result

    # Fallback: template
    return (
        f"{base_style}. Focus op {hint}. Gebruik handgeinkte zwarte lijnen, screentone schaduwen, "
        "witte negatieve ruimte, dynamische panel compositie en herkenbare silhouette-consistentie."
    )


def _generate_single_book(config: GenerationConfig, book_index: int, log: LogFn) -> Path:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_slug = _slugify(config.title)
    book_slug = f"{project_slug}_book_{book_index:02d}_{now}"

    output_dir = Path(config.output_root) / project_slug / book_slug
    stories_dir = output_dir / "stories"
    prompts_dir = output_dir / "prompts"
    images_dir = output_dir / "images"
    refs_dir = output_dir / "references"
    meta_dir = output_dir / "meta"

    for path in [stories_dir, prompts_dir, images_dir, refs_dir, meta_dir]:
        path.mkdir(parents=True, exist_ok=True)

    _log(log, f"[{book_slug}] Mappen aangemaakt")

    _copy_reference_images(config.reference_images, refs_dir, log)

    character_sheet_text = _read_optional_file(Path(config.character_sheet_path))
    story_text = (config.story_text or "").strip() or DEFAULT_PILOT_STORY

    page_plan = _build_page_plan(story_text, config.num_pages, config.genre, config.tone)
    page_prompts = _build_page_prompts(
        page_plan=page_plan,
        style=config.style,
        style_notes=config.style_notes,
        character_sheet=character_sheet_text,
        genre=config.genre,
        tone=config.tone,
    )

    _write_text(stories_dir / "story.txt", story_text)
    _write_text(stories_dir / "page_plan.md", _page_plan_markdown(page_plan))
    _write_text(prompts_dir / "page_prompts.md", _page_prompts_markdown(page_prompts))
    _write_json(prompts_dir / "page_prompts.json", page_prompts)
    _write_json(meta_dir / "config_snapshot.json", asdict(config))

    generated_assets = _render_placeholder_pages(images_dir, page_prompts, log)

    pdf_file = Path(config.pdfs_root) / project_slug / f"{book_slug}.pdf"
    pdf_file.parent.mkdir(parents=True, exist_ok=True)
    _build_text_pdf(
        pdf_file,
        title=config.title,
        page_prompts=page_prompts,
        image_assets=generated_assets,
    )

    _write_text(meta_dir / "manifest.txt", _manifest_text(config, book_slug, generated_assets, pdf_file))
    _log(log, f"[{book_slug}] Boek afgerond -> {output_dir}")
    _log(log, f"[{book_slug}] PDF opgeslagen -> {pdf_file}")
    return output_dir


def _ensure_core_dirs(config: GenerationConfig) -> None:
    for root in [config.output_root, config.stories_root, config.prompts_root, config.images_root, config.pdfs_root]:
        Path(root).mkdir(parents=True, exist_ok=True)


def _copy_reference_images(reference_images: Iterable[str], refs_dir: Path, log: LogFn) -> None:
    for file_path in reference_images:
        src = Path(file_path)
        if src.exists() and src.is_file():
            shutil.copy2(src, refs_dir / src.name)
            _log(log, f"Referentie gekopieerd: {src.name}")


def _build_page_plan(story_text: str, num_pages: int, genre: str, tone: str) -> list[dict]:
    if num_pages == 10:
        return _pilot_page_plan_10(genre, tone)

    # Bouw een structureel page plan voor willekeurig aantal pagina's
    # Gebruik de klassieke 5-act verdeling: opzet / opbouw / ommekeer / herstel / afronding
    # Verdeeld in paren (2 pagina's per fase), met extra opbouw/herstel bij meer pagina's
    structures = _distribute_structures(num_pages)
    sentences = _split_sentences(story_text)
    if not sentences:
        sentences = [story_text or DEFAULT_PILOT_STORY]
    chunks = _chunk_evenly(sentences, num_pages)

    plan: list[dict] = []
    for i, (structure, chunk) in enumerate(zip(structures, chunks), start=1):
        beat = " ".join(chunk).strip()
        # Verrijk de beat met genre/tone context via LLM als beschikbaar
        if ai_client.has_openai() and beat:
            system = (
                "Je bent een stripschrijver. Schrijf in het Nederlands. "
                "Geef een concrete scènebeschrijving van max 30 woorden voor één strippage."
            )
            user = (
                f"Verhaalfase: {structure}\nGenre: {genre}\nToon: {tone}\n"
                f"Verhaaldeel: {beat}\n"
                "Schrijf een bondige scène-omschrijving voor deze pagina."
            )
            llm_beat = ai_client.generate_text(system, user, max_tokens=80)
            if llm_beat and not llm_beat.startswith("[OpenAI fout"):
                beat = llm_beat

        plan.append(
            {
                "page": i,
                "pair_structure": structure,
                "beat": beat,
                "emotion": _pick_emotion(structure),
            }
        )
    return plan


def _distribute_structures(num_pages: int) -> list[str]:
    """
    Verdeel num_pages over de 5 verhaalfasen met minimaal 1 pagina per fase.
    Extra pagina's gaan naar opbouw en herstel (de langste fasen).
    """
    base = ["opzet", "opbouw", "ommekeer", "herstel", "afronding"]
    if num_pages <= 5:
        return base[:num_pages]

    # Begin met 1 per fase, verdeel resterende over opbouw en herstel
    counts = {s: 1 for s in base}
    extra = num_pages - 5
    growth_order = ["opbouw", "herstel", "opzet", "ommekeer", "afronding"]
    for i in range(extra):
        counts[growth_order[i % len(growth_order)]] += 1

    result: list[str] = []
    for s in base:
        result.extend([s] * counts[s])
    return result


def _pilot_page_plan_10(genre: str, tone: str) -> list[dict]:
    beats = [
        ("opzet", "Finn ontdekt het kitten onder een marktkraam en stelt het voorzichtig gerust.", "nieuwsgierig"),
        ("opzet", "Finn neemt het kitten mee door een smalle steeg; er ontstaat een eerste band.", "voorzichtig warm"),
        ("opbouw", "In een boekwinkel zoekt Finn advies over kittenzorg terwijl het diertje verkent.", "leerzaam hoopvol"),
        ("opbouw", "Op een binnenplein oefent Finn met vertrouwen; het kitten durft verder te lopen.", "zacht optimistisch"),
        ("ommekeer", "Donkere wolken en regen zorgen voor paniek; het kitten schiet weg.", "spanning"),
        ("ommekeer", "Finn zoekt in de stromende regen en roept hulp van buurtbewoners in.", "vastberaden"),
        ("herstel", "Een bakker en een oudere buurvrouw helpen mee; het kitten wordt gevonden.", "opluchting"),
        ("herstel", "Finn droogt het kitten af en maakt een veilige slaapplek in de winkel.", "geborgen"),
        ("afronding", "De buurt komt samen voor thee; Finn voelt dat hij er niet alleen voor staat.", "verbonden"),
        ("afronding", "Bij zonsondergang lopen Finn en het kitten naar huis met een rustig, blij gevoel.", "warm tevreden"),
    ]
    return [
        {
            "page": i + 1,
            "pair_structure": b[0],
            "beat": f"{b[1]} ({genre}, {tone})",
            "emotion": b[2],
        }
        for i, b in enumerate(beats)
    ]


def _build_page_prompts(
    page_plan: list[dict],
    style: str,
    style_notes: str,
    character_sheet: str,
    genre: str,
    tone: str,
) -> list[dict]:
    shared_consistency = _consistency_block(character_sheet, style, style_notes, genre, tone)

    prompts: list[dict] = []
    for page_data in page_plan:
        page = page_data["page"]
        layout = _layout_for_page(page)
        prompt_paragraphs = [
            f"PAGE {page} | STRUCTURE: {page_data['pair_structure']}",
            f"Beat: {page_data['beat']}",
            f"Emotie: {page_data['emotion']}",
            f"Panel layout: {layout}",
            "Visual goals: duidelijke silhouette, perspectief variatie, filmische kadrering, rustige flow.",
            "Style: retro handgeinkte zwart-wit manga, screentones, paper grain simulatie, geen kleur.",
            f"Consistency rules:\n{shared_consistency}",
            "Negative prompt: kleurvlakken, moderne kleding, extra hoofdpersonages die niet in story bible staan, stijlbreuk, low-detail faces.",
        ]
        prompt = "\n\n".join(prompt_paragraphs)
        prompts.append(
            {
                "page": page,
                "pair_structure": page_data["pair_structure"],
                "emotion": page_data["emotion"],
                "layout": layout,
                "prompt_paragraphs": prompt_paragraphs,
                "prompt": prompt,
            }
        )
    return prompts


def _render_placeholder_pages(images_dir: Path, page_prompts: list[dict], log: LogFn) -> list[str]:
    assets: list[str] = []
    use_replicate = ai_client.has_replicate()

    for prompt_data in page_prompts:
        page = prompt_data["page"]
        txt_file = images_dir / f"page_{page:02d}_prompt.txt"

        paragraph_text = "\n\n".join(prompt_data.get("prompt_paragraphs", [prompt_data["prompt"]]))
        _write_text(txt_file, paragraph_text)

        if use_replicate:
            png_file = images_dir / f"page_{page:02d}.png"
            # Bouw een compacte prompt voor het image model
            image_prompt = _build_image_prompt(prompt_data)
            success = ai_client.generate_image(image_prompt, png_file, log)
            if success:
                assets.append(str(png_file))
                _log(log, f"Pagina {page:02d}: afbeelding gegenereerd -> {png_file.name}")
                continue
            _log(log, f"Pagina {page:02d}: Replicate mislukt, SVG placeholder als fallback")

        svg_file = images_dir / f"page_{page:02d}_placeholder.svg"
        _write_text(svg_file, _svg_placeholder(prompt_data))
        assets.append(str(svg_file))
        _log(log, f"Pagina {page:02d}: prompt + placeholder opgeslagen")

    return assets


def _build_image_prompt(prompt_data: dict) -> str:
    """Bouw een compacte prompt geschikt voor SDXL op basis van de page prompt data."""
    paragraphs = prompt_data.get("prompt_paragraphs", [])
    # Neem de eerste 5 alinea's (header, beat, emotie, layout, visual goals)
    core = "\n".join(paragraphs[:5]) if paragraphs else prompt_data.get("prompt", "")
    return (
        f"Retro black-and-white manga comic page. {core}. "
        "Hand-inked lines, screentone shading, no color, paper grain texture, "
        "dynamic panel composition, consistent character design."
    )


def _build_text_pdf(pdf_path: Path, title: str, page_prompts: list[dict], image_assets: list[str]) -> None:
    # Probeer reportlab voor een PDF met echte afbeeldingen
    has_png_assets = any(a.endswith(".png") and Path(a).exists() for a in image_assets)
    if has_png_assets:
        try:
            _build_reportlab_pdf(pdf_path, title, page_prompts, image_assets)
            return
        except Exception:
            pass  # Fallback op minimale PDF

    # Fallback: pure-Python tekst PDF
    pages: list[list[str]] = []
    pages.append(
        [
            title,
            "Voorblad",
            "AI Comic Book Generator Draft",
            datetime.now().strftime("Gegenereerd op %Y-%m-%d %H:%M"),
        ]
    )

    for prompt_data, asset in zip(page_prompts, image_assets):
        prompt_paragraphs = prompt_data.get("prompt_paragraphs", [prompt_data["prompt"]])
        wrapped_prompt_lines = _wrap_prompt_for_pdf(prompt_paragraphs, width=84, max_lines=20)

        page_lines = [
            f"Pagina {prompt_data['page']:02d}",
            f"Structuur: {prompt_data['pair_structure']}",
            f"Emotie: {prompt_data['emotion']}",
            f"Layout: {prompt_data['layout']}",
            f"Asset: {asset}",
            "Prompt alinea's:",
        ]
        page_lines.extend(wrapped_prompt_lines)
        pages.append(page_lines)

    pages.append(["Eindblad", "Dank voor het lezen", "Einde van de pilot draft"])
    _write_minimal_pdf(pdf_path, pages)


def _build_reportlab_pdf(pdf_path: Path, title: str, page_prompts: list[dict], image_assets: list[str]) -> None:
    """Bouw een PDF met ingesloten PNG-afbeeldingen via reportlab."""
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
    from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Paragraph, Spacer, PageBreak  # type: ignore

    page_width, page_height = A4
    margin = 1.5 * cm
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Paragraph("AI Comic Book Generator Draft", styles["Normal"]))
    story.append(Paragraph(datetime.now().strftime("Gegenereerd op %Y-%m-%d %H:%M"), styles["Normal"]))
    story.append(PageBreak())

    for prompt_data, asset in zip(page_prompts, image_assets):
        asset_path = Path(asset)
        story.append(Paragraph(f"<b>Pagina {prompt_data['page']:02d}</b>", styles["Heading2"]))

        if asset_path.suffix == ".png" and asset_path.exists():
            max_w = page_width - 2 * margin
            max_h = page_height * 0.65
            story.append(RLImage(str(asset_path), width=max_w, height=max_h, kind="proportional"))
            story.append(Spacer(1, 0.3 * cm))

        story.append(Paragraph(f"Structuur: {prompt_data['pair_structure']} | Emotie: {prompt_data['emotion']}", styles["Normal"]))
        story.append(Paragraph(f"Layout: {prompt_data['layout']}", styles["Normal"]))

        prompt_paragraphs = prompt_data.get("prompt_paragraphs", [])
        for para in prompt_paragraphs[:6]:
            safe_para = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe_para, styles["Normal"]))

        story.append(PageBreak())

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=margin,
        bottomMargin=margin,
    )
    doc.build(story)


def _write_minimal_pdf(path: Path, pages: list[list[str]]) -> None:
    objects: list[bytes] = []

    def add_object(data: bytes) -> int:
        objects.append(data)
        return len(objects)

    font_obj = add_object(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    pages_obj_placeholder = add_object(b"PLACEHOLDER")

    page_obj_ids: list[int] = []
    content_obj_ids: list[int] = []

    for lines in pages:
        content_stream = _pdf_text_stream(lines)
        content_obj = add_object(
            b"<< /Length " + str(len(content_stream)).encode("ascii") + b" >>\nstream\n" + content_stream + b"\nendstream"
        )
        content_obj_ids.append(content_obj)

        page_dict = (
            b"<< /Type /Page /Parent "
            + f"{pages_obj_placeholder} 0 R".encode("ascii")
            + b" /MediaBox [0 0 595 842]"
            + b" /Resources << /Font << /F1 "
            + f"{font_obj} 0 R".encode("ascii")
            + b" >> >>"
            + b" /Contents "
            + f"{content_obj} 0 R".encode("ascii")
            + b" >>"
        )
        page_obj_ids.append(add_object(page_dict))

    kids = " ".join(f"{pid} 0 R" for pid in page_obj_ids).encode("ascii")
    pages_dict = b"<< /Type /Pages /Kids [ " + kids + b" ] /Count " + str(len(page_obj_ids)).encode("ascii") + b" >>"
    objects[pages_obj_placeholder - 1] = pages_dict

    catalog_obj = add_object(b"<< /Type /Catalog /Pages " + f"{pages_obj_placeholder} 0 R".encode("ascii") + b" >>")

    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_pos = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))

    trailer = (
        b"trailer\n<< /Size "
        + str(len(objects) + 1).encode("ascii")
        + b" /Root "
        + f"{catalog_obj} 0 R".encode("ascii")
        + b" >>\nstartxref\n"
        + str(xref_pos).encode("ascii")
        + b"\n%%EOF"
    )
    pdf.extend(trailer)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(bytes(pdf))


def _pdf_text_stream(lines: list[str]) -> bytes:
    y = 790
    chunks = [b"BT\n/F1 14 Tf\n50 790 Td\n"]

    for i, line in enumerate(lines):
        safe = _escape_pdf_text(_to_ascii(line))
        if i == 0:
            chunks.append(f"({safe}) Tj\n".encode("ascii"))
        else:
            y -= 24
            chunks.append(f"1 0 0 1 50 {y} Tm ({safe}) Tj\n".encode("ascii"))

    chunks.append(b"ET")
    return b"".join(chunks)


def _wrap_prompt_for_pdf(paragraphs: list[str], width: int = 84, max_lines: int = 20) -> list[str]:
    wrapped: list[str] = []

    for paragraph in paragraphs:
        if len(wrapped) >= max_lines:
            break

        paragraph_lines = paragraph.splitlines() or [paragraph]
        for raw_line in paragraph_lines:
            if len(wrapped) >= max_lines:
                break

            line = raw_line.strip()
            if not line:
                if wrapped and wrapped[-1] != "":
                    wrapped.append("")
                continue

            prefix = ""
            content = line
            if line.startswith("- "):
                prefix = "- "
                content = line[2:].strip()

            line_width = max(20, width - len(prefix))
            pieces = textwrap.wrap(content, width=line_width) or [content]
            for idx, piece in enumerate(pieces):
                if len(wrapped) >= max_lines:
                    break
                if prefix and idx == 0:
                    wrapped.append(prefix + piece)
                elif prefix:
                    wrapped.append("  " + piece)
                else:
                    wrapped.append(piece)

        if len(wrapped) < max_lines and wrapped and wrapped[-1] != "":
            wrapped.append("")

    if len(wrapped) > max_lines:
        wrapped = wrapped[:max_lines]
    if wrapped and wrapped[-1] == "":
        wrapped.pop()
    return wrapped


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _to_ascii(text: str) -> str:
    return text.encode("ascii", errors="ignore").decode("ascii")


def _split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def _chunk_evenly(items: list[str], count: int) -> list[list[str]]:
    if count <= 0:
        return [items]

    result: list[list[str]] = [[] for _ in range(count)]
    for idx, item in enumerate(items):
        result[idx % count].append(item)

    # Guarantee non-empty page chunks.
    for i in range(count):
        if not result[i]:
            result[i].append(random.choice(items))

    return result


def _pick_emotion(structure: str) -> str:
    mapping = {
        "opzet": "verwondering",
        "opbouw": "hoop",
        "ommekeer": "spanning",
        "herstel": "opluchting",
        "afronding": "warmte",
    }
    return mapping.get(structure, "focus")


def _layout_for_page(page: int) -> str:
    layouts = [
        "5 panelen: brede opening + 3 midden + smalle close-up onder",
        "4 panelen: diagonaal ritme met 1 hoge reactiekader",
        "6 panelen: 2x3 grid met focus op handen en blikrichting",
        "3 panelen: cinematic breed, medium interactie, detail close-up",
    ]
    return layouts[(page - 1) % len(layouts)]


def _consistency_block(character_sheet: str, style: str, style_notes: str, genre: str, tone: str) -> str:
    char_excerpt = _truncate(character_sheet.replace("\n", " ").strip(), 420) or "Gebruik hoofdpersonage jongen + kitten, vaste kleding en proporties."
    return (
        f"- Story bible basis: {char_excerpt}\n"
        f"- Genre/Tone constant: {genre} / {tone}\n"
        f"- Stilistische basis: {style}\n"
        f"- Extra style notes: {style_notes or 'geen'}\n"
        "- Houd leeftijd, kapsel, kleding, kitten-markeringen en omgeving continu identiek tussen pagina's.\n"
        "- Gebruik terugkerende props: bretels, houten krat, regenjas van buurvrouw, bakkerij-etalage."
    )


def _page_plan_markdown(page_plan: list[dict]) -> str:
    lines = ["# Page Plan", ""]
    for item in page_plan:
        lines.append(f"## Pagina {item['page']:02d}")
        lines.append(f"- Structuur: {item['pair_structure']}")
        lines.append(f"- Emotie: {item['emotion']}")
        lines.append(f"- Beat: {item['beat']}")
        lines.append("")
    return "\n".join(lines)


def _page_prompts_markdown(page_prompts: list[dict]) -> str:
    lines = ["# Pilot Page Prompts", ""]
    for item in page_prompts:
        lines.append(f"## Pagina {item['page']:02d}")
        lines.append("")
        lines.extend(item.get("prompt_paragraphs", [item["prompt"]]))
        lines.append("")
    return "\n".join(lines)


def _manifest_text(config: GenerationConfig, book_slug: str, assets: list[str], pdf_file: Path) -> str:
    lines = [
        f"Book slug: {book_slug}",
        f"Title: {config.title}",
        f"Books in run: {config.num_books}",
        f"Pages per book: {config.num_pages}",
        f"Genre: {config.genre}",
        f"Tone: {config.tone}",
        f"Style: {config.style}",
        f"PDF: {pdf_file}",
        "",
        "Generated assets:",
    ]
    lines.extend(f"- {item}" for item in assets)
    return "\n".join(lines)


def _svg_placeholder(page_data: dict) -> str:
    page = page_data["page"]
    layout = page_data["layout"]
    emotion = page_data["emotion"]
    safe_layout = _xml_escape(layout)
    safe_emotion = _xml_escape(emotion)
    return (
        "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1200\" height=\"1700\" viewBox=\"0 0 1200 1700\">"
        "<rect x=\"20\" y=\"20\" width=\"1160\" height=\"1660\" fill=\"white\" stroke=\"black\" stroke-width=\"8\"/>"
        "<text x=\"80\" y=\"160\" font-size=\"56\" font-family=\"Courier New\" fill=\"black\">"
        f"PAGE {page:02d}</text>"
        "<text x=\"80\" y=\"260\" font-size=\"30\" font-family=\"Courier New\" fill=\"black\">"
        f"{safe_layout}</text>"
        "<text x=\"80\" y=\"320\" font-size=\"30\" font-family=\"Courier New\" fill=\"black\">"
        f"Emotion: {safe_emotion}</text>"
        "<line x1=\"80\" y1=\"380\" x2=\"1120\" y2=\"380\" stroke=\"black\" stroke-width=\"4\"/>"
        "<rect x=\"90\" y=\"420\" width=\"1020\" height=\"1150\" fill=\"none\" stroke=\"black\" stroke-dasharray=\"12 8\" stroke-width=\"4\"/>"
        "<text x=\"120\" y=\"480\" font-size=\"28\" font-family=\"Courier New\" fill=\"black\">"
        "Placeholder voor model-output (retro manga b/w)</text>"
        "</svg>"
    )


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "comic-book"


def _read_optional_file(path: Path) -> str:
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return ""


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _log(log: LogFn, message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    log(f"[{timestamp}] {message}")
