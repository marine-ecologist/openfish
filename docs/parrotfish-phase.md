# Parrotfish visual phase (0.7.3)

Many parrotfish can be identified visually to juvenile, initial (IP) or terminal (TP) appearance when species-specific colour patterns and morphology are visible. This is not reliably possible for every species, fish, angle or video. Phase is an additional human annotation, separate from species and model scores.

## Fields

- Not assessed (`unassessed`): default for identified parrotfish, including older labels.
- Juvenile (visual) (`juvenile`).
- Initial phase (`initial`).
- Terminal phase (`terminal`).
- Transitional / intermediate appearance (`transitional`): descriptive visual appearance, not confirmation of physiological sex change.
- Phase uncertain (`uncertain`): assessed but insufficient evidence.
- Not applicable (`not_applicable`): non-parrotfish or unidentified fish; no phase inference is made.

The controls are available per fish in Gallery and Individual for identified parrotfish. Applicability uses Scaridae family metadata or a parrotfish-genus list, including Scarus, Sparisoma, Cryptotomus and Nicholsina. This enables annotation; it does not assert that all these taxa have equally distinguishable phases.

Phase saves automatically with reviewer metadata, follows the selected fish into Individual, and appears as a column in Viewer and the Individual track table. Species propagation never propagates phase. Reassigning Gallery species resets phase to Not assessed for a new parrotfish species or Not applicable otherwise. Same-species changes preserve phase and image exclusions.

`training_labels.json`, review history, `tracks.csv`, `samples.csv` and export manifests retain `phase`. Portable project export/import carries it unchanged. Export folders remain grouped by species; phase is a separate column suitable for future phase-aware training. Unassessed/uncertain annotations are not phase-training ground truth. The current species classifier does not predict phase, and no phase classifier or measured phase accuracy is bundled.

## Interpretation

Initial phase can include females and primary males in diandric species. Do not use IP as a sex label, or infer sex/maturity from this field. Juvenile appearance likewise does not supply a measured size or age. The system records visible phase only, not sex, histology, gonadal maturity or a calibrated probability. Colour casts, illumination, poor resolution, intermediate patterns and occlusion can all make phase identification uncertain; use Phase uncertain rather than forcing IP/TP. No fixed body-length cutoffs are applied to unscaled video.

Sources:

- Manning et al. (2023), [Territoriality drives patterns of fixed space use in Caribbean parrotfishes](https://onlinelibrary.wiley.com/doi/full/10.1002/ece3.9833): distinction between IP females/primary males and TP, with species-dependent life histories.
- Hawkins & Roberts (2003), [Effects of fishing on sex-changing Caribbean parrotfishes](https://www.sciencedirect.com/science/article/abs/pii/S0006320703001198): colour phases and interpretation limits.
- [Florida Museum: Stoplight Parrotfish](https://www.floridamuseum.ufl.edu/discover-fish/species-profiles/stoplight-parrotfish/): illustrated juvenile, IP and TP reference for Sparisoma viride. Species-specific references are needed before making unfamiliar phase assignments.
