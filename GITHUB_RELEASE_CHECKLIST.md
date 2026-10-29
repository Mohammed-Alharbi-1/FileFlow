# Release readiness checklist

- [x] Owner explicitly authorized one-shot public publication.
- [x] Active authenticated GitHub account verified; no existing FileFlow repository found.
- [x] Standalone snapshot only; original application source unchanged.
- [x] Source license deferred; inactive MIT draft moved outside root LICENSE.
- [x] Exact LGPL library sources, notices and replacement rights prepared.
- [x] Full local source tests: 115 passed.
- [x] Static/privacy scan and memory/responsiveness checks passed.
- [ ] Fresh native Windows package, extraction and tray/lifecycle validation.
- [ ] Private staging source pushed and hosted CI passed.
- [ ] Exact source tag and draft assets/checksum verified.
- [ ] Repository visibility and release made public; URLs verified.

Only complete publication after every remaining item passes. Future releases
require a new compliance review and explicit workflow/CLI release controls.
