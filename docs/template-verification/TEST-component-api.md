# Component API: TaskCard

**Type**: React Component (Presentational)
**Location**: `src/components/TaskCard.tsx`
**Category**: UI Component
**Status**: Stable

## Overview

`TaskCard` is a reusable card component that displays task/spec information in a visually organized format. It shows task status, metadata, progress indicators, and action buttons.

## Purpose

Provide a consistent card-based interface for displaying tasks across the application. Used in task lists, dashboards, and spec management views.

## Key Features

- **Status Badges**: Color-coded status indicators
- **Progress Bar**: Visual progress tracking
- **Action Menu**: Context menu for task operations
- **Responsive**: Adapts to different screen sizes
- **Accessible**: Full keyboard navigation and ARIA support

## Use Cases

- Display tasks in a grid or list layout
- Show spec status in dashboard
- Provide quick actions for task management

## Installation/Import

### React Component

```typescript
import { TaskCard } from '@/components/TaskCard';
```

### CSS Styles

```typescript
import '@/components/TaskCard.css';
```

## API Reference

### Props (React)

#### Required Props

| Prop | Type | Description |
|------|------|-------------|
| `taskId` | `string` | Unique task identifier |
| `title` | `string` | Task title/name |
| `status` | `TaskStatus` | Current task status |

#### Optional Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `description` | `string` | `undefined` | Task description |
| `progress` | `number` | `0` | Progress percentage (0-100) |
| `tags` | `string[]` | `[]` | Array of tag labels |
| `createdAt` | `Date \| string` | `undefined` | Creation timestamp |
| `onAction` | `(action: string, taskId: string) => void` | `undefined` | Action handler |
| `className` | `string` | `''` | Additional CSS classes |
| `variant` | `'default' \| 'compact' \| 'detailed'` | `'default'` | Card variant |

### Events/Callbacks

| Event | Parameters | Description |
|-------|------------|-------------|
| `onAction` | `action: string, taskId: string` | Triggered when action button clicked |
| `onClick` | `event: MouseEvent, taskId: string` | Triggered when card clicked |
| `onStatusChange` | `newStatus: TaskStatus, taskId: string` | Triggered when status changes |

### Type Definitions

#### TypeScript Interfaces

```typescript
// Task status enum
type TaskStatus =
  | 'pending'
  | 'in_progress'
  | 'completed'
  | 'failed'
  | 'cancelled';

// TaskCard props interface
interface TaskCardProps {
  taskId: string;
  title: string;
  status: TaskStatus;
  description?: string;
  progress?: number;
  tags?: string[];
  createdAt?: Date | string;
  onAction?: (action: string, taskId: string) => void;
  onClick?: (event: React.MouseEvent, taskId: string) => void;
  onStatusChange?: (newStatus: TaskStatus, taskId: string) => void;
  className?: string;
  variant?: 'default' | 'compact' | 'detailed';
}

// Action types
type TaskAction = 'view' | 'edit' | 'delete' | 'duplicate' | 'archive';
```

## Usage

### Basic Example

```typescript
import { TaskCard } from '@/components/TaskCard';

function TaskList() {
  const handleAction = (action: string, taskId: string) => {
    console.log(`Action ${action} on task ${taskId}`);
  };

  return (
    <TaskCard
      taskId="001"
      title="Add Dark Mode"
      status="in_progress"
      description="Implement dark mode support across the application"
      progress={65}
      tags={['ui', 'feature']}
      onAction={handleAction}
    />
  );
}
```

### Advanced Example

```typescript
import { TaskCard } from '@/components/TaskCard';
import { useState } from 'react';

function TaskDashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);

  const handleStatusChange = (newStatus: TaskStatus, taskId: string) => {
    setTasks(prev =>
      prev.map(task =>
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    );
  };

  return (
    <div className="task-grid">
      {tasks.map(task => (
        <TaskCard
          key={task.id}
          taskId={task.id}
          title={task.title}
          status={task.status}
          description={task.description}
          progress={task.progress}
          tags={task.tags}
          createdAt={task.createdAt}
          variant="detailed"
          onAction={handleAction}
          onStatusChange={handleStatusChange}
        />
      ))}
    </div>
  );
}
```

### Integration Example

```typescript
// Using with React Query
import { useQuery } from '@tanstack/react-query';
import { TaskCard } from '@/components/TaskCard';

function TaskListWithData() {
  const { data: tasks } = useQuery({
    queryKey: ['tasks'],
    queryFn: fetchTasks
  });

  return (
    <div>
      {tasks?.map(task => (
        <TaskCard
          key={task.id}
          taskId={task.id}
          title={task.title}
          status={task.status}
          progress={task.progress}
        />
      ))}
    </div>
  );
}
```

## Styling

### Tailwind Classes

The component uses Tailwind CSS for styling:

```typescript
<TaskCard
  className="shadow-lg hover:shadow-xl transition-shadow"
  // Other props...
/>
```

### CSS Variables

Customize appearance using CSS variables:

```css
:root {
  --task-card-border: #e5e7eb;
  --task-card-bg: #ffffff;
  --task-card-hover-bg: #f9fafb;
}

[data-theme='dark'] {
  --task-card-border: #374151;
  --task-card-bg: #1f2937;
  --task-card-hover-bg: #111827;
}
```

### Custom Styling

```css
.task-card-custom {
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.task-card-custom:hover {
  transform: translateY(-2px);
  transition: transform 0.2s ease;
}
```

## Accessibility

### ARIA Attributes

- `role="article"` - Card is an article
- `aria-label` - Descriptive label for screen readers
- `aria-describedby` - Links description to card
- `tabindex="0"` - Keyboard navigation support

### Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | Focus next card |
| `Shift + Tab` | Focus previous card |
| `Enter` | Open card details |
| `Space` | Select card |
| `Escape` | Close action menu |

### Screen Reader Support

```typescript
<TaskCard
  taskId="001"
  title="Add Dark Mode"
  status="in_progress"
  aria-label="Task: Add Dark Mode, Status: In Progress, 65% complete"
/>
```

## Testing

### Unit Tests

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { TaskCard } from './TaskCard';

describe('TaskCard', () => {
  it('renders task title and status', () => {
    render(
      <TaskCard
        taskId="001"
        title="Test Task"
        status="in_progress"
      />
    );

    expect(screen.getByText('Test Task')).toBeInTheDocument();
    expect(screen.getByText('In Progress')).toBeInTheDocument();
  });

  it('calls onAction when action button clicked', () => {
    const handleAction = jest.fn();
    render(
      <TaskCard
        taskId="001"
        title="Test Task"
        status="pending"
        onAction={handleAction}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: /view/i }));
    expect(handleAction).toHaveBeenCalledWith('view', '001');
  });

  it('displays progress bar when progress prop provided', () => {
    render(
      <TaskCard
        taskId="001"
        title="Test Task"
        status="in_progress"
        progress={50}
      />
    );

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
  });
});
```

### Integration Tests

```typescript
import { render, screen, waitFor } from '@testing-library/react';
import { TaskCard } from './TaskCard';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

describe('TaskCard Integration', () => {
  it('updates status when API call succeeds', async () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <TaskCard
          taskId="001"
          title="Test Task"
          status="pending"
          onStatusChange={mockStatusChange}
        />
      </QueryClientProvider>
    );

    // Trigger status change
    fireEvent.click(screen.getByRole('button', { name: /complete/i }));

    await waitFor(() => {
      expect(screen.getByText('Completed')).toBeInTheDocument();
    });
  });
});
```

## Performance

### Optimization Tips

1. **Memoization**: Use `React.memo` for list rendering
   ```typescript
   export const TaskCard = React.memo(TaskCardComponent);
   ```

2. **Virtualization**: Use `react-window` for large lists
   ```typescript
   import { FixedSizeList } from 'react-window';
   ```

3. **Lazy Loading**: Load images lazily
   ```typescript
   <img loading="lazy" src={thumbnailUrl} alt="" />
   ```

## Error Handling

### Error States

```typescript
interface TaskCardProps {
  // ... other props
  error?: string;
  isLoading?: boolean;
}

function TaskCard({ error, isLoading, ...props }: TaskCardProps) {
  if (isLoading) return <TaskCardSkeleton />;
  if (error) return <TaskCardError error={error} />;

  return <div>{/* Normal card */}</div>;
}
```

## Best Practices

**DO:**
- Use semantic HTML (`<article>`, `<header>`, `<footer>`)
- Provide descriptive `aria-label` for screen readers
- Handle loading and error states
- Use memoization for list rendering

**DON'T:**
- Hardcode colors (use CSS variables or Tailwind)
- Omit keyboard navigation support
- Forget to handle edge cases (missing data)
- Use inline styles (use Tailwind or CSS classes)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Card not rendering | Check required props are provided |
| Actions not triggering | Verify `onAction` callback is defined |
| Styling conflicts | Check CSS specificity, use `!important` sparingly |
| Accessibility warnings | Add missing ARIA attributes |

## Related Components

- `TaskList` - Container for multiple TaskCards
- `TaskDetail` - Detailed task view
- `StatusBadge` - Reusable status badge component

## Changelog

- **v2.1.0** (2026-02-05): Added `variant` prop for different card styles
- **v2.0.0** (2026-01-15): Migrated to TypeScript, added accessibility features
- **v1.0.0** (2025-12-01): Initial release
