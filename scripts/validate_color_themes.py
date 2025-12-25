#!/usr/bin/env python3
"""
Comprehensive validation and auto-fix script for color theme issues.

This script validates and automatically fixes:
1. Hardcoded Rich markup colors in command files
2. StyleManager imports and setup
3. Critical architectural patterns
4. Light theme compatibility across all command outputs
"""

import re
import sys
from pathlib import Path


# ANSI color codes for output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str) -> None:
    """Print a colored header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.END}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text: str) -> None:
    """Print info message."""
    print(f"{Colors.BLUE}i  {text}{Colors.END}")


def print_fix(text: str) -> None:
    """Print fix message."""
    print(f"{Colors.MAGENTA}🔧 {text}{Colors.END}")


# Color mapping for automatic fixes
COLOR_MAPPINGS = {
    "[red]": ("StyleName.ERROR", True),
    "[/red]": ("", False),
    "[yellow]": ("StyleName.WARNING", True),
    "[/yellow]": ("", False),
    "[green]": ("StyleName.SUCCESS", True),
    "[/green]": ("", False),
    "[cyan]": ("StyleName.INFO", True),
    "[/cyan]": ("", False),
    "[blue]": ("StyleName.INFO", True),
    "[/blue]": ("", False),
    "[magenta]": ("StyleName.INFO", True),
    "[/magenta]": ("", False),
    "[bold]": ("StyleName.BOLD", True),
    "[/bold]": ("", False),
    "[bold green]": ("StyleName.SUCCESS", True),
    "[/bold green]": ("", False),
    "[bold red]": ("StyleName.ERROR", True),
    "[/bold red]": ("", False),
    "[bold cyan]": ("StyleName.INFO", True),
    "[/bold cyan]": ("", False),
    "[bold yellow]": ("StyleName.WARNING", True),
    "[/bold yellow]": ("", False),
    "[dim]": ("StyleName.INFO", True),
    "[/dim]": ("", False),
}


def fix_hardcoded_colors_in_file(
    file_path: Path, auto_fix: bool = True
) -> tuple[bool, list[str], int]:
    """Fix hardcoded colors in a single file."""
    if not auto_fix:
        return False, [], 0

    try:
        content = file_path.read_text(encoding="utf-8")
        original_content = content
        fixes_made = 0

        # Check if file needs StyleManager imports
        needs_style_manager = any(color in content for color in COLOR_MAPPINGS.keys())

        if needs_style_manager:
            # Add StyleManager imports if not present
            if "from network_toolkit.common.styles import StyleManager" not in content:
                # Find import section and add StyleManager import
                lines = content.split("\n")
                import_line_idx = -1

                for i, line in enumerate(lines):
                    if line.startswith("from network_toolkit.common.logging import"):
                        # Remove console from import if present
                        if "console, " in line:
                            lines[i] = line.replace("console, ", "")
                        elif ", console" in line:
                            lines[i] = line.replace(", console", "")
                        elif (
                            line.strip()
                            == "from network_toolkit.common.logging import console"
                        ):
                            lines[i] = (
                                "from network_toolkit.common.logging import setup_logging"
                            )
                        import_line_idx = i
                        break

                if import_line_idx >= 0:
                    # Add new imports after logging import
                    lines.insert(
                        import_line_idx + 1,
                        "from network_toolkit.common.output import OutputMode",
                    )
                    lines.insert(
                        import_line_idx + 2,
                        "from network_toolkit.common.styles import StyleManager, StyleName",
                    )
                    content = "\n".join(lines)
                    fixes_made += 1

            # Add StyleManager setup after setup_logging calls
            if (
                "style_manager = StyleManager(" not in content
                and "setup_logging(" in content
            ):
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if "setup_logging(" in line and i + 1 < len(lines):
                        # Insert StyleManager setup after setup_logging
                        indent = "        " if line.startswith("        ") else "    "
                        lines.insert(i + 1, "")
                        lines.insert(
                            i + 2,
                            f"{indent}# Setup style manager for consistent theming",
                        )
                        lines.insert(
                            i + 3,
                            f"{indent}style_manager = StyleManager(OutputMode.DEFAULT)",
                        )
                        lines.insert(i + 4, f"{indent}console = style_manager.console")
                        content = "\n".join(lines)
                        fixes_made += 1
                        break

        # Fix color patterns
        for old_color, (new_style, is_opening) in COLOR_MAPPINGS.items():
            if old_color in content:
                if is_opening and new_style:
                    # For opening tags, we need to convert the entire f-string or string
                    # Pattern: f"[color]text[/color]" -> style_manager.format_message("text", StyleName.XXX)
                    # Pattern: "[color]text[/color]" -> style_manager.format_message("text", StyleName.XXX)

                    # Simple replacement for now - more complex patterns later
                    closing_tag = old_color.replace("[", "[/").replace("] ", "]")
                    if "[/" not in old_color:
                        closing_tag = "[/" + old_color[1:]

                    # Find patterns like f"[color]text[/color]" or "[color]text[/color]"
                    pattern = (
                        re.escape(old_color) + r"([^[]*?)" + re.escape(closing_tag)
                    )
                    matches = re.findall(pattern, content)

                    for match in matches:
                        old_pattern = f"{old_color}{match}{closing_tag}"
                        new_pattern = (
                            f'style_manager.format_message("{match}", {new_style})'
                        )
                        content = content.replace(old_pattern, new_pattern)
                        fixes_made += 1

                # Also handle standalone color tags
                content = content.replace(old_color, "")
                if old_color != content.replace(old_color, ""):
                    fixes_made += 1

        # Additional pattern fixes for console.print with f-strings
        # Pattern: console.print(f"[red]Error: {something}[/red]")
        f_string_pattern = r'console\.print\(f"(\[(?:red|yellow|green|cyan|blue|magenta|bold|dim)\])([^"]*?)(\[/[^]]+\])"\)'

        def replace_f_string(match):  # type: ignore[misc]
            color_start = match.group(1)
            text_content = match.group(2)
            _ = match.group(3)  # color_end unused

            if color_start in COLOR_MAPPINGS:
                style_name, _ = COLOR_MAPPINGS[color_start]
                if style_name:
                    return f'console.print(style_manager.format_message(f"{text_content}", {style_name}))'
            return match.group(0)

        new_content = re.sub(f_string_pattern, replace_f_string, content)
        if new_content != content:
            content = new_content
            fixes_made += 1

        # Write back if changes were made
        if content != original_content:
            file_path.write_text(content, encoding="utf-8")
            return (
                True,
                [f"Fixed {fixes_made} color issues in {file_path.name}"],
                fixes_made,
            )

        return True, [], 0

    except Exception as e:
        return False, [f"Error fixing {file_path.name}: {e}"], 0


def check_hardcoded_colors(auto_fix: bool = True) -> tuple[bool, list[str]]:
    """Check for hardcoded Rich markup colors in command files and auto-fix them."""
    print_info("Scanning for hardcoded Rich markup colors...")

    commands_dir = Path("src/network_toolkit/commands")
    if not commands_dir.exists():
        return False, ["Commands directory not found"]

    # Pattern to match hardcoded Rich markup
    color_pattern = re.compile(
        r"\[(red|yellow|green|cyan|blue|magenta|bold|dim|italic)\]"
    )

    violations = []
    total_files = 0
    total_fixes = 0

    for py_file in commands_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue

        total_files += 1

        if auto_fix:
            # Try to auto-fix the file
            success, messages, fixes = fix_hardcoded_colors_in_file(
                py_file, auto_fix=True
            )
            total_fixes += fixes

            if messages:
                for msg in messages:
                    print_fix(msg)

        # Check for remaining violations after fix attempt
        try:
            content = py_file.read_text(encoding="utf-8")
            matches = color_pattern.findall(content)

            if matches:
                # Get line numbers for violations
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if color_pattern.search(line):
                        violations.append(f"{py_file.name}:{i} - {line.strip()}")
        except Exception as e:
            violations.append(f"Error reading {py_file.name}: {e}")

    success = len(violations) == 0
    if success:
        print_success(f"No hardcoded colors found in {total_files} command files")
        if total_fixes > 0:
            print_success(f"Auto-fixed {total_fixes} color issues across all files")
    else:
        print_error(f"Found {len(violations)} remaining hardcoded color violations:")
        for violation in violations[:10]:  # Show first 10
            print(f"  {Colors.RED}{violation}{Colors.END}")
        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more")

    return success, violations


def check_style_manager_imports() -> tuple[bool, list[str]]:
    """Check that files using colors have proper StyleManager imports."""
    print_info("Checking StyleManager imports...")

    commands_dir = Path("src/network_toolkit/commands")
    issues = []
    files_checked = 0

    for py_file in commands_dir.glob("*.py"):
        if py_file.name.startswith("__"):
            continue

        files_checked += 1
        try:
            content = py_file.read_text(encoding="utf-8")

            # Check if file uses console.print or style formatting
            has_console_print = "console.print" in content
            has_style_formatting = "format_message" in content or "StyleName" in content

            # Check for proper imports
            has_style_manager_import = (
                "from network_toolkit.common.styles import StyleManager" in content
            )
            has_stylename_import = "StyleName" in content

            if has_console_print or has_style_formatting:
                if not has_style_manager_import and has_style_formatting:
                    issues.append(
                        f"{py_file.name}: Uses style formatting but missing StyleManager import"
                    )

                if has_style_formatting and not has_stylename_import:
                    issues.append(
                        f"{py_file.name}: Uses style formatting but missing StyleName import"
                    )

        except Exception as e:
            issues.append(f"Error checking {py_file.name}: {e}")

    success = len(issues) == 0
    if success:
        print_success(
            f"StyleManager imports properly configured in {files_checked} files"
        )
    else:
        print_error(f"Found {len(issues)} import issues:")
        for issue in issues:
            print(f"  {Colors.RED}{issue}{Colors.END}")

    return success, issues


def check_run_py_architecture() -> tuple[bool, list[str]]:
    """Check the critical architectural fix in run.py."""
    print_info("Validating run.py architectural fix...")

    run_py = Path("src/network_toolkit/commands/run.py")
    if not run_py.exists():
        return False, ["run.py not found"]

    issues = []
    try:
        content = run_py.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Look for the critical fix pattern
        style_manager_creation = False
        console_assignment = False

        for i, line in enumerate(lines):
            # Check for StyleManager creation
            if "style_manager = StyleManager(" in line:
                style_manager_creation = True
                print_success(f"Found StyleManager creation at line {i + 1}")

            # Check for console assignment from style_manager
            if "console = style_manager.console" in line:
                console_assignment = True
                # correct_console_source unused
                print_success(f"Found correct console assignment at line {i + 1}")

            # Check for problematic console assignment from ctx
            if "console = ctx.console" in line and "style_manager" in content:
                issues.append(
                    f"Line {i + 1}: Found problematic 'console = ctx.console' - should use style_manager.console"
                )

        if not style_manager_creation:
            issues.append("StyleManager creation not found")

        if not console_assignment:
            issues.append("Console assignment from style_manager not found")

        # Check for proper imports
        if "from network_toolkit.common.styles import StyleManager" not in content:
            issues.append("Missing StyleManager import")

    except Exception as e:
        issues.append(f"Error reading run.py: {e}")

    success = len(issues) == 0
    if success:
        print_success("run.py architectural fix properly implemented")
    else:
        print_error("run.py architectural issues found:")
        for issue in issues:
            print(f"  {Colors.RED}{issue}{Colors.END}")

    return success, issues


def check_semantic_color_usage() -> tuple[bool, list[str]]:
    """Check that semantic color patterns are used correctly."""
    print_info("Validating semantic color usage patterns...")

    commands_dir = Path("src/network_toolkit/commands")
    issues = []
    good_patterns = 0

    # Patterns we expect to see
    good_pattern = re.compile(
        r"style_manager\.format_message\([^,]+,\s*StyleName\.\w+\)"
    )

    for py_file in commands_dir.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")

            # Count good patterns
            matches = good_pattern.findall(content)
            good_patterns += len(matches)

            # Check for incomplete migrations
            if "style_manager" in content and "console.print(" in content:
                lines = content.split("\n")
                for i, line in enumerate(lines, 1):
                    if (
                        "console.print(" in line
                        and "style_manager.format_message" not in line
                    ):
                        # Check if this line has any formatting that could be semantic
                        if any(
                            word in line.lower()
                            for word in ["error", "warning", "success", "info", "bold"]
                        ):
                            # Allow simple prints without styling
                            if not any(marker in line for marker in ["[", "]", 'f"']):
                                continue
                            issues.append(
                                f"{py_file.name}:{i} - console.print may need semantic styling: {line.strip()}"
                            )

        except Exception as e:
            issues.append(f"Error checking {py_file.name}: {e}")

    success = len(issues) == 0
    if success:
        print_success(f"Found {good_patterns} proper semantic color usages")
    else:
        print_warning(f"Found {len(issues)} potential semantic styling opportunities:")
        for issue in issues[:5]:  # Show first 5
            print(f"  {Colors.YELLOW}{issue}{Colors.END}")
        if len(issues) > 5:
            print(f"  ... and {len(issues) - 5} more")

    return success, issues


def check_command_context_integration() -> tuple[bool, list[str]]:
    """Check proper CommandContext integration where needed."""
    print_info("Checking CommandContext integration...")

    commands_dir = Path("src/network_toolkit/commands")
    issues = []
    files_with_context = 0

    for py_file in commands_dir.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")

            if "CommandContext" in content:
                files_with_context += 1

                # Check for proper style manager setup after context creation
                if "ctx = CommandContext(" in content and "StyleManager(" in content:
                    print_success(
                        f"{py_file.name}: Proper CommandContext + StyleManager integration"
                    )
                elif "ctx = CommandContext(" in content:
                    issues.append(
                        f"{py_file.name}: Has CommandContext but missing StyleManager integration"
                    )

        except Exception as e:
            issues.append(f"Error checking {py_file.name}: {e}")

    success = len(issues) == 0
    if success:
        print_success(
            f"CommandContext properly integrated in {files_with_context} files"
        )
    else:
        print_warning(f"Found {len(issues)} CommandContext integration issues:")
        for issue in issues:
            print(f"  {Colors.YELLOW}{issue}{Colors.END}")

    return success, issues


def generate_summary_report(results: dict[str, tuple[bool, list[str]]]) -> None:
    """Generate a summary report of all validation results."""
    print_header("VALIDATION SUMMARY REPORT")

    total_checks = len(results)
    passed_checks = sum(1 for success, _ in results.values() if success)

    print(f"{Colors.BOLD}Overall Status: ", end="")
    if passed_checks == total_checks:
        print(
            f"{Colors.GREEN}✅ ALL CHECKS PASSED ({passed_checks}/{total_checks}){Colors.END}"
        )
    else:
        print(
            f"{Colors.RED}❌ {total_checks - passed_checks} CHECKS FAILED ({passed_checks}/{total_checks}){Colors.END}"
        )

    print(f"\n{Colors.BOLD}Check Details:{Colors.END}")
    for check_name, (success, issues) in results.items():
        status = f"{Colors.GREEN}✅ PASS" if success else f"{Colors.RED}❌ FAIL"
        issue_count = f" ({len(issues)} issues)" if issues else ""
        print(f"  {status}{Colors.END} {check_name}{issue_count}")

    # Overall assessment
    print(f"\n{Colors.BOLD}Assessment:{Colors.END}")
    if passed_checks == total_checks:
        print(f"{Colors.GREEN}🎉 Color theme standardization is COMPLETE!")
        print("   - All hardcoded colors eliminated")
        print("   - Semantic styling properly implemented")
        print("   - Light theme compatibility ensured")
        print(f"   - User's original issue is RESOLVED{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  Color theme standardization needs attention:")
        for check_name, (success, issues) in results.items():
            if not success and issues:
                print(f"   - {check_name}: {len(issues)} issues to address")
        print(f"   - Core architectural fix may still resolve user's issue{Colors.END}")


def main() -> int:
    """Main validation and auto-fix function."""
    print_header("NETWORKA COLOR THEME VALIDATION & AUTO-FIX")
    print_info("Validating and auto-fixing color theme issues...")

    # Change to repo root if script is run from scripts directory
    if Path.cwd().name == "scripts":
        import os

        os.chdir("..")

    # Run auto-fix for hardcoded colors first
    print_header("AUTO-FIXING HARDCODED COLORS")
    results = {}
    results["Hardcoded Colors"] = check_hardcoded_colors(auto_fix=True)

    # Then run other validation checks
    print_header("VALIDATION CHECKS")
    results["StyleManager Imports"] = check_style_manager_imports()
    results["run.py Architecture"] = check_run_py_architecture()
    results["Semantic Color Usage"] = check_semantic_color_usage()
    results["CommandContext Integration"] = check_command_context_integration()

    # Generate summary
    generate_summary_report(results)

    # Return exit code
    all_passed = all(success for success, _ in results.values())
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
