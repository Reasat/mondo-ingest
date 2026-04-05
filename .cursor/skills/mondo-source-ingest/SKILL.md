---
name: mondo-source-ingest
description: Scaffolds a new Mondo disease ontology source ingest repo and guides the user through building the ETL pipeline in a dialogue-style workflow. Use when a user wants to create a new Mondo source repo, onboard a new ingest source, or set up a new source preprocessing pipeline for Mondo.
---

# Mondo Source Ingest

You are helping a user scaffold and build a new Mondo source ingest repo. Work interactively — ask one question at a time, inspect source data before proposing mappings, and confirm decisions with the user before writing code.

Before starting, read [plan.md](plan.md) for the full architecture rationale, source format decision tree, and worked examples (ICD10CM, ICD10WHO, OncoTree).

---

## Phase 1: Intake

Ask these four questions sequentially. Do not ask them all at once.

**Q1 — Source location:**
> Where is the upstream data? Provide a URL, API endpoint, or file path.

**Q2 — Source format:** (ask after Q1)
> What format is the source in? (OWL/OBO/RDF, JSON API, JSON file, TSV/CSV, other)

**Q3 — Authentication:** (ask after Q2)
> Does accessing this source require API keys or credentials?

**Q4 — Versioning:** (ask after Q3)
> Does the source publish versioned snapshots, or is it a live/latest endpoint?

After Q4, summarise what you understood and confirm before scaffolding.

---

## Phase 2: Scaffold

Create the repo structure. Confirm the directory name with the user first.

```
<source-name>/
├── .github/workflows/
│   ├── build.yml
│   └── release.yml
├── config/
│   ├── property-map.sssom.tsv
│   └── properties.txt          # OWL sources only
├── docs/
│   ├── plan.md                 # pipeline logic: source, field mappings, design decisions, ID scheme
│   ├── report.md               # unanticipated events, errors, deviations and how they were resolved
│   └── release_notes.md        # ontology stats + Phase 9 verification results for each release
├── env/
│   ├── .env.example
│   └── .env                    # gitignored
├── linkml/
│   └── mondo_source_schema.yaml
├── scripts/
│   ├── acquire.py              # fetch/download source (all source types)
│   ├── transform.py            # OWL sources: ROBOT-output OWL → YAML
│   ├── extract.py              # non-OWL sources: raw JSON/TSV/API → YAML
│   ├── verify.py               # structural checks on the produced YAML
│   └── resolve_version.py      # optional: versioned sources only
├── sparql/                     # OWL sources only
│   └── *.ru                    # SPARQL update queries applied via ROBOT
├── src/<source_name>/
│   └── datamodel.py            # generated from schema
├── tmp/                        # gitignored
├── justfile
├── pyproject.toml
├── README.md
└── uv.lock
```

Note: exact script filenames (`transform.py` vs `extract.py`) are confirmed during Phase 4 once the source format and processing steps are known.

**`.gitignore`** — scaffold this at repo creation. Build artefacts are gitignored because they are uploaded as GitHub Release assets, not committed:

```gitignore
# Credentials — never commit
.env
env/.env

# Build artefacts — uploaded as GitHub Release assets
<source>.owl
<source>_from_linkml.owl
<source>.linkml.yaml

# Build intermediates
tmp/

# Python
*.pyc
__pycache__/
*.egg-info/

# Virtual env — uv.lock IS committed for reproducible CI builds
.venv/
```

**`pyproject.toml`** dependencies: `linkml`, `pydantic`, `PyYAML`, `rdflib`. Add `linkml-owl` for non-OWL sources only. Add `pyoxigraph` if SPARQL querying inside the Python script is needed.

**`justfile`** targets to generate:
- `just acquire` — fetch source
- `just transform` or `just extract` — source → `source.linkml.yml` (name confirmed in Phase 4)
- `just validate` — `python -m linkml.validator.cli -s linkml/mondo_source_schema.yaml -C OntologyDocument source.linkml.yml`
- `just build` — full pipeline end-to-end
- `just iterate` — transform/extract → validate loop only (tight feedback, skips acquire)
- `just release` — tag and upload

If auth is needed, scaffold `env/.env.example` and load credentials from `.env` in `acquire.py`. Load with `load_dotenv()` first, then `os.getenv()` — this means CI can pass credentials as environment variables without needing the `.env` file present.

If the source is versioned, scaffold a `scripts/resolve_version.py` that writes the resolved URL and version IRI to `.env`.

**For API traversal sources** (sources where `acquire.py` must iterate node-by-node through an API rather than download a single file):
- **Use an explicit queue or stack — never recursion.** Python's default 1,000-frame recursion limit silently truncates recursive traversals mid-run without raising an error. The choice between BFS (queue, `pop(0)`) and iterative DFS (stack, `pop()`) doesn't matter — both are safe. What matters is that the "call stack" is a plain Python list in heap memory, not the interpreter's call stack.
- **Token refresh:** if the API uses short-lived OAuth tokens (~1 hour), implement proactive refresh (e.g. every 55 minutes) inside the traversal loop, plus a reactive catch on 401 responses. A single token fetch at startup is insufficient for long traversals.
- **Cache every node response** to `tmp/cache/<encoded-uri>/response.json` as the traversal runs. If the run is interrupted, the next run reads from cache rather than re-fetching.
- **Wire `actions/cache` in CI** to persist `tmp/cache/` between workflow runs, keyed on a hash of `acquire.py`. The first CI run pays the full traversal cost; all subsequent runs restore the cache and finish in seconds:
  ```yaml
  - name: Restore API node cache
    uses: actions/cache@v4
    with:
      path: tmp/cache
      key: <source>-api-cache-${{ hashFiles('scripts/acquire.py') }}
      restore-keys: |
        <source>-api-cache-
  ```

For **live/latest endpoints** (no explicit version in the URL), scaffold a `resolve_latest_url()` function in `acquire.py` that scrapes the source's download page and extracts the current filename via regex. Always prefer dynamic resolution over hardcoding a version-specific URL — a hardcoded URL will silently fetch a stale file once the source publishes a new version.

**`README.md`** — keep it minimal. The detailed pipeline rationale lives in `docs/plan.md`. The README should only contain:

```markdown
# <source-name>

<One sentence description>.

## Setup

<Auth steps if needed, e.g.:>
1. Register at <auth URL> to get API credentials
2. Copy `env/.env.example` → `env/.env` and fill in the required variables
3. Install dependencies: `uv sync`

## Run

```bash
make acquire       # or: just acquire
make build         # ROBOT preprocessing (OWL sources only)
make build-release # YAML + validate + derived OWL
```

## Outputs

| File | Description |
|---|---|
| `<source>.linkml.yaml` | Primary artefact for Mondo ingest |
| `<source>.owl` | ROBOT-preprocessed OWL (OWL sources only) |
| `<source>_from_linkml.owl` | LinkML-derived OWL |

## Docs

| Doc | Contents |
|---|---|
| [`docs/plan.md`](docs/plan.md) | Pipeline architecture, field mappings, ID scheme |
| [`docs/release_notes.md`](docs/release_notes.md) | Ontology stats and verification results per release |
| [`docs/report.md`](docs/report.md) | Unanticipated events and how they were resolved |
```

If `acquire` is slow (e.g. API traversal), add a note in the `make acquire` line so the user knows it is expected behaviour, e.g. `# ~2.5 hrs, cached after first run`.

---

## Phase 3: Schema and datamodel

Copy `mondo_source_schema.yaml` into `linkml/`. The base schema below is the correct working template — do not simplify it. It has been validated against `linkml-owl` and produces correct OWL output.

```yaml
id: https://w3id.org/monarch-initiative/mondo-source-schema
name: mondo_source_schema
prefixes:
  linkml:    https://w3id.org/linkml/
  mondo_src: https://w3id.org/monarch-initiative/mondo-source-schema/
  rdfs:      http://www.w3.org/2000/01/rdf-schema#
  skos:      http://www.w3.org/2004/02/skos/core#
  dcterms:   http://purl.org/dc/terms/
  obo:       http://purl.obolibrary.org/obo/
  oboInOwl:  http://www.geneontology.org/formats/oboInOwl#
  owl:       http://www.w3.org/2002/07/owl#
  # ADD source-specific prefix here, e.g.:
  # ICD10WHO: https://icd.who.int/browse10/2019/en#/
  # Orphanet: http://www.orpha.net/ORDO/Orphanet_

imports:
  - linkml:types

default_prefix: mondo_src
default_range: string


classes:

  OntologyDocument:
    tree_root: true
    class_uri: owl:Ontology
    slots:
      - title
      - version
      - terms

  OntologyTerm:
    class_uri: owl:Class
    slots:
      - id
      - label
      - definition
      - exact_synonyms
      - related_synonyms
      - narrow_synonyms
      - broad_synonyms
      - parents
      - is_root
      - deprecated


slots:

  title:
    slot_uri: rdfs:label
    required: true

  version:
    slot_uri: owl:versionInfo
    required: true

  terms:
    range: OntologyTerm
    multivalued: true
    inlined_as_list: true
    required: true

  id:
    identifier: true
    slot_uri: dcterms:identifier
    range: uriorcurie        # must be uriorcurie — plain string breaks linkml-owl IRI resolution
    required: true

  label:
    slot_uri: rdfs:label
    required: true
    annotations:
      owl: AnnotationAssertion

  definition:
    slot_uri: obo:IAO_0000115
    annotations:
      owl: AnnotationAssertion

  exact_synonyms:
    slot_uri: oboInOwl:hasExactSynonym
    multivalued: true
    annotations:
      owl: AnnotationAssertion

  related_synonyms:
    slot_uri: oboInOwl:hasRelatedSynonym
    multivalued: true
    annotations:
      owl: AnnotationAssertion

  narrow_synonyms:
    slot_uri: oboInOwl:hasNarrowSynonym
    multivalued: true
    annotations:
      owl: AnnotationAssertion

  broad_synonyms:
    slot_uri: oboInOwl:hasBroadSynonym
    multivalued: true
    annotations:
      owl: AnnotationAssertion

  parents:
    slot_uri: rdfs:subClassOf
    range: OntologyTerm
    multivalued: true
    annotations:
      owl: SubClassOf          # SubClassOf, not AnnotationAssertion

  is_root:
    range: boolean
    ifabsent: "false"

  deprecated:
    slot_uri: owl:deprecated
    range: boolean
    ifabsent: "false"
    annotations:
      owl: AnnotationAssertion
```

**Critical `linkml-owl` rules — violations produce a silent empty OWL file (no error):**
1. **Use top-level `slots:`, not inline `attributes:`** — `linkml-owl` only emits axioms for slots declared at the top level with `annotations: owl:`.
2. **Every annotation property slot must have `annotations: owl: AnnotationAssertion`** — without it, `linkml-owl` silently omits that slot from the derived OWL.
3. **`parents` must use `annotations: owl: SubClassOf`** — not `AnnotationAssertion`.
4. **`id` must have `range: uriorcurie`** — plain `string` prevents `linkml-owl` from resolving CURIEs to IRIs. All class declarations will be missing.
5. **The source IRI namespace must be declared in `prefixes:`** — if `ICD10WHO:A00.0` is an `id` value but `ICD10WHO:` is not in the prefix map, `linkml-owl` cannot expand it and silently skips the class.
6. **When adding source-specific extra slots**, always include `annotations: owl: AnnotationAssertion` on them too. The pattern is invariant across sources.

**Diagnosing a silent failure:** if `linkml-owl` produces a file under ~1 KB containing only the ontology header and zero `AnnotationAssertion` lines, one of the above rules has been violated. Check them in order.

Then generate the Pydantic datamodel:
```bash
gen-pydantic linkml/mondo_source_schema.yaml > src/<source_name>/datamodel.py
```

Ask the user if they need any additional slots before generating.

**Schema slot type warning:** The `in_subsets` slot has `range: uriorcurie`. Do not put plain text strings (e.g. source-internal classification labels like "Clinical subtype") into this slot — `linkml-owl` will reject them with `ValueError: X is not a valid URI or CURIE`. If the source has free-text classification values, either drop them or add a dedicated `range: string` slot for them.

---

## Phase 4: Source analysis dialogue

Download a small sample. Show the user what you see. Then ask about each mapping one at a time.

**4.1 — Labels:**
> I can see [field name] appears to be the primary label. Should this map to `rdfs:label`?

For OWL sources, look for `rdfs:label`. For JSON, identify the name field.

**4.2 — Definitions:**
> Does this source have definitions — a text field explaining what each term means? This would map to `obo:IAO_0000115`. If not, that slot will remain empty.

**4.3 — Synonyms:**
> Next, I want to identify synonyms. This is not always obvious.
>
> Exact synonyms are alternative names that mean exactly the same thing (acronyms, official alternate names). Related synonyms are close but not exact (colloquial names, spelling variants).
>
> In ICD10CM and ICD10WHO, there are no explicit synonyms in the source — we generate an exact synonym from the label itself. In OncoTree, there are no synonyms at all.
>
> Does this source provide any synonym-like fields? If not, should I generate exact synonyms from labels?

**4.4 — Hierarchy:**
> How does the source represent parent-child relationships?
>
> - OWL sources usually have `rdfs:subClassOf` directly.
> - JSON sources often have a `parent` or `parent_code` field.
> - ORDO uses part-of restrictions instead of subClassOf — that requires a SPARQL rewrite before extraction.
>
> What does the hierarchy look like here?

**4.5 — Obsolete terms:**
> Does the source have deprecated or obsolete terms? If so, how are they marked?
>
> ICD10CM/ICD10WHO use `owl:deprecated true`. OncoTree uses `revocations` and `precursors` fields, which require a second pass — each revoked code becomes an obsolete class pointing to its replacement via `IAO:0100001`, or `oboInOwl:consider` if there are multiple replacements. Note: ignore self-revocations.
>
> Should I include obsolete terms in the output?

**4.6 — Cross-references and mappings:**
> Does the source contain cross-references to other ontologies (e.g. NCI, UMLS, OMIM)?
>
> These can be included in the YAML output or published separately as an SSSOM file. OncoTree `externalReferences` maps to `skos:exactMatch` in the output OWL.

**4.7 — IRI namespace and CURIE scheme:**
> What IRI namespace does the source use for its class identifiers?
>
> - OBO sources use `http://purl.obolibrary.org/obo/<PREFIX>_<code>` — these resolve cleanly to standard CURIEs.
> - Some sources use their own namespaces (e.g. ICD10WHO uses `https://icd.who.int/browse10/2019/en#/`).
>
> If the source IRI namespace is not an OBO PURL, declare a custom prefix in the schema's `prefixes:` block and document the CURIE scheme in `docs/plan.md`. The prefix must be declared in the schema for `linkml-owl` to resolve it — an undeclared prefix causes `linkml-owl` to silently skip all class declarations.

**4.8 — OWL structural issues (OWL sources only):**

Run a SPARQL probe. Report any of these patterns and ask for confirmation before adding a ROBOT preprocessing step:

| Pattern | Seen in | Fix |
|---|---|---|
| part-of restrictions instead of subClassOf | ORDO | SPARQL rewrite before extraction |
| illegal punning | OMIM | SPARQL fix before extraction |
| nested annotation reification | ORDO | SPARQL fix before extraction |

For non-OWL sources, skip this step entirely.

**4.9 — Term count cross-check:**

If a prior version of this source exists anywhere (committed file, BioPortal, another repo), compare term counts before treating a discrepancy as an error. Document the difference and its cause in `docs/report.md`. Known cause: the old `monarch-initiative/icd10who` TTL had 4,894 terms due to a Python recursion limit truncating the traversal — the correct full count is 12,597.

---

## Phase 5: Write the processing scripts

The pipeline differs by source type. Confirm the approach with the user before writing any code.

---

### 5a — OWL sources: ROBOT preprocessing + `transform.py`

OWL sources go through two stages. Stage 1 is ROBOT (invoked from `justfile`); Stage 2 is Python.

**Stage 1 — ROBOT (via `justfile`):**

```
just mirror   → robot merge -i raw.owl odk:normalize → tmp/mirror.owl
just build    → robot merge -i tmp/mirror.owl
                  query --update sparql/fix_*.ru        (structural fixes)
                  query --update sparql/exact_syn_from_label.ru  (if needed)
                  remove -T config/properties.txt --select complement --select properties --trim true
                  annotate --ontology-iri <IRI> --version-iri <VERSION_IRI>
                → source.owl                            ← released OWL artefact
```

SPARQL update files (`sparql/*.ru`) handle any structural issues identified in Phase 4.7. The property allowlist (`config/properties.txt`) must always include `rdfs:label` and `owl:deprecated` at minimum.

**Stage 2 — `scripts/transform.py`:**

Reads the ROBOT-output `source.owl` (not the raw acquired file) using rdflib. Maps OWL predicates to schema slots and writes `source.linkml.yml`.

Show the user a sketch and confirm field mappings before writing the full implementation:

```python
from rdflib import OWL, RDF, RDFS, Graph, Literal, URIRef
from rdflib.namespace import Namespace

OBOINOWL = Namespace("http://www.geneontology.org/formats/oboInOwl#")

def extract_terms(g: Graph) -> list[dict]:
    for iri in sorted(str(s) for s in g.subjects(RDF.type, OWL.Class) if isinstance(s, URIRef)):
        label = g.value(URIRef(iri), RDFS.label)
        if label is None:
            continue
        # map further slots: definition, synonyms, parents ...
        yield {"id": curie(iri), "label": str(label), ...}
```

---

### 5b — Non-OWL sources: `extract.py`

No ROBOT involved. The extractor reads the raw acquired file (JSON, TSV, API response) directly.

Show the user a sketch and confirm field mappings before writing the full implementation:

```python
from src.<source>.datamodel import OntologyDocument, OntologyTerm

def extract(data) -> OntologyDocument:
    terms = []
    for item in data:
        terms.append(OntologyTerm(
            id=f"PREFIX:{item['code']}",
            label=item["name"],
            parents=[f"PREFIX:{item['parent']}"] if item.get("parent") else [],
            is_root=not bool(item.get("parent")),
        ))
    return OntologyDocument(title="Source", terms=terms)
```

For sources with revocations (OncoTree-style), implement a second pass for obsolete terms after the main loop.

---

**Robustness rules (apply to both paths):**
- Always strip and skip blank/whitespace-only literal values before adding them to list slots. `linkml-owl` raises `ConstructorError: Empty list elements are not allowed` if a list contains an empty string. Use `val = str(o).strip(); if val: out.append(val)` in every literal-collecting helper.
- When writing SPARQL that filters on `owl:deprecated`, use `FILTER(str(?dep) = "true")` rather than `?cls owl:deprecated true`. Some sources (including ORDO) serialise the deprecated flag as an untyped plain string literal `"true"` rather than `"true"^^xsd:boolean`. The boolean keyword in SPARQL does not match plain literals.

---

## Phase 6: Validate and iterate

Run:
```bash
just iterate
```

If validation fails:
1. Show the user which fields failed and why
2. Propose a specific fix in the extractor
3. Re-run

Do not proceed to Phase 7 until `linkml-validate` exits 0 and term counts look plausible. Log term counts for the user to review.

---

## Phase 7: Derive OWL

This phase applies to **non-OWL sources only**.

For OWL sources, the released OWL artefact is the ROBOT-processed `source.owl` produced in Phase 5a — no further derivation is needed. Skip this phase.

For non-OWL sources (JSON, TSV, API), the source has no OWL representation, so one must be derived from the YAML:

```bash
just data2owl
# python -m linkml_owl.dumpers.owl_dumper -s linkml/mondo_source_schema.yaml -f yaml source.linkml.yml -o source.linkml.owl
```

Tell the user: the derived OWL is for OWL-native consumers only. `source.linkml.yml` is the primary contract. Known limitation: `linkml-owl` emits OWL Functional format; ROBOT may not load it cleanly in all cases. If it fails on large datasets (rdflib N3 parser error), document this in `docs/report.md` and release `source.linkml.yml` only.

---

## Phase 8: Wire CI and release

Generate the two workflow files below. For OWL sources, all steps run inside `obolibrary/odkfull:v1.6` Docker so that ROBOT and the ODK normalize plugin are available without any separate install step. For non-OWL sources (JSON, TSV), the Docker step can be replaced with a plain `uv sync && uv run python ...` step on `ubuntu-latest`.

**`.github/workflows/release.yml`**

```yaml
name: Build and release

on:
  workflow_dispatch:
  schedule:
    - cron: "0 0 * * 1"   # weekly, Monday 00:00 UTC
  push:
    branches: [main]
    paths:
      - "Makefile"         # or justfile for non-OWL sources
      - "config/**"
      - "sparql/**"        # OWL sources only
      - "linkml/**"
      - "scripts/**"
      - "pyproject.toml"
      - "uv.lock"

jobs:
  build-and-release:
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build (ROBOT + LinkML)
        run: |
          docker run --rm \
            -e ROBOT_PLUGINS_DIRECTORY=/tools/robot-plugins \
            -v "$PWD:/work" \
            -w /work \
            obolibrary/odkfull:v1.6 \
            bash -lc "pip3 install --break-system-packages uv && uv sync && make build-release"

      - name: Set release tag
        id: version
        run: echo "tag=v$(date +%Y%m%d)-${{ github.run_number }}" >> "$GITHUB_OUTPUT"

      - name: Create release and upload assets
        if: success() && hashFiles('source.linkml.yml') != ''
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{ steps.version.outputs.tag }}
          name: Release ${{ steps.version.outputs.tag }}
          files: |
            source.linkml.yml
            source.linkml.owl
          generate_release_notes: true
          draft: false
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Substitute the actual output filenames for `source.linkml.yml` / `source.linkml.owl`. Released artefacts differ by source type:

| Source type | Released YAML | Released OWL |
|---|---|---|
| OWL | `source.linkml.yml` | `source.owl` (ROBOT-processed) |
| Non-OWL | `source.linkml.yml` | `source.linkml.owl` (linkml-owl derived) |

**`.github/workflows/build.yml`**

```yaml
name: Build

on:
  pull_request:
    paths:
      - "Makefile"
      - "config/**"
      - "sparql/**"
      - "linkml/**"
      - "scripts/**"
      - "pyproject.toml"
      - "uv.lock"

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build (ROBOT + LinkML)
        run: |
          docker run --rm \
            -e ROBOT_PLUGINS_DIRECTORY=/tools/robot-plugins \
            -v "$PWD:/work" \
            -w /work \
            obolibrary/odkfull:v1.6 \
            bash -lc "pip3 install --break-system-packages uv && uv sync && make build-release"
```

**Key implementation notes:**
- `permissions: contents: write` is required on the release job for `softprops/action-gh-release` to create tags and releases.
- `ROBOT_PLUGINS_DIRECTORY=/tools/robot-plugins` makes the ODK normalize plugin available inside the container (its location in `odkfull`).
- `hashFiles('source.linkml.yml') != ''` guards the release step so a failed build does not create an empty release.
- The `workflow_dispatch` trigger allows manual runs from the GitHub Actions UI without a push.
- Local `ROBOT_PLUGINS_DIRECTORY` will differ from CI (e.g. `/home/<user>/.robot/plugins` locally vs `/tools/robot-plugins` in Docker). Set it as a `?=` default in the Makefile so it can be overridden.

---

## Phase 9: Verify

Scaffold `scripts/verify.py` and run it before the first release. Record results in `docs/release_notes.md`.

**`scripts/verify.py`** automates the structural checks. It must:
- Accept `--yaml <path>` (the produced YAML) and `--expected-version <str>` (optional)
- Check `title` and `version` are present and non-empty
- Check for duplicate term IDs
- Check every term has a non-empty `label`
- Check every `parents` entry resolves to a known term ID in the same file (broken refs = hierarchy error)
- Print a summary (term count, unique IDs, broken parent refs) and exit 0 on PASS, exit 1 on FAIL

Run it:
```bash
uv run python scripts/verify.py --yaml <source>.linkml.yaml --expected-version <version>
```

Add this as a `just verify` / `make verify` target so it can be re-run for every release.

**Full checklist (some checks automated by `verify.py`, some manual):**

| Check | How |
|---|---|
| Title and version present | `verify.py` |
| No duplicate term IDs | `verify.py` |
| `label` non-null for all terms | `verify.py` |
| All `parents` refs resolve | `verify.py` |
| `version` matches upstream release identifier | `verify.py --expected-version` |
| `linkml-validate` exits 0 | `uv run python -m linkml.validator.cli ...` |
| OWL artefact loads in ROBOT / Protégé | manual spot-check |
| `robot diff` vs mondo-ingest reference (if migrating) | manual |

**OWL sources additionally:**
- [ ] `source.owl` (ROBOT output) can be loaded by ROBOT or opened in Protégé
- [ ] If migrating from mondo-ingest: run `robot diff` between this OWL and the mondo-ingest reference OWL

**Non-OWL sources additionally:**
- [ ] `source.linkml.owl` (linkml-owl output) can be loaded by ROBOT or opened in Protégé

---

## Guardrails

- Never propose field mappings without first showing the user a data sample
- Never write the extractor without showing a sketch and getting confirmation
- Never proceed past validation until it passes
- Do not add SPARQL preprocessing steps for non-OWL sources
- Do not invent synonym behaviour — ask the user if the source has synonyms or if they should be generated from labels
- Never silently remove or simplify a pipeline step because a tool or plugin appears to be missing. Search the full filesystem, then ask the user where it is before removing anything.
- Generate `docs/plan.md` capturing the pipeline logic that governs this repo: upstream source, field-to-slot mappings, ID scheme, versioning strategy, and key design decisions. This is the canonical reference for anyone maintaining the pipeline.
- Generate `docs/report.md` recording every unanticipated event that occurred during the session — errors, tool failures, necessary deviations from the standard pipeline, and the exact steps taken to resolve each one.
- Generate `docs/release_notes.md` containing the ontology statistics from the full run (term count, definitions, synonyms, roots, broken refs) together with the Phase 9 verification checklist results. Update this file for every subsequent release.
- **Never substitute a third-party or mirror source for the official upstream.** The acquire step must always fetch from the authoritative publisher (e.g. WHO API, BioPortal official submission, ORPHADATA). Third-party builds (e.g. biopragmatics/obo-db-ingest, OBO Foundry mirrors) may be used for *inspection and prototyping only* — never as the production source. If the official source is slow or requires credentials, scaffold the credentials properly and document the performance impact; do not silently swap to a convenience mirror.
- **Always record the official release identifier in the output.** The `version` field in the produced YAML must match the upstream publisher's versioning scheme (e.g. `2026-01` for WHO ICD-11, submission ID for BioPortal). A date derived from a third-party build timestamp is not an acceptable substitute.
