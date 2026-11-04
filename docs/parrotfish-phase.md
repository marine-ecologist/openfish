# Parrotfish species labels (0.7.3)

Parrotfish use one species dropdown with three combined labels:

- Species name [J]
- Species name [IP]
- Species name [TP]

[TP] is the first/default option for each parrotfish species. Non-parrotfish retain ordinary species names. There is no separate phase selector or phase column, and transitional, uncertain and unassessed choices are removed from the active interface. Use Unidentifiable if a combined species/form label cannot be assigned confidently.

The combined selection autosaves like other species choices and follows the existing group-assignment behavior. Individual changes and image exclusions remain available. Viewer and Individual show the suffix in the Species column.

Training exports include a combined `species_id` and readable `label`, while retaining the underlying `base_species_id` and unmodified taxonomic `scientific_name`. No separate `phase` column is exported. Images are grouped by their combined training-label ID. Project transfers preserve these labels.

Existing juvenile/initial/terminal records migrate to [J]/[IP]/[TP]. An older unspecific or uncertain parrotfish record retains its base species label rather than silently asserting TP; choose a new combined label when revisiting it. Historical review events remain intact. The default is an interface convenience, not a model prediction or confirmed sex.

Initial phase can include females and primary males; the suffixes describe visual appearance. The model does not automatically identify these combined labels. Species/form judgements require suitable markings and image quality. See [Manning et al. (2023)](https://onlinelibrary.wiley.com/doi/full/10.1002/ece3.9833) for Caribbean parrotfish colour-phase context.
