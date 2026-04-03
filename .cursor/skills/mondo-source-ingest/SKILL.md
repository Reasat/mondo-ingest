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
├── docs/plan.md                 # generated summary of this session
├── env/
│   ├── .env.example
│   └── .env                    # gitignored
├── linkml/
│   └── mondo_source_schema.yaml
├── scripts/
│   ├── acquire.py
│   └── extract.py
├── src/<source_name>/
│   └── datamodel.py            # generated from schema
├── tmp/                        # gitignored
├── justfile
├── pyproject.toml
└── uv.lock
```

**`pyproject.toml`** dependencies: `linkml`, `linkml-owl`, `pydantic`, `PyYAML`. Add `pyoxigraph` for OWL sources.

**`justfile`** targets to generate:
- `just acquire` — fetch source
- `just extract` — run extractor → `source.linkml.yml`
- `just validate` — `python -m linkml.validator.cli -s linkml/mondo_source_schema.yaml -C OntologyDocument source.linkml.yml`
- `just data2owl` — `python -m linkml_owl.dumpers.owl_dumper -s linkml/mondo_source_schema.yaml source.linkml.yml -o source.linkml.owl`
- `just build` — acquire → extract → validate → data2owl
- `just iterate` — extract → validate loop only (tight feedback)
- `just release` — tag and upload

If auth is needed, scaffold `env/.env.example` and load credentials from `.env` in `acquire.py`.

If the source is versioned, scaffold a `scripts/resolve_version.py` that writes the resolved URL and version IRI to `.env`.

---

## Phase 3: Schema and datamodel

Copy `mondo_source_schema.yaml` into `linkml/`. The base schema is:

```yaml
id: https://w3id.org/monarch-initiative/mondo-source
name: mondo_source
prefixes:
  linkml: https://w3id.org/linkml/
  owl: http://www.w3.org/2002/07/owl#
  rdfs: http://www.w3.org/2000/01/rdf-schema#
  obo: http://purl.obolibrary.org/obo/
  oboInOwl: http://www.geneontology.org/formats/oboInOwl#
  skos: http://www.w3.org/2004/02/skos/core#
imports: [linkml:types]
default_range: string

classes:
  OntologyDocument:
    tree_root: true
    class_uri: owl:Ontology
    attributes:
      title: {required: true}
      version: {}
      terms:
        multivalued: true
        range: OntologyTerm
        inlined_as_list: true

  OntologyTerm:
    class_uri: owl:Class
    attributes:
      id: {identifier: true, required: true}
      label: {required: true, slot_uri: rdfs:label}
      definition: {slot_uri: "obo:IAO_0000115"}
      exact_synonyms:
        multivalued: true
        slot_uri: "oboInOwl:hasExactSynonym"
      related_synonyms:
        multivalued: true
        slot_uri: "oboInOwl:hasRelatedSynonym"
      narrow_synonyms:
        multivalued: true
        slot_uri: "oboInOwl:hasNarrowSynonym"
      broad_synonyms:
        multivalued: true
        slot_uri: "oboInOwl:hasBroadSynonym"
      parents:
        multivalued: true
        slot_uri: rdfs:subClassOf
      is_root:
        range: boolean
```

Then generate the Pydantic datamodel:
```bash
gen-pydantic linkml/mondo_source_schema.yaml > src/<source_name>/datamodel.py
```

Ask the user if they need any additional slots before generating.

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

**4.7 — OWL structural issues (OWL sources only):**

Run a SPARQL probe. Report any of these patterns and ask for confirmation before adding a ROBOT preprocessing step:

| Pattern | Seen in | Fix |
|---|---|---|
| part-of restrictions instead of subClassOf | ORDO | SPARQL rewrite before extraction |
| illegal punning | OMIM | SPARQL fix before extraction |
| nested annotation reification | ORDO | SPARQL fix before extraction |

For non-OWL sources, skip this step entirely.

---

## Phase 5: Write the extractor

Show the user a sketch of `scripts/extract.py` based on the confirmed field mappings. Ask for approval before writing the full implementation.

The extractor must:
1. Load the source
2. Iterate over terms
3. Create `OntologyTerm` instances from the generated datamodel
4. Assemble into `OntologyDocument`
5. Serialise to `source.linkml.yml` using `yaml.dump` or LinkML's Python serialiser

For OncoTree-style sources with revocations, implement the second pass for obsolete terms after the main loop.

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

Run:
```bash
just data2owl
```

Tell the user: the derived OWL is for OWL-native consumers only. `source.linkml.yml` is the primary contract. Known limitation: `linkml-owl` emits OWL Functional format; ROBOT may not load it cleanly in all cases.

---

## Phase 8: Wire CI and release

Generate `.github/workflows/release.yml`. The workflow must:
- Trigger on push to `main` (paths: `justfile`, `scripts/**`, `linkml/**`, `pyproject.toml`) and weekly schedule
- Run `uv sync && just build`
- Create a dated tag (`vYYYYMMDD-<run_number>`)
- Upload `source.linkml.yml` and `source.linkml.owl` as release assets

Generate `.github/workflows/build.yml` for PRs (same build, no release).

---

## Phase 9: Verify

Walk the user through this checklist before the first release:

- [ ] Term count in YAML matches expected source count
- [ ] `label` is non-null for all terms
- [ ] All `parents` references resolve to known term IDs
- [ ] `linkml-validate` exits 0
- [ ] `source.linkml.owl` can be opened in Protégé or loaded by ROBOT
- [ ] If migrating from mondo-ingest: run `robot diff` between this OWL and the mondo-ingest reference OWL

---

## Guardrails

- Never propose field mappings without first showing the user a data sample
- Never write the extractor without showing a sketch and getting confirmation
- Never proceed past validation until it passes
- Do not add SPARQL preprocessing steps for non-OWL sources
- Do not invent synonym behaviour — ask the user if the source has synonyms or if they should be generated from labels
- Generate `docs/release_notes.md` at the end of the session summarising the results and what was built
- Generate `docs/report.md` and report the unanticipated events that occured while following the instructions and what steps were taken to solve it.
