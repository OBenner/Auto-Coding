# Component: [Component Name]

<!--
INSTRUCTIONS: Replace [Component Name] with the actual component name (e.g., TaskCard, AuthManager, MemoryClient)
This template helps document components/modules/classes following Auto Claude's documentation patterns.
Suitable for: React components, Python classes, TypeScript modules, Python modules
Fill in each section below, removing placeholder comments and sections that don't apply.
-->

[One-sentence description of what this component does]

## Overview

<!--
INSTRUCTIONS: Provide a brief overview of the component's purpose and use cases.
-->

**Type:** [React Component / Python Class / TypeScript Module / Python Module]
**Location:** `[relative/path/to/file.tsx or .py]`
**Category:** [UI Component / Service / Utility / Integration / Data Model]
**Status:** [Stable / Experimental / Deprecated]

### Purpose

[Explain what this component accomplishes and when it should be used]

### Key Features

- **Feature 1:** [Description]
- **Feature 2:** [Description]
- **Feature 3:** [Description]

### Use Cases

- **Use Case 1:** [When to use this component]
- **Use Case 2:** [Another scenario where this is helpful]
- **Use Case 3:** [Additional use case]

---

## Installation / Import

<!--
INSTRUCTIONS: Show how to import or instantiate this component.
-->

### React Component Import

```typescript
import { ComponentName } from '@/components/path/to/component';
// or
import ComponentName from '@/components/path/to/component';
```

### Python Module Import

```python
from apps.backend.module.path import ComponentName
# or
from module.path import ComponentName
```

### Dependencies

**Required:**
- `[package-name]` - [Why it's needed]
- `[another-package]` - [Why it's needed]

**Optional:**
- `[optional-package]` - [What it enables]

---

## API Reference

<!--
INSTRUCTIONS: Document the component's public API (props for React, parameters for Python).
-->

### Props (React) / Parameters (Python)

#### Required Props/Parameters

| Prop/Parameter | Type | Description | Example |
|----------------|------|-------------|---------|
| `propName` | `string` | [What this prop controls] | `"example-value"` |
| `propName` | `number` | [What this prop controls] | `42` |
| `propName` | `(arg: string) => void` | [Callback description] | `(val) => console.log(val)` |

#### Optional Props/Parameters

| Prop/Parameter | Type | Default | Description | Example |
|----------------|------|---------|-------------|---------|
| `optionalProp` | `boolean` | `false` | [What this prop controls] | `true` |
| `optionalProp` | `string \| null` | `null` | [What this prop controls] | `"custom-value"` |
| `optionalProp` | `number` | `10` | [What this prop controls] | `25` |
| `className` | `string` | `""` | Additional CSS classes | `"custom-class"` |
| `style` | `CSSProperties` | `{}` | Inline styles | `{{ margin: 10 }}` |

### Events / Callbacks

<!--
INSTRUCTIONS: Document event handlers and callbacks.
For React: onClick, onChange, onSubmit, etc.
For Python: Callback functions passed as arguments.
-->

| Event/Callback | Signature | Description | When Triggered |
|----------------|-----------|-------------|----------------|
| `onClick` | `(event: MouseEvent) => void` | Click handler | When component is clicked |
| `onChange` | `(value: T) => void` | Value change handler | When value changes |
| `onError` | `(error: Error) => void` | Error handler | When an error occurs |

### Methods (Class Components / Python Classes)

<!--
INSTRUCTIONS: Document public methods.
Remove this section for functional components without exposed methods.
-->

#### `methodName(param1: Type, param2: Type): ReturnType`

**Description:** [What this method does]

**Parameters:**
- `param1` (Type) - [Description]
- `param2` (Type) - [Description]

**Returns:** [Description of return value]

**Throws:** [Exceptions/Errors that can be thrown]

**Example:**
```typescript
const result = component.methodName(value1, value2);
```

#### `anotherMethod(): Promise<ResultType>`

**Description:** [What this async method does]

**Returns:** Promise that resolves to [description]

**Example:**
```typescript
const result = await component.anotherMethod();
```

---

## Type Definitions

<!--
INSTRUCTIONS: Document TypeScript interfaces, types, or Python type hints used.
-->

### TypeScript Types

```typescript
interface ComponentNameProps {
  // Required props
  requiredProp: string;
  requiredProp2: number;

  // Optional props
  optionalProp?: boolean;
  optionalProp2?: string | null;

  // Callbacks
  onEvent?: (data: EventData) => void;
  onError?: (error: Error) => void;

  // React-specific
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

interface EventData {
  id: string;
  timestamp: number;
  payload: Record<string, unknown>;
}

type ComponentVariant = 'primary' | 'secondary' | 'danger';
type ComponentSize = 'small' | 'medium' | 'large';
```

### Python Type Hints

```python
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

@dataclass
class ComponentConfig:
    """Configuration for ComponentName"""
    required_field: str
    optional_field: Optional[int] = None
    callback: Optional[Callable[[str], None]] = None

class ComponentName:
    def __init__(
        self,
        param1: str,
        param2: int,
        optional_param: Optional[bool] = False,
        callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> None:
        """
        Initialize ComponentName.

        Args:
            param1: Description of param1
            param2: Description of param2
            optional_param: Description of optional parameter
            callback: Optional callback function
        """
        pass

    def method(self, arg: str) -> Dict[str, Any]:
        """
        Method description.

        Args:
            arg: Description

        Returns:
            Dictionary containing result data
        """
        pass
```

---

## Usage Examples

<!--
INSTRUCTIONS: Provide practical examples from simple to advanced use cases.
-->

### Basic Usage

#### React Component

```typescript
import { ComponentName } from '@/components/path';

function ParentComponent() {
  return (
    <ComponentName
      requiredProp="value"
      requiredProp2={42}
    />
  );
}
```

#### Python Class

```python
from apps.backend.module.path import ComponentName

# Initialize component
component = ComponentName(
    param1="value",
    param2=42
)

# Use component
result = component.method("argument")
print(result)
```

### Advanced Usage

#### React with State Management

```typescript
import { useState, useCallback } from 'react';
import { ComponentName } from '@/components/path';

function AdvancedParentComponent() {
  const [state, setState] = useState<StateType>(initialState);

  const handleEvent = useCallback((data: EventData) => {
    // Handle event
    setState(prevState => ({
      ...prevState,
      ...data
    }));
  }, []);

  const handleError = useCallback((error: Error) => {
    console.error('Component error:', error);
    // Error handling logic
  }, []);

  return (
    <ComponentName
      requiredProp="value"
      requiredProp2={42}
      optionalProp={true}
      onEvent={handleEvent}
      onError={handleError}
      className="custom-styling"
    />
  );
}
```

#### Python with Context Manager

```python
from apps.backend.module.path import ComponentName
from typing import Optional

class ServiceWithComponent:
    def __init__(self, config: dict):
        self.component = ComponentName(
            param1=config['param1'],
            param2=config.get('param2', 10),
            optional_param=True,
            callback=self._handle_callback
        )

    def _handle_callback(self, data: dict) -> None:
        """Handle component callback"""
        print(f"Received data: {data}")

    async def process(self, input_data: str) -> Optional[dict]:
        """Process data using component"""
        try:
            result = self.component.method(input_data)
            return result
        except Exception as e:
            print(f"Error processing: {e}")
            return None

# Usage
service = ServiceWithComponent(config={'param1': 'value', 'param2': 42})
result = await service.process("input")
```

### Integration Example

<!--
INSTRUCTIONS: Show how this component integrates with other parts of the system.
-->

#### React with Context and Hooks

```typescript
import { ComponentName } from '@/components/path';
import { useAppContext } from '@/contexts/AppContext';
import { useQuery } from '@tanstack/react-query';

function IntegratedComponent() {
  const { user, settings } = useAppContext();

  const { data, isLoading, error } = useQuery({
    queryKey: ['data-key'],
    queryFn: fetchData
  });

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <ComponentName
      requiredProp={data.value}
      requiredProp2={settings.count}
      optionalProp={user.preferences.enabled}
      onEvent={(event) => {
        // Handle event with context
        console.log('Event from:', user.id, event);
      }}
    />
  );
}
```

#### Python with Dependency Injection

```python
from apps.backend.module.path import ComponentName
from apps.backend.core.client import create_client
from typing import Optional

class SystemIntegration:
    """Integration layer using ComponentName"""

    def __init__(
        self,
        project_dir: str,
        component: Optional[ComponentName] = None
    ):
        self.project_dir = project_dir
        self.component = component or ComponentName(
            param1=self._load_config(),
            param2=42
        )
        self.client = create_client(project_dir)

    def _load_config(self) -> str:
        """Load configuration"""
        # Configuration loading logic
        return "config-value"

    def execute(self, task: str) -> dict:
        """Execute task using component"""
        result = self.component.method(task)

        # Integrate with other systems
        self.client.update_status(result)

        return result
```

---

## Styling (React Components)

<!--
INSTRUCTIONS: For UI components, document styling approach.
Remove this section for non-UI components.
-->

### Default Styles

The component uses Tailwind CSS classes by default:

```typescript
<ComponentName
  className="bg-white rounded-lg shadow-md p-4"
/>
```

### Customization

#### Tailwind CSS Classes

```typescript
<ComponentName
  className="
    bg-gradient-to-r from-blue-500 to-purple-500
    text-white font-bold
    rounded-xl shadow-lg
    hover:shadow-2xl transition-shadow
  "
/>
```

#### CSS Modules

```typescript
import styles from './CustomStyles.module.css';

<ComponentName className={styles.customComponent} />
```

**CustomStyles.module.css:**
```css
.customComponent {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
}

.customComponent:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15);
}
```

#### Inline Styles

```typescript
<ComponentName
  style={{
    backgroundColor: '#f0f0f0',
    border: '1px solid #ddd',
    borderRadius: '8px',
    padding: '16px'
  }}
/>
```

### Theme Integration

```typescript
import { useTheme } from '@/contexts/ThemeContext';

function ThemedComponent() {
  const { theme } = useTheme();

  return (
    <ComponentName
      className={`
        ${theme === 'dark' ? 'bg-gray-800 text-white' : 'bg-white text-gray-900'}
        rounded-lg p-4
      `}
    />
  );
}
```

---

## Accessibility

<!--
INSTRUCTIONS: For UI components, document accessibility features.
Remove this section for non-UI components.
-->

### ARIA Attributes

The component implements the following ARIA attributes:

- `role="[role]"` - [Description]
- `aria-label="[label]"` - [Description]
- `aria-describedby="[id]"` - [Description]
- `aria-live="[polite/assertive]"` - [Description]

### Keyboard Navigation

| Key | Action |
|-----|--------|
| `Enter` / `Space` | [Action] |
| `Tab` | [Action] |
| `Escape` | [Action] |
| `Arrow Keys` | [Action] |

### Screen Reader Support

The component provides descriptive labels for screen readers:

```typescript
<ComponentName
  aria-label="Descriptive label for screen readers"
  aria-describedby="help-text-id"
/>
```

### Focus Management

The component manages focus appropriately:
- Focus indicator visible for keyboard navigation
- Focus trapped within modal dialogs
- Focus restored after closing overlays

---

## Testing

<!--
INSTRUCTIONS: Provide testing examples and strategies.
-->

### Unit Tests

#### React Component Tests (Jest + React Testing Library)

**Location:** `tests/components/ComponentName.test.tsx`

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ComponentName } from '@/components/path';

describe('ComponentName', () => {
  it('renders with required props', () => {
    render(
      <ComponentName
        requiredProp="test-value"
        requiredProp2={42}
      />
    );

    expect(screen.getByText('test-value')).toBeInTheDocument();
  });

  it('handles events correctly', async () => {
    const mockHandler = jest.fn();

    render(
      <ComponentName
        requiredProp="test"
        requiredProp2={42}
        onEvent={mockHandler}
      />
    );

    const element = screen.getByRole('button');
    fireEvent.click(element);

    await waitFor(() => {
      expect(mockHandler).toHaveBeenCalledTimes(1);
    });
  });

  it('renders with optional props', () => {
    render(
      <ComponentName
        requiredProp="test"
        requiredProp2={42}
        optionalProp={true}
      />
    );

    expect(screen.getByTestId('optional-feature')).toBeInTheDocument();
  });

  it('handles errors gracefully', async () => {
    const mockErrorHandler = jest.fn();

    render(
      <ComponentName
        requiredProp="test"
        requiredProp2={42}
        onError={mockErrorHandler}
      />
    );

    // Trigger error condition
    fireEvent.click(screen.getByRole('button'));

    await waitFor(() => {
      expect(mockErrorHandler).toHaveBeenCalled();
    });
  });
});
```

#### Python Class Tests (pytest)

**Location:** `tests/test_component_name.py`

```python
import pytest
from apps.backend.module.path import ComponentName

class TestComponentName:
    """Test suite for ComponentName"""

    def test_initialization(self):
        """Test component initialization"""
        component = ComponentName(
            param1="test-value",
            param2=42
        )

        assert component.param1 == "test-value"
        assert component.param2 == 42

    def test_method_success(self):
        """Test successful method execution"""
        component = ComponentName(param1="test", param2=42)

        result = component.method("input")

        assert result is not None
        assert result["status"] == "success"

    def test_method_with_callback(self):
        """Test method with callback"""
        callback_called = []

        def callback(data):
            callback_called.append(data)

        component = ComponentName(
            param1="test",
            param2=42,
            callback=callback
        )

        component.method("input")

        assert len(callback_called) == 1
        assert callback_called[0]["processed"] is True

    def test_error_handling(self):
        """Test error handling"""
        component = ComponentName(param1="", param2=0)

        with pytest.raises(ValueError, match="Invalid parameters"):
            component.method("invalid-input")

    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method"""
        component = ComponentName(param1="test", param2=42)

        result = await component.async_method("input")

        assert result["completed"] is True
```

### Integration Tests

```bash
# React component integration tests
npm run test:integration -- ComponentName

# Python class integration tests
pytest tests/integration/test_component_name.py -v

# Run with coverage
pytest tests/integration/test_component_name.py --cov=apps/backend.module.path
```

### Testing Checklist

- [ ] Component renders with required props
- [ ] Optional props work as expected
- [ ] Event handlers are called correctly
- [ ] Error handling works properly
- [ ] Edge cases are handled
- [ ] Accessibility features work
- [ ] Performance is acceptable
- [ ] Integration with other components works

---

## Performance Considerations

<!--
INSTRUCTIONS: Document performance characteristics and optimization tips.
-->

### Optimization Tips

1. **[React] Memoization** - Use `React.memo()` to prevent unnecessary re-renders
   ```typescript
   export const ComponentName = React.memo<ComponentNameProps>(({ ...props }) => {
     // Component implementation
   });
   ```

2. **[React] useCallback for event handlers** - Prevent function recreation
   ```typescript
   const handleEvent = useCallback((data) => {
     // Handler logic
   }, [dependencies]);
   ```

3. **[Python] Caching** - Cache expensive computations
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=128)
   def expensive_operation(self, input: str) -> dict:
       # Expensive computation
       pass
   ```

4. **[Python] Async operations** - Use async for I/O-bound tasks
   ```python
   async def async_operation(self) -> dict:
       result = await fetch_data()
       return result
   ```

### Performance Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| Initial render time | < [X]ms | [Context] |
| Re-render time | < [Y]ms | [Context] |
| Memory usage | < [Z]MB | [Context] |
| Method execution | < [W]ms | [Context] |

---

## Error Handling

<!--
INSTRUCTIONS: Document error handling strategy and common errors.
-->

### Error Types

#### React Component Errors

```typescript
try {
  // Component logic
} catch (error) {
  if (error instanceof ValidationError) {
    // Handle validation error
  } else if (error instanceof NetworkError) {
    // Handle network error
  } else {
    // Handle unexpected error
  }
}
```

#### Python Class Errors

```python
class ComponentError(Exception):
    """Base exception for ComponentName"""
    pass

class ValidationError(ComponentError):
    """Raised when validation fails"""
    pass

class ProcessingError(ComponentError):
    """Raised when processing fails"""
    pass

# Usage
try:
    result = component.method("input")
except ValidationError as e:
    logger.error(f"Validation failed: {e}")
    raise
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    # Handle or re-raise
```

### Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `TypeError: [message]` | Missing required prop/param | Ensure all required props are provided |
| `ValidationError: [message]` | Invalid input value | Check input constraints |
| `NetworkError: [message]` | API call failed | Retry with exponential backoff |
| `StateError: [message]` | Invalid component state | Reset component state |

---

## Migration Guide

<!--
INSTRUCTIONS: For deprecated components or breaking changes.
Remove if not applicable.
-->

### Migrating from v1.x to v2.x

**Breaking Changes:**
- Prop `oldProp` renamed to `newProp`
- Method `oldMethod()` removed, use `newMethod()` instead
- Event `onOldEvent` replaced with `onNewEvent`

**Migration Steps:**

1. **Update prop names:**
   ```diff
   <ComponentName
   -  oldProp="value"
   +  newProp="value"
   />
   ```

2. **Replace method calls:**
   ```diff
   -component.oldMethod();
   +component.newMethod();
   ```

3. **Update event handlers:**
   ```diff
   <ComponentName
   -  onOldEvent={handleEvent}
   +  onNewEvent={handleEvent}
   />
   ```

---

## Related Components/Modules

<!--
INSTRUCTIONS: Link to related components and documentation.
-->

### Similar Components

- [RelatedComponent1](./related-component-1.md) - [Brief description]
- [RelatedComponent2](./related-component-2.md) - [Brief description]

### Dependencies

- [DependencyModule](./dependency-module.md) - [What it provides]

### Used By

- [ParentComponent1](./parent-component-1.md) - [How it uses this]
- [ParentComponent2](./parent-component-2.md) - [How it uses this]

---

## Best Practices

<!--
INSTRUCTIONS: Document recommended usage patterns and anti-patterns.
-->

### DO

✅ **Use descriptive prop names**
```typescript
<ComponentName requiredProp="clear-description" />
```

✅ **Handle errors gracefully**
```typescript
<ComponentName
  onError={(error) => {
    console.error('Component error:', error);
    showNotification('An error occurred');
  }}
/>
```

✅ **Provide proper types**
```typescript
const props: ComponentNameProps = {
  requiredProp: "value",
  requiredProp2: 42
};
```

✅ **Use memoization for expensive operations**
```typescript
const memoizedValue = useMemo(() => expensiveOperation(), [dependencies]);
```

### DON'T

❌ **Don't ignore required props**
```typescript
// WRONG - Missing required props
<ComponentName />
```

❌ **Don't mutate props directly**
```typescript
// WRONG
props.value = newValue;

// RIGHT
const newValue = calculateNewValue(props.value);
```

❌ **Don't create inline callbacks without memoization**
```typescript
// WRONG - Creates new function on every render
<ComponentName onEvent={(data) => handleData(data)} />

// RIGHT - Memoized callback
const handleEvent = useCallback((data) => handleData(data), []);
<ComponentName onEvent={handleEvent} />
```

---

## Troubleshooting

<!--
INSTRUCTIONS: Document common issues and debugging tips.
-->

### Common Issues

#### Issue: Component not rendering

**Cause:** Missing required props or incorrect prop types

**Solution:**
1. Verify all required props are provided
2. Check prop types match expected types
3. Ensure parent component is rendering
4. Check browser console for errors

#### Issue: Event handlers not firing

**Cause:** Event handler not properly bound or missing

**Solution:**
1. Verify event handler is passed as prop
2. Check event handler signature matches expected type
3. Ensure event target element is interactive
4. Use browser DevTools to inspect event listeners

#### Issue: Performance degradation

**Cause:** Unnecessary re-renders or expensive operations

**Solution:**
1. Use React DevTools Profiler to identify bottlenecks
2. Implement memoization for expensive computations
3. Use `React.memo()` to prevent unnecessary re-renders
4. Check for memory leaks

### Debug Mode

Enable detailed logging:

```typescript
// React component debug mode
<ComponentName
  debug={true}
  requiredProp="value"
  requiredProp2={42}
/>
```

```python
# Python class debug mode
import logging

logging.basicConfig(level=logging.DEBUG)
component = ComponentName(param1="value", param2=42)
component.set_debug(True)
```

---

## Changelog

<!--
INSTRUCTIONS: Document changes to this component.
-->

### Version 2.1.0 - 2024-01-15

**Added:**
- New optional prop `optionalProp3` for enhanced functionality
- Support for async operations

**Changed:**
- Improved error messages
- Updated default values for better UX

**Fixed:**
- Memory leak in event listener cleanup
- Race condition in async operations

### Version 2.0.0 - 2024-01-01

**Breaking Changes:**
- Renamed `oldProp` to `newProp`
- Removed deprecated method `oldMethod()`

**Added:**
- TypeScript type definitions
- Comprehensive test coverage

**Changed:**
- Complete rewrite using modern patterns
- Improved performance by 50%

### Version 1.0.0 - 2023-12-01

**Initial Release:**
- Core component functionality
- Basic prop support
- Event handling

---

**Document Information:**
- **Component Version:** [X.Y.Z]
- **Last Updated:** [YYYY-MM-DD]
- **Maintainer:** [Team/Person responsible]
- **Status:** [Stable / Experimental / Deprecated]
- **Compatibility:** [React 18+ / Python 3.12+ / etc.]
