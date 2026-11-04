# Manual species catalogues

`caribbean_reef_v5.json` is a read-only extraction of named rows flagged Reef Associated=yes in **Robertson, D.R. & Tornabene, L. (2023), Reef-associated Bony Fishes of the Greater Caribbean: A Checklist (VERSION 5)**, DOI [10.5281/zenodo.10225031](https://zenodo.org/records/10225031). It contains 1,002 named taxa. Unresolved labels and one ambiguous synonym-labelled row are excluded and listed in `caribbean_reef_v5_source.json`. Parenthetical provisional-name annotations are removed where the row already supplies a named taxon; named subspecies and hyphenated epithets are retained. Authority, family, original source row and the source Deep flag are retained. These are manual label choices, not trained model classes or measured occurrence records for a particular survey.

The published scope is native reef-associated bony fishes from the Greater Caribbean, not every regional fish or a Cayman-specific inventory. It excludes sharks/rays and introduced species, among other scope limitations. The existing CoReFish crosswalk entries remain available as supplements and compatibility labels, including its nurse shark and southern stingray entries. The two introduced species explicitly mentioned in the checklist introduction, Pterois volitans and Neopomacentrus cyanomos, are added as identified supplements. This combination is extensive but is not claimed to include all Caribbean fish species or all recent taxonomic changes.

The source marks Deep using approximately 40 m, not a numeric occurrence-depth interval. 862 extracted entries are not flagged Deep; this does not establish an exact 0–50 m species list. All named reef taxa remain available to avoid incorrectly removing species encountered near the shallow/mesophotic boundary. No automatic depth-based taxonomic assignment occurs. Source depths are descriptive metadata, not classifier evidence.

The downloaded source workbook remains in local `outputs/catalog-source/` and is not modified or bundled with the application. Its SHA-256, citation and extraction scope are recorded in the metadata. No licence is asserted beyond the source's published terms. Rebuild using a Python environment containing openpyxl:

```sh
python experiments/build_caribbean_catalog.py /path/to/caribbean-v5.xlsx catalogs/caribbean_reef_v5.json
```

Training loads the expanded catalogue plus compatibility entries. Previously reviewed model taxa remain available; loading a global model does not by itself add every global class to the manual dropdown. Project-specific saved catalogues are preserved for compatibility. Existing species IDs and review history are not silently reclassified or merged when names differ.
