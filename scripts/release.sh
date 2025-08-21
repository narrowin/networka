#!/usr/bin/env bash
# Release script for networka
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Parse command line arguments
VERSION=""
DRY_RUN=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--version)
            VERSION="$2"
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
            echo "Usage: $0 -v VERSION [--dry-run] [--force]"
            echo ""
            echo "Options:"
            echo "  -v, --version    Version to release (e.g., 1.0.0)"
            echo "  --dry-run        Show what would be done without making changes"
            echo "  -f, --force      Force release even if version exists"
            echo "  -h, --help       Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

if [[ -z "$VERSION" ]]; then
    echo "❌ Version is required. Use -v VERSION"
    exit 1
fi

# Validate version format (basic semver check)
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
    echo "❌ Invalid version format. Use semantic versioning (e.g., 1.0.0, 1.0.0-beta1)"
    exit 1
fi

echo "🚀 Preparing release v$VERSION..."

if [[ "$DRY_RUN" == true ]]; then
    echo "🔍 DRY RUN MODE - No changes will be made"
fi

# Check if we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]] && [[ "$FORCE" != true ]]; then
    echo "❌ Not on main branch. Current branch: $CURRENT_BRANCH"
    echo "   Use --force to release from current branch"
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "❌ There are uncommitted changes. Please commit or stash them first."
    exit 1
fi

# Check if tag already exists
if git tag | grep -q "^v$VERSION$" && [[ "$FORCE" != true ]]; then
    echo "❌ Tag v$VERSION already exists. Use --force to overwrite"
    exit 1
fi

# Update version in __about__.py
VERSION_FILE="src/network_toolkit/__about__.py"
if [[ "$DRY_RUN" != true ]]; then
    echo "📝 Updating version in $VERSION_FILE..."
    sed -i.bak "s/__version__ = \".*\"/__version__ = \"$VERSION\"/" "$VERSION_FILE"
    rm -f "$VERSION_FILE.bak"
else
    echo "📝 Would update version in $VERSION_FILE to $VERSION"
fi

# Update CHANGELOG.md
CHANGELOG_FILE="CHANGELOG.md"
TODAY=$(date +%Y-%m-%d)

if [[ "$DRY_RUN" != true ]]; then
    echo "📝 Updating CHANGELOG.md..."
    # Replace [Unreleased] with [VERSION] - DATE and add new [Unreleased] section
    sed -i.bak "s/## \[Unreleased\]/## [$VERSION] - $TODAY/" "$CHANGELOG_FILE"

    # Add new unreleased section at the top
    TEMP_FILE=$(mktemp)
    head -n 8 "$CHANGELOG_FILE" > "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
    echo "## [Unreleased]" >> "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
    echo "### Added" >> "$TEMP_FILE"
    echo "- " >> "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
    echo "### Changed" >> "$TEMP_FILE"
    echo "- " >> "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
    echo "### Fixed" >> "$TEMP_FILE"
    echo "- " >> "$TEMP_FILE"
    echo "" >> "$TEMP_FILE"
    tail -n +9 "$CHANGELOG_FILE" >> "$TEMP_FILE"
    mv "$TEMP_FILE" "$CHANGELOG_FILE"
    rm -f "$CHANGELOG_FILE.bak"
else
    echo "📝 Would update CHANGELOG.md with version $VERSION and date $TODAY"
fi

# Update uv.lock with new version
if [[ "$DRY_RUN" != true ]]; then
    echo "🔄 Updating uv.lock..."
    uv sync
else
    echo "🔄 Would update uv.lock"
fi

# Commit changes
if [[ "$DRY_RUN" != true ]]; then
    echo "💾 Committing release changes..."
    git add "$VERSION_FILE" "$CHANGELOG_FILE" uv.lock
    git commit --no-verify -m "chore: bump version to v$VERSION"
else
    echo "💾 Would commit release changes"
fi

# Create and push tag
if [[ "$DRY_RUN" != true ]]; then
    echo "🏷️  Creating tag v$VERSION..."
    git tag -a "v$VERSION" -m "Release v$VERSION"

    echo "📤 Pushing changes and tag..."
    git push origin main
    git push origin "v$VERSION"
else
    echo "🏷️  Would create tag v$VERSION"
    echo "📤 Would push changes and tag"
fi

echo ""
echo "✅ Release v$VERSION prepared successfully!"
echo ""
if [[ "$DRY_RUN" != true ]]; then
    echo "🎯 Next steps:"
    echo "   1. GitHub Actions will automatically build and publish to PyPI"
    echo "   2. A GitHub release will be created automatically"
    echo "   3. Monitor the CI/CD pipeline: https://github.com/narrowin/networka/actions"
else
    echo "🔍 This was a dry run. Use without --dry-run to execute the release."
fi
