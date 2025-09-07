#!/usr/bin/env python3
"""
Markdown-based Todo Management System for site2pdf

Provides functionality to manage tasks with priorities, due dates, and status tracking.
Todos are stored as individual markdown files in a folder structure organized by status.
"""

import os
import yaml
import shutil
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
import re


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    URGENT = "urgent"


class Status(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoManager:
    """Manages todos stored as markdown files in folder structure."""
    
    def __init__(self, todos_dir: str = None):
        if todos_dir is None:
            # Use project directory by default
            todos_dir = os.path.join(os.getcwd(), 'todos')
        
        self.todos_dir = todos_dir
        self._ensure_directory_structure()
        
        # Status folder mapping
        self.status_folders = {
            Status.PENDING.value: 'pending',
            Status.IN_PROGRESS.value: 'in_progress', 
            Status.COMPLETED.value: 'completed',
            Status.CANCELLED.value: 'cancelled'
        }
    
    def _ensure_directory_structure(self):
        """Ensure todos directory structure exists."""
        os.makedirs(self.todos_dir, exist_ok=True)
        for folder in ['pending', 'in_progress', 'completed', 'cancelled']:
            os.makedirs(os.path.join(self.todos_dir, folder), exist_ok=True)
    
    def _parse_markdown_file(self, filepath: str) -> Optional[Dict[str, Any]]:
        """Parse a markdown todo file and extract metadata and content."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split frontmatter and content
            parts = content.split('---', 2)
            if len(parts) < 3:
                return None
            
            # Parse YAML frontmatter
            frontmatter = yaml.safe_load(parts[1])
            markdown_content = parts[2].strip()
            
            # Extract description from first heading
            lines = markdown_content.split('\n')
            description = ''
            content_lines = []
            notes = []
            
            in_notes = False
            for line in lines:
                if line.startswith('# '):
                    description = line[2:].strip()
                elif line.startswith('## Notes'):
                    in_notes = True
                elif in_notes and line.strip() and not line.startswith('<!--'):
                    # Parse notes (assume simple format for now)
                    notes.append({'text': line.strip(), 'timestamp': frontmatter.get('created', '')})
                elif not in_notes and line.strip():
                    content_lines.append(line)
            
            if not description and content_lines:
                description = ' '.join(content_lines)
            
            # Merge frontmatter with parsed content
            todo = frontmatter.copy()
            todo['description'] = description
            todo['notes'] = notes
            
            return todo
        
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            return None
    
    def _save_todo_file(self, todo_id: str, todo: Dict[str, Any]) -> bool:
        """Save a single todo as a markdown file."""
        try:
            status = todo.get('status', Status.PENDING.value)
            folder = self.status_folders.get(status, 'pending')
            filepath = os.path.join(self.todos_dir, folder, f"{todo_id}.md")
            
            # Prepare frontmatter (exclude description and notes)
            frontmatter = {k: v for k, v in todo.items() if k not in ['description', 'notes']}
            frontmatter['id'] = todo_id
            
            # Build markdown content
            content = "---\n"
            content += yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
            content += "---\n\n"
            content += f"# {todo.get('description', 'Untitled Todo')}\n\n"
            
            # Add notes if any
            content += "## Notes\n"
            if todo.get('notes'):
                for note in todo['notes']:
                    timestamp = note.get('timestamp', '')
                    if timestamp:
                        try:
                            dt = datetime.fromisoformat(timestamp)
                            formatted_time = dt.strftime('%Y-%m-%d %H:%M')
                            content += f"**{formatted_time}**: {note['text']}\n\n"
                        except:
                            content += f"{note['text']}\n\n"
                    else:
                        content += f"{note['text']}\n\n"
            else:
                content += "<!-- Notes will be added here as they're created -->\n"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
        
        except Exception as e:
            print(f"Error saving todo {todo_id}: {e}")
            return False
    
    def add_todo(self, description: str, priority: str = "medium", due_date: Optional[str] = None, 
                 category: str = "general") -> str:
        """Add a new todo item."""
        todo_id = str(uuid.uuid4())[:8]  # Short unique ID
        
        # Validate priority
        try:
            priority_enum = Priority(priority.lower())
        except ValueError:
            priority_enum = Priority.MEDIUM
        
        # Parse due date
        parsed_due_date = None
        if due_date:
            try:
                if due_date.lower() in ['today', 'tomorrow', 'next week']:
                    if due_date.lower() == 'today':
                        parsed_due_date = datetime.now().date().isoformat()
                    elif due_date.lower() == 'tomorrow':
                        parsed_due_date = (datetime.now() + timedelta(days=1)).date().isoformat()
                    elif due_date.lower() == 'next week':
                        parsed_due_date = (datetime.now() + timedelta(weeks=1)).date().isoformat()
                else:
                    # Try to parse as ISO date format
                    parsed_date = datetime.fromisoformat(due_date).date()
                    parsed_due_date = parsed_date.isoformat()
            except ValueError:
                print(f"Warning: Invalid due date format '{due_date}', ignoring due date")
        
        todo_item = {
            'description': description,
            'status': Status.PENDING.value,
            'priority': priority_enum.value,
            'category': category,
            'created': datetime.now().isoformat(),
            'due_date': parsed_due_date,
            'completed': None,
            'notes': []
        }
        
        if self._save_todo_file(todo_id, todo_item):
            return todo_id
        else:
            raise Exception("Failed to save todo")
    
    def list_todos(self, status_filter: Optional[str] = None, priority_filter: Optional[str] = None,
                   category_filter: Optional[str] = None, show_completed: bool = False) -> List[Dict[str, Any]]:
        """List todos with optional filtering."""
        todos_list = []
        
        # Get all markdown files from all status folders
        for status_folder in ['pending', 'in_progress', 'completed', 'cancelled']:
            folder_path = os.path.join(self.todos_dir, status_folder)
            if not os.path.exists(folder_path):
                continue
                
            for filepath in glob.glob(os.path.join(folder_path, '*.md')):
                todo = self._parse_markdown_file(filepath)
                if not todo:
                    continue
                
                todo_id = os.path.splitext(os.path.basename(filepath))[0]
                
                # Apply filters
                if status_filter and todo.get('status') != status_filter:
                    continue
                if priority_filter and todo.get('priority') != priority_filter:
                    continue
                if category_filter and todo.get('category') != category_filter:
                    continue
                if not show_completed and todo.get('status') == Status.COMPLETED.value:
                    continue
                
                # Add ID to todo for display
                todo_with_id = {'id': todo_id, **todo}
                todos_list.append(todo_with_id)
        
        # Sort by priority (urgent first) then by created date
        priority_order = {Priority.URGENT.value: 0, Priority.HIGH.value: 1, 
                         Priority.MEDIUM.value: 2, Priority.LOW.value: 3}
        
        todos_list.sort(key=lambda x: (priority_order.get(x.get('priority', 'medium'), 4), 
                                      x.get('created', '')))
        
        return todos_list
    
    def update_todo(self, todo_id: str, description: Optional[str] = None, 
                   status: Optional[str] = None, priority: Optional[str] = None,
                   due_date: Optional[str] = None, category: Optional[str] = None) -> bool:
        """Update an existing todo item."""
        # Find the current todo file
        current_todo = self.get_todo(todo_id)
        if not current_todo:
            return False
        
        # Get the old status to potentially move files
        old_status = current_todo.get('status', Status.PENDING.value)
        
        # Update fields
        if description:
            current_todo['description'] = description
        
        if status:
            try:
                status_enum = Status(status.lower())
                current_todo['status'] = status_enum.value
                
                # Set completion time if marking as completed
                if status_enum == Status.COMPLETED:
                    current_todo['completed'] = datetime.now().isoformat()
                elif current_todo.get('completed'):
                    current_todo['completed'] = None  # Clear completion time if unmarking
                    
            except ValueError:
                print(f"Invalid status: {status}")
                return False
        
        if priority:
            try:
                priority_enum = Priority(priority.lower())
                current_todo['priority'] = priority_enum.value
            except ValueError:
                print(f"Invalid priority: {priority}")
                return False
        
        if due_date:
            try:
                if due_date.lower() == 'none':
                    current_todo['due_date'] = None
                else:
                    parsed_date = datetime.fromisoformat(due_date).date()
                    current_todo['due_date'] = parsed_date.isoformat()
            except ValueError:
                print(f"Invalid due date format: {due_date}")
                return False
        
        if category:
            current_todo['category'] = category
        
        # Remove old file if status changed
        new_status = current_todo.get('status', old_status)
        if old_status != new_status:
            old_folder = self.status_folders.get(old_status, 'pending')
            old_filepath = os.path.join(self.todos_dir, old_folder, f"{todo_id}.md")
            if os.path.exists(old_filepath):
                os.remove(old_filepath)
        
        # Save in new location
        return self._save_todo_file(todo_id, current_todo)
    
    def delete_todo(self, todo_id: str) -> bool:
        """Delete a todo item."""
        # Find and remove the file
        for status_folder in self.status_folders.values():
            filepath = os.path.join(self.todos_dir, status_folder, f"{todo_id}.md")
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
        return False
    
    def add_note(self, todo_id: str, note: str) -> bool:
        """Add a note to a todo item."""
        todo = self.get_todo(todo_id)
        if not todo:
            return False
        
        note_entry = {
            'text': note,
            'timestamp': datetime.now().isoformat()
        }
        
        if 'notes' not in todo:
            todo['notes'] = []
        todo['notes'].append(note_entry)
        
        return self._save_todo_file(todo_id, todo)
    
    def get_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific todo by ID."""
        # Search through all status folders
        for status_folder in self.status_folders.values():
            filepath = os.path.join(self.todos_dir, status_folder, f"{todo_id}.md")
            if os.path.exists(filepath):
                todo = self._parse_markdown_file(filepath)
                if todo:
                    todo['id'] = todo_id
                    return todo
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get todo statistics."""
        all_todos = self.list_todos(show_completed=True)
        
        stats = {
            'total': len(all_todos),
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'cancelled': 0,
            'overdue': 0,
            'by_priority': {p.value: 0 for p in Priority},
            'by_category': {}
        }
        
        today = datetime.now().date()
        
        for todo in all_todos:
            status = todo.get('status', Status.PENDING.value)
            priority = todo.get('priority', Priority.MEDIUM.value)
            category = todo.get('category', 'general')
            due_date = todo.get('due_date')
            
            # Count by status
            if status == Status.PENDING.value:
                stats['pending'] += 1
            elif status == Status.IN_PROGRESS.value:
                stats['in_progress'] += 1
            elif status == Status.COMPLETED.value:
                stats['completed'] += 1
            elif status == Status.CANCELLED.value:
                stats['cancelled'] += 1
            
            # Count by priority
            stats['by_priority'][priority] += 1
            
            # Count by category
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Check if overdue
            if due_date and status not in [Status.COMPLETED.value, Status.CANCELLED.value]:
                try:
                    due = datetime.fromisoformat(due_date).date()
                    if due < today:
                        stats['overdue'] += 1
                except ValueError:
                    pass
        
        return stats
    
    def find_todos(self, search_term: str) -> List[Dict[str, Any]]:
        """Search todos by description content."""
        results = []
        search_lower = search_term.lower()
        
        all_todos = self.list_todos(show_completed=True)
        
        for todo in all_todos:
            if (search_lower in todo.get('description', '').lower() or 
                search_lower in todo.get('category', '').lower() or
                any(search_lower in note.get('text', '').lower() 
                    for note in todo.get('notes', []))):
                
                results.append(todo)
        
        return results