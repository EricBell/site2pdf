#!/usr/bin/env python3
"""
CLI interface for the YAML-based Todo Management System.
"""

import click
from datetime import datetime
from typing import Optional
try:
    from .todo_manager import TodoManager, Priority, Status
except ImportError:
    from todo_manager import TodoManager, Priority, Status


def format_priority(priority: str) -> str:
    """Format priority with colors and icons."""
    icons = {
        'urgent': '🚨',
        'high': '🔴', 
        'medium': '🟡',
        'low': '🟢'
    }
    return f"{icons.get(priority, '⚪')} {priority.upper()}"


def format_status(status: str) -> str:
    """Format status with colors and icons."""
    icons = {
        'pending': '⏳',
        'in_progress': '🔄',
        'completed': '✅',
        'cancelled': '❌'
    }
    return f"{icons.get(status, '❓')} {status.replace('_', ' ').title()}"


def format_due_date(due_date: Optional[str]) -> str:
    """Format due date with relative time."""
    if not due_date:
        return ""
    
    try:
        due = datetime.fromisoformat(due_date).date()
        today = datetime.now().date()
        days_diff = (due - today).days
        
        if days_diff < 0:
            return f"🔥 Overdue by {abs(days_diff)} day{'s' if abs(days_diff) > 1 else ''}"
        elif days_diff == 0:
            return "📅 Due today"
        elif days_diff == 1:
            return "📅 Due tomorrow" 
        elif days_diff <= 7:
            return f"📅 Due in {days_diff} day{'s' if days_diff > 1 else ''}"
        else:
            return f"📅 Due {due.strftime('%Y-%m-%d')}"
    except ValueError:
        return f"📅 {due_date}"


@click.group()
def todo():
    """Todo management system for site2pdf project."""
    pass


@todo.command()
@click.argument('description')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']), 
              default='medium', help='Task priority')
@click.option('--due', '-d', help='Due date (YYYY-MM-DD, today, tomorrow, next week)')
@click.option('--category', '-c', default='general', help='Task category')
def add(description: str, priority: str, due: Optional[str], category: str):
    """Add a new todo item."""
    manager = TodoManager()
    
    try:
        todo_id = manager.add_todo(description, priority, due, category)
        click.echo(f"✅ Added todo: {todo_id}")
        click.echo(f"   📝 {description}")
        click.echo(f"   {format_priority(priority)} | 📂 {category}")
        if due:
            click.echo(f"   {format_due_date(due)}")
    except Exception as e:
        click.echo(f"❌ Error adding todo: {e}")


@todo.command()
@click.option('--status', '-s', type=click.Choice(['pending', 'in_progress', 'completed', 'cancelled']),
              help='Filter by status')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']),
              help='Filter by priority')
@click.option('--category', '-c', help='Filter by category')
@click.option('--completed', is_flag=True, help='Show completed todos')
@click.option('--all', 'show_all', is_flag=True, help='Show all todos including completed')
def list(status: Optional[str], priority: Optional[str], category: Optional[str], 
         completed: bool, show_all: bool):
    """List todo items."""
    manager = TodoManager()
    
    show_completed = completed or show_all
    todos = manager.list_todos(status, priority, category, show_completed)
    
    if not todos:
        click.echo("📝 No todos found matching your criteria.")
        return
    
    # Group by status for better display
    status_groups = {}
    for todo in todos:
        status_key = todo['status']
        if status_key not in status_groups:
            status_groups[status_key] = []
        status_groups[status_key].append(todo)
    
    # Display todos grouped by status
    for status_key in ['pending', 'in_progress', 'completed', 'cancelled']:
        if status_key in status_groups:
            todos_in_status = status_groups[status_key]
            click.echo(f"\n{format_status(status_key)} ({len(todos_in_status)} items):")
            click.echo("─" * 50)
            
            for todo in todos_in_status:
                click.echo(f"[{todo['id']}] 📝 {todo['description']}")
                
                details = []
                details.append(format_priority(todo['priority']))
                details.append(f"📂 {todo['category']}")
                
                if todo.get('due_date'):
                    details.append(format_due_date(todo['due_date']))
                
                click.echo(f"         {' | '.join(details)}")
                
                # Show notes if any
                if todo.get('notes'):
                    latest_note = todo['notes'][-1]
                    click.echo(f"         💭 {latest_note['text'][:50]}{'...' if len(latest_note['text']) > 50 else ''}")
                
                click.echo()


@todo.command()
@click.argument('todo_id')
@click.option('--description', '-d', help='Update description')
@click.option('--status', '-s', type=click.Choice(['pending', 'in_progress', 'completed', 'cancelled']),
              help='Update status')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high', 'urgent']),
              help='Update priority')
@click.option('--due', help='Update due date (YYYY-MM-DD or "none" to clear)')
@click.option('--category', '-c', help='Update category')
def update(todo_id: str, description: Optional[str], status: Optional[str], 
           priority: Optional[str], due: Optional[str], category: Optional[str]):
    """Update a todo item."""
    manager = TodoManager()
    
    # Check if todo exists
    todo = manager.get_todo(todo_id)
    if not todo:
        click.echo(f"❌ Todo '{todo_id}' not found.")
        return
    
    success = manager.update_todo(todo_id, description, status, priority, due, category)
    
    if success:
        updated_todo = manager.get_todo(todo_id)
        click.echo(f"✅ Updated todo: {todo_id}")
        click.echo(f"   📝 {updated_todo['description']}")
        click.echo(f"   {format_status(updated_todo['status'])} | {format_priority(updated_todo['priority'])} | 📂 {updated_todo['category']}")
        if updated_todo.get('due_date'):
            click.echo(f"   {format_due_date(updated_todo['due_date'])}")
    else:
        click.echo(f"❌ Failed to update todo: {todo_id}")


@todo.command()
@click.argument('todo_id') 
@click.confirmation_option(prompt='Are you sure you want to delete this todo?')
def delete(todo_id: str):
    """Delete a todo item."""
    manager = TodoManager()
    
    # Show what we're deleting
    todo = manager.get_todo(todo_id)
    if not todo:
        click.echo(f"❌ Todo '{todo_id}' not found.")
        return
    
    success = manager.delete_todo(todo_id)
    
    if success:
        click.echo(f"🗑️  Deleted todo: {todo_id}")
        click.echo(f"   📝 {todo['description']}")
    else:
        click.echo(f"❌ Failed to delete todo: {todo_id}")


@todo.command()
@click.argument('todo_id')
def show(todo_id: str):
    """Show detailed information about a todo."""
    manager = TodoManager()
    
    todo = manager.get_todo(todo_id)
    if not todo:
        click.echo(f"❌ Todo '{todo_id}' not found.")
        return
    
    click.echo(f"📝 Todo: {todo_id}")
    click.echo("═" * 50)
    click.echo(f"Description: {todo['description']}")
    click.echo(f"Status:      {format_status(todo['status'])}")
    click.echo(f"Priority:    {format_priority(todo['priority'])}")
    click.echo(f"Category:    📂 {todo['category']}")
    click.echo(f"Created:     📅 {datetime.fromisoformat(todo['created']).strftime('%Y-%m-%d %H:%M')}")
    
    if todo.get('due_date'):
        click.echo(f"Due Date:    {format_due_date(todo['due_date'])}")
    
    if todo.get('completed'):
        click.echo(f"Completed:   ✅ {datetime.fromisoformat(todo['completed']).strftime('%Y-%m-%d %H:%M')}")
    
    if todo.get('notes'):
        click.echo(f"\n💭 Notes ({len(todo['notes'])}):")
        click.echo("─" * 20)
        for note in todo['notes']:
            timestamp = datetime.fromisoformat(note['timestamp']).strftime('%Y-%m-%d %H:%M')
            click.echo(f"[{timestamp}] {note['text']}")


@todo.command()
@click.argument('todo_id')
@click.argument('note')
def note(todo_id: str, note: str):
    """Add a note to a todo item."""
    manager = TodoManager()
    
    success = manager.add_note(todo_id, note)
    
    if success:
        click.echo(f"💭 Added note to todo: {todo_id}")
        click.echo(f"   {note}")
    else:
        click.echo(f"❌ Todo '{todo_id}' not found.")


@todo.command()
@click.argument('search_term')
def search(search_term: str):
    """Search todos by description, category, or notes."""
    manager = TodoManager()
    
    results = manager.find_todos(search_term)
    
    if not results:
        click.echo(f"🔍 No todos found matching '{search_term}'")
        return
    
    click.echo(f"🔍 Found {len(results)} todo(s) matching '{search_term}':")
    click.echo("═" * 50)
    
    for todo in results:
        click.echo(f"[{todo['id']}] {format_status(todo['status'])} 📝 {todo['description']}")
        click.echo(f"         {format_priority(todo['priority'])} | 📂 {todo['category']}")
        if todo.get('due_date'):
            click.echo(f"         {format_due_date(todo['due_date'])}")
        click.echo()


@todo.command()
@click.argument('todo_id')
@click.confirmation_option(prompt='Mark this todo as completed?')
def done(todo_id: str):
    """Mark a todo as completed (shortcut for update --status completed)."""
    manager = TodoManager()
    
    todo = manager.get_todo(todo_id)
    if not todo:
        click.echo(f"❌ Todo '{todo_id}' not found.")
        return
    
    success = manager.update_todo(todo_id, status='completed')
    
    if success:
        click.echo(f"🎉 Completed todo: {todo_id}")
        click.echo(f"   📝 {todo['description']}")
    else:
        click.echo(f"❌ Failed to complete todo: {todo_id}")


@todo.command()
def stats():
    """Show todo statistics."""
    manager = TodoManager()
    
    stats = manager.get_statistics()
    
    click.echo("📊 Todo Statistics")
    click.echo("═" * 30)
    click.echo(f"Total todos:     {stats['total']}")
    click.echo(f"⏳ Pending:       {stats['pending']}")
    click.echo(f"🔄 In Progress:   {stats['in_progress']}")
    click.echo(f"✅ Completed:     {stats['completed']}")
    click.echo(f"❌ Cancelled:     {stats['cancelled']}")
    
    if stats['overdue'] > 0:
        click.echo(f"🔥 Overdue:       {stats['overdue']}")
    
    if stats['by_priority']:
        click.echo(f"\n📈 By Priority:")
        for priority, count in stats['by_priority'].items():
            if count > 0:
                click.echo(f"   {format_priority(priority)}: {count}")
    
    if stats['by_category']:
        click.echo(f"\n📂 By Category:")
        for category, count in stats['by_category'].items():
            click.echo(f"   {category}: {count}")


if __name__ == '__main__':
    todo()