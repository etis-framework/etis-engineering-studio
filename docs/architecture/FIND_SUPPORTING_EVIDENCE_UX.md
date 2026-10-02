# Find Supporting Evidence UX

This revision exposes the existing bounded equivalent-evidence discovery engine as a visible student action.

## Contract

- Find supporting evidence searches the active review's frozen snapshot.
- Inspect cited source opens the source already attached to the concern.
- Discovery sends only FINDING identity, not an exact PATH citation, so exact-path precedence cannot suppress the search.
- Unsent drafts are preserved.
- Cross-snapshot searches are blocked.
- Corrected/resolved findings do not present discovery as an active-finding action.
- With no active review, Studio starts a Finding Review and then runs the search automatically.
- The action itself never changes finding lifecycle state.
