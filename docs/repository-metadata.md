# Repository and release controls

Authenticated publication owner: Mohammed-Alharbi-1 (verified with GitHub CLI).
Copyright attribution: M.Alharbi. These names are not inferred from each other.
Repository name: FileFlow. Source license decision: deferred.

The first launch uses private staging, passing hosted Windows CI, an exact tested
commit/tag and manually verified draft assets before public visibility/release.
Future release builds require manual workflow dispatch on a matching version tag
and an explicit distribution-reviewed input. The workflow only uploads review
artifacts; it cannot publish releases. Publication and native tray validation
remain separate deliberate steps. No release is generated automatically on tags.
