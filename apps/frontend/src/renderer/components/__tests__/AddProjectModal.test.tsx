/**
 * @vitest-environment jsdom
 */
/**
 * Unit tests for AddProjectModal component validation logic
 * Tests form validation, state management, and error handling
 *
 * Key behaviors tested:
 * - Form validation (name required, location required)
 * - Step transitions (choose → create-form)
 * - Error state management
 * - State reset when modal opens
 */
import { describe, it, expect } from 'vitest';

type ModalStep = 'choose' | 'create-form';

/**
 * Mock translation function that returns the key for testing
 */
function mockT(key: string): string {
  const translations: Record<string, string> = {
    'addProject.nameRequired': 'Project name is required',
    'addProject.locationRequired': 'Project location is required',
    'addProject.failedToCreate': 'Failed to create project',
    'addProject.failedToOpen': 'Failed to open project',
  };
  return translations[key] || key;
}

/**
 * Simulates the form validation logic from AddProjectModal
 * Extracted for testing without rendering the full component
 */
function validateProjectCreation(params: {
  projectName: string;
  projectLocation: string;
  t: (key: string) => string;
}): { isValid: boolean; error: string | null } {
  const { projectName, projectLocation, t } = params;

  if (!projectName.trim()) {
    return {
      isValid: false,
      error: t('addProject.nameRequired'),
    };
  }

  if (!projectLocation.trim()) {
    return {
      isValid: false,
      error: t('addProject.locationRequired'),
    };
  }

  return {
    isValid: true,
    error: null,
  };
}

/**
 * Simulates step transition logic
 */
function getNextStep(currentStep: ModalStep, action: 'create-new' | 'back'): ModalStep {
  if (action === 'create-new') {
    return 'create-form';
  }
  if (action === 'back') {
    return 'choose';
  }
  return currentStep;
}

/**
 * Simulates modal state reset logic when modal opens
 */
function resetModalState(): {
  step: ModalStep;
  projectName: string;
  projectLocation: string;
  initGit: boolean;
  error: string | null;
} {
  return {
    step: 'choose',
    projectName: '',
    projectLocation: '',
    initGit: true,
    error: null,
  };
}

describe('AddProjectModal - Form Validation', () => {
  it('should return error when project name is empty', () => {
    const result = validateProjectCreation({
      projectName: '',
      projectLocation: '/some/path',
      t: mockT,
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Project name is required');
  });

  it('should return error when project name is only whitespace', () => {
    const result = validateProjectCreation({
      projectName: '   ',
      projectLocation: '/some/path',
      t: mockT,
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Project name is required');
  });

  it('should return error when project location is empty', () => {
    const result = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: '',
      t: mockT,
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Project location is required');
  });

  it('should return error when project location is only whitespace', () => {
    const result = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: '   ',
      t: mockT,
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Project location is required');
  });

  it('should validate successfully with valid name and location', () => {
    const result = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: '/home/user/projects',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
    expect(result.error).toBe(null);
  });

  it('should trim whitespace when validating project name', () => {
    const result = validateProjectCreation({
      projectName: '  my-project  ',
      projectLocation: '/home/user/projects',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
    expect(result.error).toBe(null);
  });

  it('should trim whitespace when validating project location', () => {
    const result = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: '  /home/user/projects  ',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
    expect(result.error).toBe(null);
  });

  it('should check project name before project location', () => {
    // Name is checked first, so should get name error even if location is also invalid
    const result = validateProjectCreation({
      projectName: '',
      projectLocation: '',
      t: mockT,
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toBe('Project name is required');
  });
});

describe('AddProjectModal - Step Transitions', () => {
  it('should transition from choose to create-form when create-new action', () => {
    const nextStep = getNextStep('choose', 'create-new');
    expect(nextStep).toBe('create-form');
  });

  it('should transition from create-form to choose when back action', () => {
    const nextStep = getNextStep('create-form', 'back');
    expect(nextStep).toBe('choose');
  });

  it('should stay on current step when no matching action', () => {
    const currentStep: ModalStep = 'choose';
    // @ts-expect-error - Testing invalid action
    const nextStep = getNextStep(currentStep, 'invalid-action');
    expect(nextStep).toBe('choose');
  });
});

describe('AddProjectModal - State Reset', () => {
  it('should reset all form fields when modal opens', () => {
    const state = resetModalState();

    expect(state.step).toBe('choose');
    expect(state.projectName).toBe('');
    expect(state.projectLocation).toBe('');
    expect(state.initGit).toBe(true);
    expect(state.error).toBe(null);
  });

  it('should set initGit to true by default', () => {
    const state = resetModalState();
    expect(state.initGit).toBe(true);
  });

  it('should clear any previous errors', () => {
    const state = resetModalState();
    expect(state.error).toBe(null);
  });

  it('should reset to choose step', () => {
    const state = resetModalState();
    expect(state.step).toBe('choose');
  });
});

describe('AddProjectModal - Error Handling', () => {
  it('should handle empty form submission gracefully', () => {
    const result = validateProjectCreation({
      projectName: '',
      projectLocation: '',
      t: mockT,
    });

    expect(result.isValid).toBe(false);
    expect(result.error).toBeTruthy();
  });

  it('should provide specific error messages for validation failures', () => {
    const nameError = validateProjectCreation({
      projectName: '',
      projectLocation: '/path',
      t: mockT,
    });

    const locationError = validateProjectCreation({
      projectName: 'project',
      projectLocation: '',
      t: mockT,
    });

    expect(nameError.error).toBe('Project name is required');
    expect(locationError.error).toBe('Project location is required');
  });

  it('should use translation function for error messages', () => {
    const customT = (key: string) => `TRANSLATED:${key}`;

    const result = validateProjectCreation({
      projectName: '',
      projectLocation: '/path',
      t: customT,
    });

    expect(result.error).toBe('TRANSLATED:addProject.nameRequired');
  });
});

describe('AddProjectModal - Edge Cases', () => {
  it('should handle special characters in project name', () => {
    const result = validateProjectCreation({
      projectName: 'my-project_2024!',
      projectLocation: '/home/user',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
  });

  it('should handle Windows-style paths', () => {
    const result = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: 'C:\\Users\\user\\projects',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
  });

  it('should handle Unix-style paths', () => {
    const result = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: '/home/user/projects',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
  });

  it('should handle paths with spaces', () => {
    const result = validateProjectCreation({
      projectName: 'my project',
      projectLocation: '/home/user/my projects',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
  });

  it('should handle very long project names', () => {
    const longName = 'a'.repeat(256);
    const result = validateProjectCreation({
      projectName: longName,
      projectLocation: '/home/user',
      t: mockT,
    });

    expect(result.isValid).toBe(true);
  });

  it('should handle very long paths', () => {
    const longPath = '/home/' + 'a'.repeat(256);
    const result = validateProjectCreation({
      projectName: 'project',
      projectLocation: longPath,
      t: mockT,
    });

    expect(result.isValid).toBe(true);
  });
});

describe('AddProjectModal - Integration Scenarios', () => {
  it('should support full workflow: choose → create-form → validate → reset', () => {
    // 1. Start at choose step
    let currentStep: ModalStep = 'choose';
    expect(currentStep).toBe('choose');

    // 2. Click "Create New" to go to form
    currentStep = getNextStep(currentStep, 'create-new');
    expect(currentStep).toBe('create-form');

    // 3. Attempt to submit empty form
    const validationResult = validateProjectCreation({
      projectName: '',
      projectLocation: '',
      t: mockT,
    });
    expect(validationResult.isValid).toBe(false);

    // 4. Fill in form and validate
    const validResult = validateProjectCreation({
      projectName: 'my-project',
      projectLocation: '/home/user/projects',
      t: mockT,
    });
    expect(validResult.isValid).toBe(true);

    // 5. Reset modal state
    const resetState = resetModalState();
    expect(resetState.step).toBe('choose');
    expect(resetState.projectName).toBe('');
  });

  it('should support back navigation: create-form → choose', () => {
    let currentStep: ModalStep = 'create-form';

    // Click back button
    currentStep = getNextStep(currentStep, 'back');
    expect(currentStep).toBe('choose');
  });

  it('should validate form before showing success', () => {
    // Invalid form
    const invalidResult = validateProjectCreation({
      projectName: '',
      projectLocation: '/path',
      t: mockT,
    });
    expect(invalidResult.isValid).toBe(false);

    // Valid form
    const validResult = validateProjectCreation({
      projectName: 'project',
      projectLocation: '/path',
      t: mockT,
    });
    expect(validResult.isValid).toBe(true);
  });
});
