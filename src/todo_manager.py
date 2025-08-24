#!/usr/bin/env python3
"""
YAML-based Todo Management System for site2pdf

Provides functionality to manage tasks with priorities, due dates, and status tracking.
"""

import os
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


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
    """Manages todos stored in YAML format."""
    
    def __init__(self, todos_file: str = "todos.yaml"):
        self.todos_file = todos_file
        self.todos = self._load_todos()
    
    def _load_todos(self) -> Dict[str, Any]:
        """Load todos from YAML file."""
        if not os.path.exists(self.todos_file):
            return {
                'metadata': {
                    'created': datetime.now().isoformat(),
                    'last_modified': datetime.now().isoformat(),
                    'version': '1.0'
                },
                'todos': {}
            }
        
        try:
            with open(self.todos_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {'metadata': {}, 'todos': {}}
        except Exception as e:
            print(f"Error loading todos: {e}")
            return {'metadata': {}, 'todos': {}}
    
    def _save_todos(self) -> bool:
        """Save todos to YAML file."""
        try:
            self.todos['metadata']['last_modified'] = datetime.now().isoformat()
            with open(self.todos_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.todos, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"Error saving todos: {e}")
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
        
        self.todos['todos'][todo_id] = todo_item
        
        if self._save_todos():
            return todo_id
        else:
            raise Exception("Failed to save todo")
    
    def list_todos(self, status_filter: Optional[str] = None, priority_filter: Optional[str] = None,
                   category_filter: Optional[str] = None, show_completed: bool = False) -> List[Dict[str, Any]]:
        """List todos with optional filtering."""
        todos_list = []
        
        for todo_id, todo in self.todos['todos'].items():
            # Apply filters
            if status_filter and todo['status'] != status_filter:
                continue
            if priority_filter and todo['priority'] != priority_filter:
                continue
            if category_filter and todo['category'] != category_filter:
                continue
            if not show_completed and todo['status'] == Status.COMPLETED.value:
                continue
            
            # Add ID to todo for display
            todo_with_id = {'id': todo_id, **todo}
            todos_list.append(todo_with_id)
        
        # Sort by priority (urgent first) then by created date
        priority_order = {Priority.URGENT.value: 0, Priority.HIGH.value: 1, 
                         Priority.MEDIUM.value: 2, Priority.LOW.value: 3}
        
        todos_list.sort(key=lambda x: (priority_order.get(x['priority'], 4), x['created']))
        
        return todos_list
    
    def update_todo(self, todo_id: str, description: Optional[str] = None, 
                   status: Optional[str] = None, priority: Optional[str] = None,
                   due_date: Optional[str] = None, category: Optional[str] = None) -> bool:
        """Update an existing todo item."""
        if todo_id not in self.todos['todos']:
            return False
        
        todo = self.todos['todos'][todo_id]
        
        if description:
            todo['description'] = description
        
        if status:
            try:
                status_enum = Status(status.lower())
                todo['status'] = status_enum.value
                
                # Set completion time if marking as completed
                if status_enum == Status.COMPLETED:
                    todo['completed'] = datetime.now().isoformat()
                elif todo.get('completed'):
                    todo['completed'] = None  # Clear completion time if unmarking
                    
            except ValueError:
                print(f"Invalid status: {status}")
                return False
        
        if priority:
            try:
                priority_enum = Priority(priority.lower())
                todo['priority'] = priority_enum.value
            except ValueError:
                print(f"Invalid priority: {priority}")
                return False
        
        if due_date:
            try:
                if due_date.lower() == 'none':
                    todo['due_date'] = None
                else:
                    parsed_date = datetime.fromisoformat(due_date).date()
                    todo['due_date'] = parsed_date.isoformat()
            except ValueError:
                print(f"Invalid due date format: {due_date}")
                return False
        
        if category:
            todo['category'] = category
        
        return self._save_todos()
    
    def delete_todo(self, todo_id: str) -> bool:
        """Delete a todo item."""
        if todo_id not in self.todos['todos']:
            return False
        
        del self.todos['todos'][todo_id]
        return self._save_todos()
    
    def add_note(self, todo_id: str, note: str) -> bool:
        """Add a note to a todo item."""
        if todo_id not in self.todos['todos']:
            return False
        
        note_entry = {
            'text': note,
            'timestamp': datetime.now().isoformat()
        }
        
        self.todos['todos'][todo_id]['notes'].append(note_entry)
        return self._save_todos()
    
    def get_todo(self, todo_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific todo by ID."""
        if todo_id not in self.todos['todos']:
            return None
        
        todo = self.todos['todos'][todo_id].copy()
        todo['id'] = todo_id
        return todo
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get todo statistics."""
        total = len(self.todos['todos'])
        
        stats = {
            'total': total,
            'pending': 0,
            'in_progress': 0,
            'completed': 0,
            'cancelled': 0,
            'overdue': 0,
            'by_priority': {p.value: 0 for p in Priority},
            'by_category': {}
        }
        
        today = datetime.now().date()
        
        for todo in self.todos['todos'].values():
            status = todo['status']
            priority = todo['priority']
            category = todo['category']
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
        
        for todo_id, todo in self.todos['todos'].items():
            if (search_lower in todo['description'].lower() or 
                search_lower in todo['category'].lower() or
                any(search_lower in note['text'].lower() for note in todo.get('notes', []))):
                
                todo_with_id = {'id': todo_id, **todo}
                results.append(todo_with_id)
        
        return results