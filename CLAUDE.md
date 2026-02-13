# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Retavortaropy parses Esperanto dictionary XML files from the [Revo dictionary](https://github.com/revuloj/revo-fonto) (using the [voko-grundo DTD](https://github.com/revuloj/voko-grundo)) and extracts structured data into JSON. The XML schema represents a rich linguistic structure: articles (`art`) contain derivations (`drv`), which contain senses (`snc`), definitions (`dif`), examples (`ekz`), references (`ref`), and more.

## Commands

```bash
# Run all tests
python -m unittest test_gensenses.py test_genkaps.py

# Run a single test file
python -m unittest test_gensenses.py

# Run a single test case
python -m unittest test_gensenses.TestExtractDifText.test_simple_dif

# Extract sense definitions from XML files (outputs JSON to stdout)
python gensenses.py <xml_directory>
python gensenses.py <xml_directory> -o output.json

# Extract headwords (kap values)
python genkaps.py <xml_directory>

# Extract roots (rad values)
python genrads.py <xml_directory>
```

Package manager is **uv** (not pip). Python 3.13+ required.

## Architecture

### Data Model (`src/retavortaropy/data/vortaro.py`)
The core of the project: 70+ dataclasses modeling every XML element type in the Revo dictionary DTD. Key base classes:
- `Element` — abstract base for all elements
- `HasContent[T]` — elements with ordered child content lists
- `HasTextInContent[T]` — elements that mix inline text with structured children
- `HasKap` — mixin for elements containing headword (`kap`) children

The factory function `element_for(qname)` maps XML tag names to Python dataclass types. Elements support JSON serialization via `json_encode()`/`json_subencode()`.

### XML Parsing (`src/retavortaropy/xmlparse.py`)
SAX-based parsing using lxml. `RevoContentHandler` builds a Python object tree from XML events using an element stack. `DTDResolver` loads DTD files from package resources (`src/retavortaropy/dtd/`).

### CLI Tools (root-level scripts)
- **gensenses.py** — Main extraction tool. Walks `drv`/`subdrv` elements, extracts definitions from `dif`, `ref` (tip="dif"), and `refgrp` elements. Handles tilde (`tld`) replacement with the article's root (`rad`) text, including variant rads. Produces nested sense numbering (1, 1.1, 1.2).
- **genkaps.py** — Extracts headword text from `drv`/`subdrv` kap elements, reconstructing full words from rad + tld patterns.
- **genrads.py** — Extracts root (`rad`) text and variant rads from articles.

### Key Esperanto Dictionary Concepts
- **rad** (radiko/root): The root morpheme of a word, stored in article-level `kap`
- **tld** (tildo/tilde): A placeholder in derivation-level `kap` that gets replaced by the `rad` text
- **drv** (derivaĵo): A word derived from the root, with its own senses and definitions
- **snc** (senco/sense): A numbered meaning of a derivation
- **dif** (difino/definition): The actual definition text within a sense
- **kap** (kapo/head): The headword element containing rad/tld and affixes
