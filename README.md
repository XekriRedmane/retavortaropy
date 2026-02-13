# retavortaropy

Parses Esperanto dictionary XML files from the [Revo dictionary](https://github.com/revuloj/revo-fonto) (using the [voko-grundo DTD](https://github.com/revuloj/voko-grundo)) and extracts structured data into JSON.

## Requirements

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) package manager
- Git (for downloading the dictionary)

## Setup

Install dependencies:

```bash
uv sync
```

Download the revo-fonto dictionary:

```bash
uv run python download_revo.py [destination]
```

If `destination` is omitted, it clones to `./revo-fonto`. If the repository already exists at the destination, it runs `git pull` to update instead.

The download path is saved to `~/.retavortaropy/config.json` so the CLI tools can find it automatically. All tools also accept an explicit path argument to override the saved location.

## CLI tools

### gensenses.py

Extracts sense definitions from derivations (`drv`/`subdrv`) and produces a JSON dictionary mapping headwords to numbered senses.

```bash
# Use saved revo-fonto path
uv run python gensenses.py

# Use explicit path
uv run python gensenses.py path/to/revo

# Write to file instead of stdout
uv run python gensenses.py -o output.json
```

### genkaps.py

Extracts headword text (`kap` values) from derivations and maps them to their source XML files.

```bash
uv run python genkaps.py
uv run python genkaps.py path/to/revo -o kaps.json
```

### genrads.py

Extracts root morphemes (`rad` values), including variant roots, and maps them to their source XML files.

```bash
uv run python genrads.py
uv run python genrads.py path/to/revo -o rads.json
```

### process_ir.py

Filters derivations by subject field (`uzo` with `tip="fak"`) and checks for English translations.

```bash
uv run python process_ir.py
uv run python process_ir.py path/to/revo
```

## Tests

```bash
uv run python -m unittest test_gensenses.py test_genkaps.py
```

## Project structure

- `config.py` — Persistent config management (`~/.retavortaropy/config.json`)
- `download_revo.py` — Downloads/updates the revo-fonto repository
- `gensenses.py` — Sense definition extraction
- `genkaps.py` — Headword extraction
- `genrads.py` — Root morpheme extraction
- `process_ir.py` — Subject field filtering
- `src/retavortaropy/` — Core library (data model, XML parsing, utilities)
- `src/retavortaropy/dtd/` — DTD files from [voko-grundo](https://github.com/revuloj/voko-grundo)
