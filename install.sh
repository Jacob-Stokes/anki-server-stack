#!/usr/bin/env bash
# The installer: the same as ./anki-stack install.
exec "$(dirname "$0")/anki-stack" install "$@"
