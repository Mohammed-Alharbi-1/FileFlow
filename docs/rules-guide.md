# Rules guide

Rules are evaluated in configured order before the category fallback. An enabled
extension rule for `pdf` can route to `Reading/PDF`; filename-contains `invoice`
can route to `Work/Invoices`. Disabled rules do not match.

Destinations must be relative paths inside the selected root. Parent traversal,
absolute paths, invalid Windows names and unsafe junction/symlink routes are
rejected. Temporary-download extensions are ignored before rules. Rules do not
run scripts, inspect document content, recurse through nested folders or execute
installers. Overlapping watched roots are rejected by settings validation.
