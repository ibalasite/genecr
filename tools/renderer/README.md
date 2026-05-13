# GeneCR Renderer

Pure Python renderers: **template + JSON input → output file**.
AI's job is only to produce JSON; this code owns layout & cross-linking.

## Layout

```
renderer/
├─ render.py            # CLI: render one type
├─ orchestrate.py       # (todo) run all 7 from one master JSON
├─ templates/           # Jinja2 templates (.tmpl)
├─ schemas/             # JSON Schemas
└─ examples/            # sample input.json + expected output
```

## Types

| type            | template                  | output           |
|-----------------|---------------------------|------------------|
| spec-basic      | spec-basic.md.tmpl        | *-spec-basic.md  |
| spec-advanced   | spec-advanced.md.tmpl     | *-spec-advanced.md |
| assets          | assets.md.tmpl            | *-assets.md      |
| bdd             | bdd.md.tmpl               | *-bdd.md         |
| scrum           | scrum.md.tmpl             | *-scrum.md       |
| docs            | docs.html.tmpl            | *-docs.html      |
| prototype       | prototype.html.tmpl       | *-prototype.html |

## Quickstart

```bash
pip install -r requirements.txt
python render.py spec-basic examples/spec-basic.input.json out/spec-basic.md
```
