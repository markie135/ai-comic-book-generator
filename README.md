# AI Comic Book Generator

**Geautomatiseerd systeem voor het maken van complete stripboeken / manga met AI**

Een krachtig, modulair Python-systeem dat volledige stripboeken (100+ pagina's) genereert met behulp van AI. Van verhaalcreatie tot kant-en-klare PDF.

---

## ✨ Over het project

Dit project automatiseert het hele proces van het maken van een professioneel stripboek:
- Een compleet verhaal bedenken
- Karakters en wereld consistent houden
- Het verhaal verdelen over pagina's
- Per pagina een optimale prompt genereren
- Hoogwaardige zwart-wit afbeeldingen genereren in mangastijl
- Consistentie bewaken over honderden pagina's
- Alles automatisch opslaan als losse bestanden + print-ready PDF

**Doel:** Eerst 1 perfect boek maken, daarna een hele serie (5 boeken van ~100 pagina's).

---

## 🎯 Hoofdfuncties

- **Verhaalgeneratie**: Volledig originele verhalen met duidelijke 3-act structuur
- **Karakterconsistentie**: Vast character sheet + referentiebeelden
- **Automatische paginaverdeling**: 100 pagina's met logische hoofdstukindeling
- **Slimme prompt engineering**: Per pagina gedetailleerde, consistente prompts
- **Stijlcontrole**: Retro handgeïnkte mangastijl (zwart-wit)
- **Consistentie checks**: Automatische controle op verhaal, kleding, locaties en sfeer
- **Bestandsbeheer**: Georganiseerde mapstructuur per boek
- **PDF export**: Volledig stripboek als één PDF (voorblad, inhoud, eindblad)
- **Modulair ontwerp**: Makkelijk uit te breiden naar nieuwe stijlen en series

---

## 📋 Huidige status

**Fase 1: Pilot** (actief)
- Eerste testverhaal met de jongen + kitten (gebaseerd op de geüploade referentieafbeelding)
- Retro handgeïnkte mangastijl
- 3-panel per pagina layout
- Focus op verhaalconsistentie en visuele kwaliteit

**Volgende stappen:**
1. Pilot van 8-10 pagina's afronden
2. Volledig 100-pagina boek maken
3. Systeem verder automatiseren (Python pipeline)
4. Serie van 5 boeken voorbereiden

---

## 🛠 Technische roadmap

- [ ] Pilot (8-10 pagina's) met jongen + kitten
- [ ] Volledig boek (100 pagina's)
- [ ] Geautomatiseerde Python pipeline
- [ ] Character LoRA / consistente image references
- [ ] Post-processing (tekstballonnen, sound effects, uniform filter)
- [ ] PDF generatie met InDesign-achtige layout
- [ ] Multi-boek serie management (5 boeken)
- [ ] Web interface (optioneel)

---

## 📁 Projectstructuur

```
ai-comic-book-generator/
├── books/                  # Gegenereerde boeken
│   ├── boek1_kat_avontuur/
│   │   ├── images/
│   │   ├── prompts/
│   │   ├── pdf/
│   │   └── metadata.json
├── characters/             # Character sheets & referenties
├── prompts/                # Prompt templates
├── scripts/                # Python automation scripts
├── stories/                # Verhalen en outlines
├── output/                 # Tijdelijke bestanden
├── README.md
└── requirements.txt
```

---

## 🚀 Hoe te gebruiken (binnenkort)

1. Clone de repo
2. Installeer dependencies
3. Voeg je AI API keys toe (Grok, Claude, Midjourney, Flux, etc.)
4. Run `python main.py --new-book "De jongen en de magische kat"`

Meer gedetailleerde instructies volgen zodra de eerste scripts klaar zijn.

---

## 🤝 Bijdragen

Dit is een persoonlijk project dat snel groeit. Ideeën, suggesties en pull requests zijn welkom!

---

**Gemaakt met ❤️ voor stripverhalen en AI**

*Eerste versie - Mei 2026*
