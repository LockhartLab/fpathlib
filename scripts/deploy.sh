# Full release: build docs, bump+push the patch tag, then build and upload
# to PyPI. Order matters -- tag.sh must run before pypi.sh so that HEAD is
# exactly on the new tag (clean release, no .devN) when pypi.sh builds.
# For an interim dev release without cutting a tag, run
# `source scripts/pypi.sh dev` directly instead of this script.
set -e

source scripts/docs.sh
source scripts/tag.sh "patch"
source scripts/pypi.sh
