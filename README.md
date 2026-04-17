# ctx.py

A lightweight, zero-dependency tool for preparing structured context prompts for LLMs when working with code generation tasks.

## What It Does

ctx.py helps you quickly assemble project context—codebase structure, selected files, and custom guidelines—into a formatted output ready for copy-paste into LLM chat interfaces (Claude, ChatGPT, etc.).

## Features

- **Zero dependencies** - Uses Python standard library only
- **Single file** - Easy to copy anywhere
- **Interactive file selection** - Terminal UI with keyboard navigation
- **Preset file selections** - Save/load common file selections per project
- **Clipboard support** - Copy output directly to clipboard
- **Smart ignore handling** - Respects `.gitignore` + common dev patterns
- **Token estimation** - Shows rough token count for context size management
- **Constitution support** - Include project-specific guidelines for LLMs
- **Three workflow modes** - Quick for simple tasks, full for complex requirements, lite for weaker models

## Requirements

Python 3.7+

## Usage

```bash
python ctx.py
```

This launches an interactive workflow:

1. **Select mode** - Quick or full workflow
2. **Describe task** - Multi-line input (type `END` to finish)
3. **Include constitution** - If found, optionally include project guidelines
4. **Select files** - Load a preset or make a custom selection
5. **Save preset** - Optionally save your selection for reuse
6. **Output** - Generates `llm_context.txt` and offers to copy to clipboard

### Keyboard Controls (File Selection)

| Key | Action |
|-----|--------|
| ↑/↓ | Navigate files |
| SPACE | Toggle selection |
| ENTER | Confirm selection |

## Workflow Modes

### Quick Mode

For straightforward tasks with clear requirements. The LLM receives simple instructions to implement directly.

### Full Mode (3-Phase)

For complex or ambiguous requirements:

1. **Clarification** - LLM asks questions to understand the task
2. **Specification** - LLM produces spec and plan, waits for approval
3. **Implementation** - LLM implements after you approve

### Lite Mode

For weaker models (e.g. Gemini 2.5) that struggle with the full 3-phase workflow. The prompt is flattened: task goes up front, instructions become numbered imperatives, no clarification phase, no approval gates, and a concrete `FILE:` output format is shown literally. Task is also restated at the end to counter recency bias in long prompts.

## Project Constitution

Create a `CONSTITUTION.md` in your project root to provide persistent guidelines for LLMs. This can include:

- Project overview and tech stack
- Architecture guidelines
- Code conventions
- Patterns to follow/avoid
- Testing approach

See `CONSTITUTION_TEMPLATE.md` for a starting template.

Supported locations:
- `CONSTITUTION.md`
- `.ctx/constitution.md`
- `constitution.md`

## File Selection Presets

Save commonly used file selections to avoid reselecting the same files repeatedly.

### How It Works

1. When presets exist, you'll be prompted to load one or make a custom selection
2. Loading a preset pre-selects those files (you can still modify the selection)
3. After selecting files, you can save the selection as a new preset
4. Presets are stored in `.ctx/presets.json`

### Preset Storage

Presets are stored as JSON in `.ctx/presets.json`:

```json
{
  "backend": [
    "src/api.py",
    "src/models.py",
    "src/database.py"
  ],
  "frontend": [
    "components/App.tsx",
    "components/Header.tsx"
  ]
}
```

If files in a preset no longer exist (renamed/deleted), they're skipped with a warning.

## Output Format

The generated `llm_context.txt` contains:

```
<context>
Project metadata and timestamp
</context>

<instructions> or <workflow>
Mode-specific instructions for the LLM
</instructions>

<task>
Your task description
</task>

<constitution>
Project guidelines (if included)
</constitution>

<directory_tree>
Project structure visualization
</directory_tree>

<codebase>
Selected file contents with paths
</codebase>
```

## Configuration

Edit constants in the Configuration section of `ctx.py`:

```python
OUTPUT_FILE = "llm_context.txt"
CONSTITUTION_PATHS = ["CONSTITUTION.md", ".ctx/constitution.md", "constitution.md"]
PRESETS_PATH = ".ctx/presets.json"
MAX_TREE_DEPTH = 6
DEFAULT_IGNORE_PATTERNS = {...}
```
