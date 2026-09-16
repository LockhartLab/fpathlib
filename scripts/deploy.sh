# Full release: build docs, bump+push the patch tag, build and upload to
# PyPI, then build and upload to conda (lockhartlab org). Order matters --
# tag.sh must run before pypi.sh so that HEAD is exactly on the new tag
# (clean release, no .devN) when pypi.sh builds, and conda.sh must run
# after pypi.sh since it packages what was just published to PyPI.
# For an interim dev release without cutting a tag, run
# `source scripts/pypi.sh dev` directly instead of this script.
set -e

source scripts/docs.sh
source scripts/tag.sh "patch"
source scripts/pypi.sh
source scripts/conda.sh
