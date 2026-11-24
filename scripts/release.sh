#!/usr/bin/env bash
# Release script for networka
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Parse command line arguments
VERSION=""
DRY_RUN=false
RELEASE_BRANCH=main
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        --branch)
            RELEASE_BRANCH="${2:?Specify the checked-out release branch}"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 -v VERSION [--branch BRANCH] [--dry-run] [--force]"
            echo ""
            echo "Options:"
            echo "  -v, --version    Version to release (e.g., 1.0.0)"
            echo "  --branch         Expected release branch (default main)"
            echo "  --dry-run        Show what would be done without making changes"
            echo "  -f, --force      Skip branch and pre-release marker checks"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Example - Full release workflow:"
            echo "  1. Run pre-release checks:"
            echo "     ./scripts/pre-release-check.sh"
            echo ""
            echo "  2. Create and push the release:"
            echo "     ./scripts/release.sh -v 1.2.3"
            echo ""
            echo "  Tip: Use --dry-run first to preview changes:"
            echo "     ./scripts/release.sh -v 1.2.3 --dry-run"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    echo "ERROR: Version is required. Use -v VERSION"
    exit 1
fi

# Use the same canonical spelling that appears in the wheel filename.
if [[ ! "$VERSION" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)((a|b|rc)(0|[1-9][0-9]*))?$ ]]; then
    echo "Expected a version such as 1.2.3 or 1.2.3rc1"
    exit 1
fi

echo "Preparing release v$VERSION..."

if [[ "$DRY_RUN" == true ]]; then
    echo "DRY RUN MODE - No changes will be made"
fi

# Check if we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ -z "$CURRENT_BRANCH" ]]; then
    echo "Check out the branch to release first"
    exit 1
fi
if [[ "$CURRENT_BRANCH" != "$RELEASE_BRANCH" ]] && [[ "$FORCE" != true ]]; then
    echo "Expected branch $RELEASE_BRANCH. Current branch: $CURRENT_BRANCH"
    echo "Use --branch to select an intentional maintenance release branch."
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "ERROR: There are uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Check if pre-release checks were run (unless --force is used)
if [[ "$FORCE" != true ]]; then
    MARKER_FILE=".pre-release-passed"
    CURRENT_COMMIT=$(git rev-parse HEAD)

    if [[ ! -f "$MARKER_FILE" ]]; then
        echo ""
        echo "ERROR: Pre-release quality checks not run!"
        echo ""
        echo "You must run pre-release checks before creating a release:"
        echo "   ./scripts/pre-release-check.sh"
        echo ""
        echo "This ensures all quality checks pass before pushing the release."
        echo "Use --force to skip this check (not recommended)."
        echo ""
        exit 1
    fi

    # Verify marker is for current commit
    MARKER_COMMIT=$(grep "COMMIT_HASH=" "$MARKER_FILE" | cut -d'=' -f2)
    if [[ "$MARKER_COMMIT" != "$CURRENT_COMMIT" ]]; then
        echo ""
        echo "ERROR: Pre-release checks are outdated!"
        echo ""
        echo "Code has changed since pre-release checks were run."
        echo "Marker commit: $MARKER_COMMIT"
        echo "Current commit: $CURRENT_COMMIT"
        echo ""
        echo "Run pre-release checks again:"
        echo "   ./scripts/pre-release-check.sh"
        echo ""
        exit 1
    fi

    MARKER_TIMESTAMP=$(grep "TIMESTAMP=" "$MARKER_FILE" | cut -d'=' -f2)
    echo ""
    echo "✓ Pre-release quality checks verified"
    echo "   Commit: $MARKER_COMMIT"
    echo "   Time:   $MARKER_TIMESTAMP"
    echo ""
else
    echo ""
    echo "WARNING: Skipping pre-release check verification (--force used)"
    echo "   GitHub Actions will still install and check both release archives"
    echo ""
fi

# Check if tag already exists
if git show-ref --verify --quiet "refs/tags/v$VERSION"; then
    echo "ERROR: Tag v$VERSION already exists."
    exit 1
fi

# Check current version in file
CURRENT_VERSION=$(grep -o '__version__ = "[^"]*"' src/network_toolkit/__about__.py | cut -d'"' -f2)
echo "Current version in __about__.py: $CURRENT_VERSION"
echo "Target version: $VERSION"

# Update version in __about__.py
VERSION_FILE="src/network_toolkit/__about__.py"
if [[ "$DRY_RUN" != true ]]; then
    echo "Updating version in $VERSION_FILE..."
    sed -i.bak "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" "$VERSION_FILE"
    rm -f "$VERSION_FILE.bak"

    # Verify the change
    NEW_VERSION=$(grep -o '__version__ = "[^"]*"' src/network_toolkit/__about__.py | cut -d'"' -f2)
    if [[ "$NEW_VERSION" != "$VERSION" ]]; then
        echo "ERROR: Failed to update version. Expected $VERSION, got $NEW_VERSION"
        exit 1
    fi
    echo "Version updated successfully: $CURRENT_VERSION -> $VERSION"
else
    echo "Would update version in $VERSION_FILE to $VERSION"
fi

# Update CHANGELOG.md
CHANGELOG_FILE="CHANGELOG.md"
TODAY=$(date +%Y-%m-%d)

if [[ "$DRY_RUN" != true ]]; then
    echo "Updating CHANGELOG.md..."
    python3 - "$CHANGELOG_FILE" "$VERSION" "$TODAY" <<'PYTHON'
from pathlib import Path
import sys

path = Path(sys.argv[1])
version, today = sys.argv[2:]
text = path.read_text()
header = f"## [{version}]"
if header in text.splitlines():
    text = text.replace(header + "\n", f"{header} - {today}\n", 1)
elif not any(line.startswith(header + " - ") for line in text.splitlines()):
    if "## [Unreleased]" not in text.splitlines():
        raise SystemExit("Missing Unreleased section in CHANGELOG.md")
    text = text.replace("## [Unreleased]\n", f"## [Unreleased]\n\n{header} - {today}\n", 1)
path.write_text(text)
PYTHON

else
    echo "Would update CHANGELOG.md with version $VERSION and date $TODAY"
fi

# Update CITATION.cff version and date if file exists
CITATION_FILE="CITATION.cff"
if [[ -f "$CITATION_FILE" ]]; then
    if [[ "$DRY_RUN" != true ]]; then
        echo "Updating CITATION.cff version and date..."
        # Simple sed updates for version and date only
        sed -i.bak "s/^version: .*/version: \"$VERSION\"/" "$CITATION_FILE"
        sed -i.bak "s/^date-released: .*/date-released: \"$TODAY\"/" "$CITATION_FILE"
        rm -f "$CITATION_FILE.bak"
        echo "CITATION.cff updated: version $VERSION, date $TODAY"
    else
        echo "Would update CITATION.cff with version $VERSION and date $TODAY"
    fi
fi

# Validate CITATION.cff if it exists
if [[ -f "CITATION.cff" ]]; then
    if [[ "$DRY_RUN" != true ]]; then
        echo "Validating CITATION.cff..."
        if command -v cffconvert >/dev/null 2>&1; then
            if cffconvert --validate; then
                echo "CITATION.cff is valid"
            else
                echo "WARNING: CITATION.cff validation failed"
            fi
        else
            echo "cffconvert not found - skipping CITATION.cff validation"
        fi
    else
        echo "Would validate CITATION.cff"
    fi
fi

# Update uv.lock with new version
if [[ "$DRY_RUN" != true ]]; then
    echo "Updating uv.lock..."
    uv lock
else
    echo "Would update uv.lock"
fi

# Commit changes
COMMIT_FILES=("$VERSION_FILE" "$CHANGELOG_FILE" "uv.lock")
if [[ -f "$CITATION_FILE" ]]; then
    COMMIT_FILES+=("$CITATION_FILE")
fi

if [[ "$DRY_RUN" != true ]]; then
    echo "Committing release changes..."
    git add "${COMMIT_FILES[@]}"
    if ! git diff --cached --quiet; then
        git commit -m "chore: prepare v$VERSION for release"
    fi
else
    echo "Would commit release changes: ${COMMIT_FILES[*]}"
fi

if [[ "$DRY_RUN" != true ]]; then
    git tag -a "v$VERSION" -m "Release v$VERSION"
    git push --atomic origin "HEAD:refs/heads/$CURRENT_BRANCH" "refs/tags/v$VERSION"
else
    echo "Would push $CURRENT_BRANCH and new tag v$VERSION atomically"
fi

echo ""
echo "Release v$VERSION prepared successfully!"
echo ""
if [[ "$DRY_RUN" != true ]]; then
    # Clean up pre-release marker file
    if [[ -f ".pre-release-passed" ]]; then
        rm -f ".pre-release-passed"
        echo "Cleaned up pre-release marker file"
    fi

    echo ""
    echo "Next steps:"
    echo "   1. GitHub Actions will automatically build and publish to PyPI"
    echo "   2. A GitHub release will be created automatically"
    echo "   3. Monitor the CI/CD pipeline: https://github.com/narrowin/networka/actions"
else
    echo "This was a dry run. Use without --dry-run to execute the release."
fi
