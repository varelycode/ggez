# Versioning

ggez uses SemVer. `ggez --version` reads the version embedded in `scripts/ggez.py`.

`main` is the update channel. Every change to the install payload must bump the version. Tag the merged commit `vX.Y.Z`.

The installer also stores each payload under its SHA-256 hash. The version names the release; the hash verifies its exact files and supports safe activation.
