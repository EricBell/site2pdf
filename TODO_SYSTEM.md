# Todo Management System Documentation

## Overview

The site2pdf project includes a comprehensive todo management system that uses **markdown files with YAML frontmatter** stored in a **folder-based structure**. This approach provides human-readable todos that work seamlessly with version control systems.

## Architecture

### Storage Format

Each todo is stored as an individual markdown file with:
- **YAML frontmatter** containing metadata (priority, status, dates, etc.)
- **Markdown body** with the todo description as heading
- **Notes section** for timestamped notes

### Folder Structure

```
todos/
├── pending/           # Active todos awaiting work
├── in_progress/      # Todos currently being worked on  
├── completed/        # Finished todos (preserved for history)
└── cancelled/        # Cancelled todos
```

**Status-Based Organization:**
- Todos automatically move between folders when status changes
- Completed todos are **marked and preserved**, not deleted
- File organization makes it easy to see project status at a glance

## File Format

### Example Todo File (`todos/pending/a1b2c3d4.md`)

```markdown
---
id: a1b2c3d4
priority: high
category: bug
status: pending
created: '2025-08-23T22:23:33.477531'
due_date: '2025-08-25'
completed: null
---

# Fix PDF generation error with large images

PDF generation crashes when processing images larger than 10MB. Need to implement image resizing or memory optimization.

## Notes
**2025-08-23 22:25**: Added debug logging to identify root cause
**2025-08-24 09:15**: Reproduced issue with 15MB test image
```

### YAML Frontmatter Fields

- **id**: Unique identifier (8-character UUID)
- **priority**: `low`, `medium`, `high`, `urgent`
- **category**: Custom categories (`bug`, `feature`, `docs`, etc.)
- **status**: `pending`, `in_progress`, `completed`, `cancelled`
- **created**: ISO datetime when todo was created
- **due_date**: ISO date string or `null`
- **completed**: ISO datetime when marked completed or `null`

## CLI Commands

### Adding Todos

```bash
# Basic todo
python run.py todo add "Fix authentication bug"

# With priority and due date
python run.py todo add "Implement user dashboard" --priority high --due today

# With category
python run.py todo add "Update README" --priority low --category docs
```

### Listing and Filtering

```bash
# List active todos
python run.py todo list

# Include completed todos
python run.py todo list --completed

# Filter by status
python run.py todo list --status in_progress

# Filter by priority
python run.py todo list --priority high

# Filter by category
python run.py todo list --category bug
```

### Managing Todos

```bash
# Show detailed information
python run.py todo show a1b2c3d4

# Update status (automatically moves file)
python run.py todo update a1b2c3d4 --status in_progress

# Add notes
python run.py todo note a1b2c3d4 "Found root cause in image processing"

# Mark completed
python run.py todo done a1b2c3d4

# Search todos
python run.py todo search "authentication"

# View statistics
python run.py todo stats
```

## Benefits of Markdown-Based Storage

### 1. **Human Readable**
- Todos are plain text markdown files
- Easy to read and understand without special tools
- Can be edited directly in any text editor

### 2. **Version Control Friendly**
- Each todo is a separate file - better for Git diffs
- Status changes create meaningful commit history
- Easy to track todo evolution over time

### 3. **Portable and Searchable**
- No database dependencies
- Works with standard file search tools (`grep`, `find`, etc.)
- Compatible with any markdown viewer

### 4. **Organized Structure**
- Status-based folders provide visual organization
- Easy to see project status at directory level
- Completed todos preserved for project history

### 5. **Integration Ready**
- Works with markdown-aware tools and editors
- Compatible with documentation systems
- Can be included in project wikis or knowledge bases

## Migration from YAML Format

The system includes automatic migration from the old `todos.yaml` format:

1. **Automatic Detection**: Finds existing YAML todo files
2. **Preservation**: All data (metadata, notes, timestamps) preserved
3. **Organization**: Todos placed in appropriate status folders
4. **Backup**: Original YAML file backed up before migration

## Technical Implementation

### Core Classes

- **TodoManager**: Main interface for todo operations
- **File Operations**: Handles markdown parsing and generation
- **Status Management**: Moves files between folders on status changes

### File Operations

- **Create**: New todos → `pending/` folder
- **Update**: Status changes → move between folders
- **Delete**: Remove file completely
- **Notes**: Append to markdown file with timestamps

### Search and Filtering

- **Full-text search**: Searches descriptions, categories, and notes
- **Metadata filtering**: Filter by status, priority, category
- **Statistics**: Aggregate counts and progress tracking

## Configuration

The todo system works out of the box with minimal configuration. The `TodoManager` class automatically:

- Creates directory structure if needed
- Uses project-relative `./todos/` directory
- Handles file creation and organization
- Maintains data consistency

## Future Enhancements

Potential improvements to the markdown-based system:

- **Tags**: Support for hashtag-based tagging
- **Templates**: Custom todo templates for different types
- **Attachments**: Link to related files or external resources
- **Dependencies**: Link todos to show relationships
- **Time Tracking**: Built-in time logging capabilities

## Conclusion

The markdown-based todo system provides a robust, human-readable, and version-control-friendly approach to project task management. By using individual files organized in status-based folders, it offers excellent visibility into project progress while maintaining compatibility with standard development workflows.