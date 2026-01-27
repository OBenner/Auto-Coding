/**
 * Generate large test log files for performance testing
 *
 * Usage:
 *   npx tsx scripts/generate-test-logs.ts [entries] [output-file]
 *
 * Example:
 *   npx tsx scripts/generate-test-logs.ts 1000 test-logs.json
 */

import { writeFileSync } from 'fs';
import { join } from 'path';

interface TaskLogEntry {
  type: 'text' | 'tool_start' | 'tool_end' | 'error' | 'success' | 'info';
  content: string;
  timestamp: string;
  detail?: string;
  tool_name?: string;
  tool_input?: string;
  subphase?: string;
}

interface TaskPhaseLog {
  status: 'pending' | 'active' | 'completed' | 'failed';
  entries: TaskLogEntry[];
  startedAt?: string;
  completedAt?: string;
}

interface TaskLogs {
  taskId: string;
  phases: {
    planning: TaskPhaseLog;
    coding: TaskPhaseLog;
    validation: TaskPhaseLog;
  };
}

const TOOLS = ['Read', 'Write', 'Edit', 'Bash', 'Glob', 'Grep'];
const SUBPHASES = ['discovery', 'implementation', 'testing', 'review', 'fixing'];

function randomItem<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function generateTimestamp(baseTime: number, offset: number): string {
  return new Date(baseTime + offset * 1000).toISOString();
}

function generateLogEntry(index: number, baseTime: number): TaskLogEntry {
  const types = ['text', 'tool_start', 'tool_end', 'error', 'success', 'info'] as const;
  const type = randomItem(types);
  const timestamp = generateTimestamp(baseTime, index);

  switch (type) {
    case 'tool_start': {
      const tool = randomItem(TOOLS);
      return {
        type,
        content: `Starting ${tool}`,
        timestamp,
        tool_name: tool,
        tool_input: tool === 'Read' ? 'src/components/Example.tsx' :
                   tool === 'Bash' ? 'npm test' :
                   tool === 'Edit' ? 'src/utils/helper.ts' :
                   'pattern/**/*.ts',
        subphase: randomItem(SUBPHASES),
      };
    }
    case 'tool_end': {
      const tool = randomItem(TOOLS);
      const hasDetail = Math.random() > 0.5;
      return {
        type,
        content: `Completed ${tool}`,
        timestamp,
        tool_name: tool,
        detail: hasDetail ? `Output from ${tool}:\n${'Sample output line\n'.repeat(Math.floor(Math.random() * 20) + 5)}` : undefined,
      };
    }
    case 'error':
      return {
        type,
        content: `Error: Failed to process item ${index}`,
        timestamp,
        detail: Math.random() > 0.3 ? `Stack trace:\n  at Object.<anonymous> (/app/src/index.ts:${index}:10)\n  at Module._compile (internal/modules/cjs/loader.js:1063:30)\n  at Object.Module._extensions..js (internal/modules/cjs/loader.js:1092:10)` : undefined,
        subphase: randomItem(SUBPHASES),
      };
    case 'success':
      return {
        type,
        content: `Successfully completed step ${index}`,
        timestamp,
        subphase: randomItem(SUBPHASES),
      };
    case 'info':
      return {
        type,
        content: `Processing item ${index} of batch`,
        timestamp,
        subphase: randomItem(SUBPHASES),
      };
    default:
      return {
        type: 'text',
        content: `Log entry ${index}: Performing operation on data set ${Math.floor(index / 10)}`,
        timestamp,
        detail: Math.random() > 0.7 ? `Additional details:\n- Item count: ${index}\n- Status: processing\n- Next step: validation` : undefined,
      };
  }
}

function generatePhaseLog(
  phase: string,
  entryCount: number,
  baseTime: number,
  status: 'pending' | 'active' | 'completed' | 'failed'
): TaskPhaseLog {
  const entries: TaskLogEntry[] = [];

  for (let i = 0; i < entryCount; i++) {
    entries.push(generateLogEntry(i, baseTime + i));
  }

  return {
    status,
    entries,
    startedAt: status !== 'pending' ? generateTimestamp(baseTime, 0) : undefined,
    completedAt: status === 'completed' ? generateTimestamp(baseTime, entryCount) : undefined,
  };
}

function generateLargeLogs(totalEntries: number): TaskLogs {
  const baseTime = Date.now() - totalEntries * 1000;

  // Distribute entries across phases
  const planningCount = Math.floor(totalEntries * 0.2);  // 20%
  const codingCount = Math.floor(totalEntries * 0.6);    // 60%
  const validationCount = totalEntries - planningCount - codingCount; // Remaining

  return {
    taskId: 'test-task-large-logs',
    phases: {
      planning: generatePhaseLog('planning', planningCount, baseTime, 'completed'),
      coding: generatePhaseLog('coding', codingCount, baseTime + planningCount * 1000, 'active'),
      validation: generatePhaseLog('validation', validationCount, baseTime + (planningCount + codingCount) * 1000, 'pending'),
    },
  };
}

// Main execution
const args = process.argv.slice(2);
const entryCount = parseInt(args[0]) || 1000;
const outputFile = args[1] || join(__dirname, '..', 'test-logs.json');

console.log(`Generating ${entryCount} log entries...`);
const logs = generateLargeLogs(entryCount);

const totalGenerated =
  logs.phases.planning.entries.length +
  logs.phases.coding.entries.length +
  logs.phases.validation.entries.length;

writeFileSync(outputFile, JSON.stringify(logs, null, 2));

console.log(`✅ Generated ${totalGenerated} log entries`);
console.log(`   Planning: ${logs.phases.planning.entries.length} entries`);
console.log(`   Coding: ${logs.phases.coding.entries.length} entries`);
console.log(`   Validation: ${logs.phases.validation.entries.length} entries`);
console.log(`📁 Saved to: ${outputFile}`);
console.log(`\nTo use this in performance testing:`);
console.log(`1. Copy the generated JSON file to a task's logs.json file`);
console.log(`2. Open the task in TaskDetailModal`);
console.log(`3. Navigate to the Logs tab`);
console.log(`4. Measure performance using browser DevTools`);
