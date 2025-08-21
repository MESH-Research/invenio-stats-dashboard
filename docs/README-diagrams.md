# EventReindexingService Diagrams

This folder contains Mermaid diagram files that visualize the EventReindexingService architecture and flow.

## Available Diagrams

1. **`event-reindexing-flow.mmd`** - Main flowchart showing the complete migration process
2. **`health-checks-failure-handling.mmd`** - Health checks and failure handling mechanisms
3. **`event-reindexing-sequence.mmd`** - Sequence diagram showing component interactions

## How to View/Convert These Diagrams

### Option 1: Online Mermaid Editor
1. Go to [Mermaid Live Editor](https://mermaid.live/)
2. Copy and paste the content of any `.mmd` file
3. The diagram will render automatically
4. Export as PNG, SVG, or PDF

### Option 2: GitHub/GitLab
- These `.mmd` files will automatically render in GitHub and GitLab when viewed
- Just open the file in your repository and the diagram will display

### Option 3: VS Code Extension
1. Install the "Mermaid Preview" extension
2. Open any `.mmd` file
3. Use `Ctrl+Shift+P` and select "Mermaid Preview: Open Preview"

### Option 4: Command Line (Node.js)
```bash
# Install mermaid-cli globally
npm install -g @mermaid-js/mermaid-cli

# Convert to PNG
mmdc -i event-reindexing-flow.mmd -o event-reindexing-flow.png

# Convert to SVG
mmdc -i event-reindexing-flow.mmd -o event-reindexing-flow.svg
```

### Option 5: Python Script
```python
# Install mermaid-cli Python wrapper
pip install mermaid-cli

# Convert diagrams
import mermaid_cli
mermaid_cli.run('event-reindexing-flow.mmd', 'event-reindexing-flow.png')
```

## Diagram Descriptions

### Event Reindexing Flow
Shows the complete process from template preparation through data migration, validation, and cleanup. Includes all decision points and error handling paths.

### Health Checks & Failure Handling
Shows how health checks and error handling are integrated throughout the migration process, including pre-migration checks, per-batch monitoring, failure recovery, and rollback strategies. This diagram demonstrates the practical application of these mechanisms rather than just listing them.

### Event Reindexing Sequence
Illustrates the interaction between different components during the migration process, showing the sequence of operations and data flow.

## Customization

You can modify these diagrams by editing the `.mmd` files. The Mermaid syntax is well-documented at [mermaid-js.github.io](https://mermaid-js.github.io/).

## Integration with Documentation

These diagrams can be embedded in:
- Sphinx documentation using the `mermaid` extension
- Markdown files (GitHub/GitLab will auto-render them)
- HTML documentation
- PDF exports (when converted to images)
