#!/usr/bin/env python3
"""Generate JSON schema for network toolkit configuration files."""

import json
import sys
from pathlib import Path

# Add src to path so we can import our modules
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import after path modification
from network_toolkit.config import generate_json_schema  # noqa: E402


def main() -> None:
    """Generate and save JSON schema for NetworkConfig."""
    try:
        schema = generate_json_schema()

        # Add metadata for YAML editor support
        schema["$id"] = "https://narrowin.github.io/networka/schemas/config.json"
        schema["title"] = "Network Toolkit Configuration"
        schema["description"] = "JSON Schema for Network Toolkit configuration files"

        # Output paths
        schema_file = project_root / "config-schema.json"
        docs_schema_file = project_root / "docs" / "config-schema.json"

        # Write schema to multiple locations
        for output_file in [schema_file, docs_schema_file]:
            output_file.parent.mkdir(exist_ok=True)
            with output_file.open("w", encoding="utf-8") as f:
                json.dump(schema, f, indent=2, sort_keys=True)
            print(f"✅ Generated schema: {output_file}")

        # Generate VS Code settings snippet
        vscode_snippet = {
            "yaml.schemas": {
                "./config-schema.json": [
                    "config.yml",
                    "config.yaml",
                    "devices.yml",
                    "devices.yaml",
                    "groups.yml",
                    "groups.yaml",
                    "sequences.yml",
                    "sequences.yaml",
                    "config/config.yml",
                    "config/config.yaml",
                    "config/devices/*.yml",
                    "config/devices/*.yaml",
                    "config/groups/*.yml",
                    "config/groups/*.yaml",
                    "config/sequences/*.yml",
                    "config/sequences/*.yaml",
                ]
            }
        }

        vscode_file = project_root / ".vscode" / "settings.json"
        vscode_file.parent.mkdir(exist_ok=True)
        with vscode_file.open("w", encoding="utf-8") as f:
            json.dump(vscode_snippet, f, indent=2)
        print(f"✅ Generated VS Code settings: {vscode_file}")

        print("\n📝 To enable YAML validation in VS Code:")
        print("1. Install the 'YAML' extension by Red Hat")
        print("2. The schema is automatically configured via .vscode/settings.json")
        print("3. Open any config YAML file to see validation and auto-completion")

    except Exception as e:
        print(f"❌ Error generating schema: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
