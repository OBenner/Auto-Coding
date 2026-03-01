/**
 * Test Data Generator for Task Logs
 *
 * Generates realistic test data for task log entries to test virtual scrolling
 * and other UI features with large datasets (1000+ entries).
 */

import type {
  TaskLogEntry,
  TaskLogPhase,
  TaskLogEntryType,
  TaskLogs
} from '../../../../shared/types';

/**
 * Configuration for generating test log entries
 */
export interface TestDataGeneratorOptions {
  entryCount?: number;
  startTimestamp?: Date;
  includeErrors?: boolean;
  includeToolOutput?: boolean;
  subtaskCount?: number;
}

/**
 * Default configuration for test data generation
 */
const DEFAULT_OPTIONS: Required<TestDataGeneratorOptions> = {
  entryCount: 1000,
  startTimestamp: new Date('2025-01-01T10:00:00Z'),
  includeErrors: true,
  includeToolOutput: true,
  subtaskCount: 20
};

/**
 * Tool names commonly used in task execution
 */
const TOOL_NAMES = [
  'Read',
  'Write',
  'Bash',
  'Edit',
  'Grep',
  'Glob',
  'TodoWrite',
  'AskUserQuestion',
  'EnterPlanMode',
  'ExitPlanMode'
];

/**
 * Sample messages for different log entry types
 */
const SAMPLE_MESSAGES = {
  text: [
    'Analyzing current implementation...',
    'Reviewing codebase structure...',
    'Considering implementation approach...',
    'Evaluating options...',
    'Processing requirements...',
    'Building solution...',
    'Refining implementation...',
    'Optimizing performance...',
    'Adding error handling...',
    'Improving code quality...',
    'Writing documentation...',
    'Running tests...',
    'Fixing issues found...',
    'Completing feature implementation...',
    'Preparing for next phase...'
  ],
  error: [
    'Failed to read file: Permission denied',
    'Compilation error: Missing semicolon',
    'Type error: Property does not exist',
    'Runtime error: Cannot read property',
    'Network timeout: Connection failed',
    'Test failure: Assertion failed',
    'Build error: Dependency not found',
    'Configuration error: Invalid settings'
  ],
  success: [
    'Implementation completed successfully',
    'All tests passed',
    'Build completed',
    'Files created successfully',
    'Configuration updated',
    'Feature deployed',
    'Migration completed',
    'Optimization applied'
  ],
  info: [
    'Starting new phase...',
    'Switching context...',
    'Loading configuration...',
    'Initializing subsystem...',
    'Preparing environment...',
    'Checking dependencies...',
    'Validating inputs...',
    'Setup complete'
  ]
};

/**
 * Subphase names for planning phase
 */
const PLANNING_SUBPHASES = [
  'PROJECT DISCOVERY',
  'CONTEXT GATHERING',
  'REQUIREMENTS ANALYSIS',
  'ARCHITECTURE DESIGN',
  'IMPLEMENTATION PLANNING'
];

/**
 * Subphase names for coding phase
 */
const CODING_SUBPHASES = [
  'FOUNDATION',
  'CORE FEATURES',
  'INTEGRATION',
  'TESTING',
  'REFACTORING'
];

/**
 * Subphase names for validation phase
 */
const VALIDATION_SUBPHASES = [
  'ACCEPTANCE TESTING',
  'BUG FIXING',
  'RETESTING',
  'FINAL VALIDATION'
];

/**
 * Generate a random integer between min and max (inclusive)
 */
function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Pick a random item from an array
 */
function randomPick<T>(array: T[]): T {
  return array[randomInt(0, array.length - 1)];
}

/**
 * Increment a timestamp by a random number of milliseconds
 */
function incrementTimestamp(date: Date, maxMs: number = 60000): Date {
  return new Date(date.getTime() + randomInt(100, maxMs));
}

/**
 * Generate a single log entry with realistic data
 */
function generateLogEntry(
  index: number,
  timestamp: Date,
  phase: TaskLogPhase,
  options: Required<TestDataGeneratorOptions>
): TaskLogEntry {
  // Determine entry type based on patterns
  let type: TaskLogEntryType;
  const rand = Math.random();

  if (rand < 0.5) {
    type = 'text';
  } else if (rand < 0.65) {
    type = 'tool_start';
  } else if (rand < 0.8) {
    type = 'tool_end';
  } else if (rand < 0.85) {
    type = 'info';
  } else if (rand < 0.9 && options.includeErrors) {
    type = 'error';
  } else if (rand < 0.95) {
    type = 'success';
  } else {
    type = randomPick(['phase_start', 'phase_end']);
  }

  // Generate content based on type
  let content: string;
  let tool_name: string | undefined;
  let tool_input: string | undefined;
  let detail: string | undefined;
  let subphase: string | undefined;
  let collapsed: boolean | undefined;

  switch (type) {
    case 'text':
      content = `(${index}) ${randomPick(SAMPLE_MESSAGES.text)}`;
      break;

    case 'tool_start':
      tool_name = randomPick(TOOL_NAMES);
      content = `Starting: ${tool_name}`;
      if (tool_name === 'Read') {
        tool_input = `apps/backend/core/file_${randomInt(1, 100)}.py`;
        detail = `Reading file: ${tool_input}\nLine count: ${randomInt(50, 500)}`;
      } else if (tool_name === 'Write') {
        tool_input = `apps/frontend/src/components/Component${randomInt(1, 50)}.tsx`;
        detail = `Writing ${randomInt(20, 300)} lines to ${tool_input}`;
      } else if (tool_name === 'Bash') {
        tool_input = `npm run ${randomPick(['test', 'build', 'lint', 'typecheck'])}`;
        detail = `Executing command in ${tool_name}`;
      }
      collapsed = false;
      break;

    case 'tool_end':
      tool_name = randomPick(TOOL_NAMES);
      content = `Completed: ${tool_name}`;
      if (Math.random() > 0.7) {
        detail = JSON.stringify({
          exit_code: 0,
          duration_ms: randomInt(50, 5000),
          output: 'Operation completed successfully'
        }, null, 2);
      }
      collapsed = true;
      break;

    case 'error':
      content = randomPick(SAMPLE_MESSAGES.error);
      detail = `Error at index ${index}\nStack trace:\n  at process (${randomPick(['file1.py', 'file2.ts', 'file3.js'])}:${randomInt(1, 100)}:${randomInt(1, 50)})`;
      collapsed = false;
      break;

    case 'success':
      content = randomPick(SAMPLE_MESSAGES.success);
      break;

    case 'info':
      content = randomPick(SAMPLE_MESSAGES.info);
      break;

    case 'phase_start':
      content = `Starting phase: ${phase}`;
      detail = `Phase: ${phase}\nTimestamp: ${timestamp.toISOString()}`;
      break;

    case 'phase_end':
      content = `Completed phase: ${phase}`;
      detail = `Phase: ${phase}\nDuration: ${randomInt(1, 60)} minutes\nEntries: ${randomInt(10, 100)}`;
      break;

    default:
      content = `Log entry ${index}`;
  }

  // Add subphase for certain types
  if ((type === 'text' || type === 'tool_start' || type === 'tool_end') && Math.random() > 0.6) {
    if (phase === 'planning') {
      subphase = randomPick(PLANNING_SUBPHASES);
    } else if (phase === 'coding') {
      subphase = randomPick(CODING_SUBPHASES);
    } else if (phase === 'validation') {
      subphase = randomPick(VALIDATION_SUBPHASES);
    }
  }

  // Assign to a random subtask
  const subtask_id = Math.random() > 0.3
    ? `subtask-${randomInt(1, options.subtaskCount)}`
    : undefined;

  return {
    timestamp: timestamp.toISOString(),
    type,
    content,
    phase,
    tool_name,
    tool_input,
    subtask_id,
    session: randomInt(1, 5),
    detail,
    subphase,
    collapsed
  };
}

/**
 * Generate a complete TaskLogs object with the specified number of entries
 */
export function generateTestTaskLogs(
  options: TestDataGeneratorOptions = {}
): TaskLogs {
  const config = { ...DEFAULT_OPTIONS, ...options };

  // Generate entries distributed across phases
  const planningEntries: TaskLogEntry[] = [];
  const codingEntries: TaskLogEntry[] = [];
  const validationEntries: TaskLogEntry[] = [];

  const entriesPerPhase = Math.floor(config.entryCount / 3);
  const planningCount = entriesPerPhase;
  const codingCount = entriesPerPhase + (config.entryCount % 3);
  const validationCount = entriesPerPhase;

  let currentTimestamp = config.startTimestamp;

  // Generate planning phase entries
  for (let i = 0; i < planningCount; i++) {
    currentTimestamp = incrementTimestamp(currentTimestamp, 30000);
    planningEntries.push(
      generateLogEntry(i + 1, currentTimestamp, 'planning', config)
    );
  }

  // Add phase start/end markers
  planningEntries.unshift({
    timestamp: config.startTimestamp.toISOString(),
    type: 'phase_start',
    content: 'Starting phase: planning',
    phase: 'planning',
    subphase: 'PROJECT DISCOVERY'
  });
  planningEntries.push({
    timestamp: currentTimestamp.toISOString(),
    type: 'phase_end',
    content: 'Completed phase: planning',
    phase: 'planning',
    detail: `Generated ${planningCount} log entries in planning phase`
  });

  // Generate coding phase entries
  for (let i = 0; i < codingCount; i++) {
    currentTimestamp = incrementTimestamp(currentTimestamp, 20000);
    codingEntries.push(
      generateLogEntry(planningCount + i + 1, currentTimestamp, 'coding', config)
    );
  }

  const codingStartTimestamp = new Date(planningEntries[planningEntries.length - 1].timestamp);
  codingEntries.unshift({
    timestamp: codingStartTimestamp.toISOString(),
    type: 'phase_start',
    content: 'Starting phase: coding',
    phase: 'coding',
    subphase: 'FOUNDATION'
  });
  codingEntries.push({
    timestamp: currentTimestamp.toISOString(),
    type: 'phase_end',
    content: 'Completed phase: coding',
    phase: 'coding',
    detail: `Generated ${codingCount} log entries in coding phase`
  });

  // Generate validation phase entries
  for (let i = 0; i < validationCount; i++) {
    currentTimestamp = incrementTimestamp(currentTimestamp, 15000);
    validationEntries.push(
      generateLogEntry(planningCount + codingCount + i + 1, currentTimestamp, 'validation', config)
    );
  }

  const validationStartTimestamp = new Date(codingEntries[codingEntries.length - 1].timestamp);
  validationEntries.unshift({
    timestamp: validationStartTimestamp.toISOString(),
    type: 'phase_start',
    content: 'Starting phase: validation',
    phase: 'validation',
    subphase: 'ACCEPTANCE TESTING'
  });
  validationEntries.push({
    timestamp: currentTimestamp.toISOString(),
    type: 'phase_end',
    content: 'Completed phase: validation',
    phase: 'validation',
    detail: `Generated ${validationCount} log entries in validation phase`
  });

  return {
    spec_id: `test-spec-${Date.now()}`,
    created_at: config.startTimestamp.toISOString(),
    updated_at: currentTimestamp.toISOString(),
    phases: {
      planning: {
        phase: 'planning',
        status: 'completed',
        started_at: planningEntries[0].timestamp,
        completed_at: planningEntries[planningEntries.length - 1].timestamp,
        entries: planningEntries
      },
      coding: {
        phase: 'coding',
        status: 'completed',
        started_at: codingEntries[0].timestamp,
        completed_at: codingEntries[codingEntries.length - 1].timestamp,
        entries: codingEntries
      },
      validation: {
        phase: 'validation',
        status: 'completed',
        started_at: validationEntries[0].timestamp,
        completed_at: validationEntries[validationEntries.length - 1].timestamp,
        entries: validationEntries
      }
    }
  };
}

/**
 * Generate a flat array of log entries from all phases
 */
export function generateTestLogEntries(
  options: TestDataGeneratorOptions = {}
): TaskLogEntry[] {
  const taskLogs = generateTestTaskLogs(options);

  return [
    ...taskLogs.phases.planning.entries,
    ...taskLogs.phases.coding.entries,
    ...taskLogs.phases.validation.entries
  ];
}

/**
 * Generate log entries with specific characteristics for targeted testing
 */
export function generateSpecializedTestLogs(
  scenario: 'errors-only' | 'tools-only' | 'text-only' | 'mixed-heavy',
  count: number = 100
): TaskLogEntry[] {
  const options: TestDataGeneratorOptions = {
    entryCount: count,
    startTimestamp: new Date(),
    includeErrors: scenario === 'errors-only',
    includeToolOutput: true,
    subtaskCount: 10
  };

  const allEntries = generateTestLogEntries(options);

  switch (scenario) {
    case 'errors-only':
      return allEntries.filter(e => e.type === 'error' || e.type === 'text');

    case 'tools-only':
      return allEntries.filter(e => e.type === 'tool_start' || e.type === 'tool_end');

    case 'text-only':
      return allEntries.filter(e => e.type === 'text' || e.type === 'info');

    default:
      // Return all entries with extra detail content
      return allEntries.map(entry => ({
        ...entry,
        detail: entry.detail || `Extended detail content for entry testing purposes.\n`.repeat(5)
      }));
  }
}
