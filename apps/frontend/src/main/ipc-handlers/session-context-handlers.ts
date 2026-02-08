import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import path from 'path';
import { promises as fsPromises } from 'fs';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  ConversationHistory,
  SessionContextSummary,
  OptimizedContext
} from '../../shared/types';
import { projectStore } from '../project-store';
import {
  loadProjectEnvVars,
  isGraphitiEnabled,
  getGraphitiDatabaseDetails
} from './context/utils';
import { runPythonSubprocess } from './github/utils/subprocess-runner';
import { parsePythonCommand } from '../python-detector';

/**
 * Check if a file exists
 */
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Load conversation history from file-based storage
 */
async function loadConversationHistory(
  specDir: string,
  sessionId?: string
): Promise<ConversationHistory[]> {
  const histories: ConversationHistory[] = [];

  if (!(await fileExists(specDir))) {
    return histories;
  }

  const memoryDir = path.join(specDir, 'memory');
  if (!(await fileExists(memoryDir))) {
    return histories;
  }

  const conversationHistoryDir = path.join(memoryDir, 'conversation_history');
  if (!(await fileExists(conversationHistoryDir))) {
    return histories;
  }

  try {
    const files = await fsPromises.readdir(conversationHistoryDir);
    const historyFiles = files
      .filter((f: string) => f.startsWith('session_') && f.endsWith('.json'))
      .sort()
      .reverse();

    for (const file of historyFiles) {
      // Filter by session ID if provided
      if (sessionId && !file.includes(sessionId)) {
        continue;
      }

      try {
        const filePath = path.join(conversationHistoryDir, file);
        const content = await fsPromises.readFile(filePath, 'utf-8');
        const historyData = JSON.parse(content) as ConversationHistory;
        histories.push(historyData);
      } catch (error) {
        console.warn(`Failed to load conversation history file ${file}:`, error);
      }
    }
  } catch (error) {
    console.error('Failed to read conversation history directory:', error);
  }

  return histories;
}

/**
 * Load session context summaries from file-based storage
 */
async function loadSessionContextSummaries(
  specDir: string
): Promise<SessionContextSummary[]> {
  const summaries: SessionContextSummary[] = [];

  if (!(await fileExists(specDir))) {
    return summaries;
  }

  const memoryDir = path.join(specDir, 'memory');
  if (!(await fileExists(memoryDir))) {
    return summaries;
  }

  const sessionContextDir = path.join(memoryDir, 'session_context');
  if (!(await fileExists(sessionContextDir))) {
    return summaries;
  }

  try {
    const files = await fsPromises.readdir(sessionContextDir);
    const summaryFiles = files
      .filter((f: string) => f.startsWith('session_') && f.endsWith('.json'))
      .sort()
      .reverse();

    for (const file of summaryFiles) {
      try {
        const filePath = path.join(sessionContextDir, file);
        const content = await fsPromises.readFile(filePath, 'utf-8');
        const summaryData = JSON.parse(content) as SessionContextSummary;
        summaries.push(summaryData);
      } catch (error) {
        console.warn(`Failed to load session context summary ${file}:`, error);
      }
    }
  } catch (error) {
    console.error('Failed to read session context directory:', error);
  }

  return summaries;
}

/**
 * Register session context handlers
 */
export function registerSessionContextHandlers(
  _getMainWindow: () => BrowserWindow | null
): void {
  /**
   * Get conversation history for a task/session
   */
  ipcMain.handle(
    IPC_CHANNELS.SESSION_CONTEXT_GET_HISTORY,
    async (
      _,
      projectId: string,
      taskId: string,
      sessionId?: string
    ): Promise<IPCResult<ConversationHistory[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
        const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

        // Try Python backend with Graphiti first
        if (graphitiEnabled) {
          try {
            const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
            const backendPath = path.join(project.path, 'apps', 'backend');

            // Prepare arguments for session context retrieval
            const args = [
              '-c',
              `
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from agents.session_context import SessionContext
    from integrations.graphiti.queries_pkg.client import get_graphiti_client_sync

    session_id = ${JSON.stringify(sessionId || taskId)}
    project_dir = Path('${project.path.replace(/\\/g, '\\\\')}')
    spec_dir = project_dir / '.auto-claude' / 'specs' / '${taskId}'

    # Get client
    client = get_graphiti_client_sync(str(project_dir))
    if not client:
        print(json.dumps({"error": "Failed to initialize Graphiti client"}))
        return

    # Initialize SessionContext
    session_context = SessionContext(spec_dir=spec_dir, project_dir=project_dir, graphiti_memory=client)
    await session_context.initialize()

    # Get optimized context for the session
    optimized = await session_context.get_optimized_context(query="")

    # Build ConversationHistory from optimized context
    all_rounds = optimized.get("recent_rounds", []) + optimized.get("relevant_rounds", [])
    history = {
        "session_id": session_id,
        "subtask_id": None,
        "session_start": all_rounds[0].get("timestamp", "") if all_rounds else "",
        "rounds": all_rounds,
        "total_input_tokens": sum(r.get("input_tokens", 0) for r in all_rounds),
        "total_output_tokens": sum(r.get("output_tokens", 0) for r in all_rounds),
        "all_code_references": optimized.get("code_references", [])
    }

    print(json.dumps({"histories": [history]}))

asyncio.run(main())
              `.trim()
            ];

            const { promise } = runPythonSubprocess<{ histories: ConversationHistory[] }>({
              pythonPath: pythonCommand,
              args: [...baseArgs, ...args],
              cwd: backendPath,
              env: { ...process.env, PYTHONPATH: backendPath }
            });

            const result = await promise;

            if (result.success) {
              try {
                const lines = result.stdout.split('\n');
                const jsonLine = lines.find(line => line.trim().startsWith('{'));
                if (jsonLine) {
                  const data = JSON.parse(jsonLine);
                  if (!data.error && data.histories) {
                    return { success: true, data: data.histories };
                  }
                }
              } catch (parseError) {
                console.warn('Failed to parse Python output, falling back to file-based:', parseError);
              }
            }
          } catch (error) {
            console.warn('Failed to get history from Python backend, falling back to file-based:', error);
          }
        }

        // Fall back to file-based storage
        const specDir = path.join(
          project.path,
          '.auto-claude',
          'specs',
          taskId
        );

        const histories = await loadConversationHistory(specDir, sessionId);

        return {
          success: true,
          data: histories
        };
      } catch (error) {
        console.error('Failed to get conversation history:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get session context summaries for a task
   */
  ipcMain.handle(
    IPC_CHANNELS.SESSION_CONTEXT_GET_SUMMARIES,
    async (
      _,
      projectId: string,
      taskId: string,
      limit: number = 20
    ): Promise<IPCResult<SessionContextSummary[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
        const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

        // Try Python backend with Graphiti first
        if (graphitiEnabled) {
          try {
            const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
            const backendPath = path.join(project.path, 'apps', 'backend');

            // Prepare arguments for session summaries
            const args = [
              '-c',
              `
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from integrations.graphiti.queries_pkg.client import get_graphiti_client_sync
    from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_CONVERSATION_ROUND

    limit = ${limit}
    project_dir = Path('${project.path.replace(/\\/g, '\\\\')}')
    task_id = '${taskId}'

    # Get client
    client = get_graphiti_client_sync(str(project_dir))
    if not client:
        print(json.dumps({"error": "Failed to initialize Graphiti client"}))
        return

    # Generate group_id from project path
    import hashlib
    project_name = project_dir.name
    path_hash = hashlib.md5(str(project_dir.resolve()).encode(), usedforsecurity=False).hexdigest()[:8]
    group_id = f"project_{project_name}_{path_hash}"

    # Get all episodes of type conversation_round
    episodes = await client.graphiti.get_episodes(
        group_id=group_id,
        limit=limit * 10
    )

    # Group by session_id and create summaries
    sessions = {}
    for ep in episodes:
        if ep.episode_body:
            try:
                body = json.loads(ep.episode_body)
                if body.get("type") == EPISODE_TYPE_CONVERSATION_ROUND:
                    session_id = body.get("session_id")
                    # Filter by task_id (spec_id)
                    if body.get("spec_id") != task_id:
                        continue

                    if session_id and session_id not in sessions:
                        sessions[session_id] = {
                            "session_id": session_id,
                            "subtask_id": body.get("subtask_id"),
                            "session_start": ep.created_at,
                            "total_rounds": 0,
                            "total_input_tokens": 0,
                            "total_output_tokens": 0,
                            "code_references": set()
                        }

                    if session_id in sessions:
                        sessions[session_id]["total_rounds"] += 1
                        round_data = body.get("round_data", {})
                        sessions[session_id]["total_input_tokens"] += round_data.get("input_tokens", 0)
                        sessions[session_id]["total_output_tokens"] += round_data.get("output_tokens", 0)
                        sessions[session_id]["code_references"].update(round_data.get("code_references", []))
            except:
                pass

    # Convert to list and sort by start time
    summaries = []
    for session_data in sessions.values():
        session_data["code_references"] = list(session_data["code_references"])
        summaries.append(session_data)

    summaries.sort(key=lambda x: x.get("session_start", ""), reverse=True)
    summaries = summaries[:limit]

    print(json.dumps({"summaries": summaries}))

asyncio.run(main())
              `.trim()
            ];

            const { promise } = runPythonSubprocess<{ summaries: SessionContextSummary[] }>({
              pythonPath: pythonCommand,
              args: [...baseArgs, ...args],
              cwd: backendPath,
              env: { ...process.env, PYTHONPATH: backendPath }
            });

            const result = await promise;

            if (result.success) {
              try {
                const lines = result.stdout.split('\n');
                const jsonLine = lines.find(line => line.trim().startsWith('{'));
                if (jsonLine) {
                  const data = JSON.parse(jsonLine);
                  if (!data.error && data.summaries) {
                    return { success: true, data: data.summaries };
                  }
                }
              } catch (parseError) {
                console.warn('Failed to parse Python output, falling back to file-based:', parseError);
              }
            }
          } catch (error) {
            console.warn('Failed to get summaries from Python backend, falling back to file-based:', error);
          }
        }

        // Fall back to file-based storage
        const specDir = path.join(
          project.path,
          '.auto-claude',
          'specs',
          taskId
        );

        const summaries = await loadSessionContextSummaries(specDir);

        return {
          success: true,
          data: summaries
        };
      } catch (error) {
        console.error('Failed to get session context summaries:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get code references from conversation history
   */
  ipcMain.handle(
    IPC_CHANNELS.SESSION_CONTEXT_GET_CODE_REFS,
    async (
      _,
      projectId: string,
      taskId: string,
      sessionId?: string,
      filePath?: string
    ): Promise<IPCResult<string[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
        const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

        // Try Python backend with Graphiti first
        if (graphitiEnabled) {
          try {
            const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
            const backendPath = path.join(project.path, 'apps', 'backend');

            // Prepare arguments for code references
            const args = [
              '-c',
              `
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from agents.session_context import SessionContext
    from integrations.graphiti.queries_pkg.client import get_graphiti_client_sync

    session_id = ${JSON.stringify(sessionId || null)}
    file_path = ${JSON.stringify(filePath || null)}
    project_dir = Path('${project.path.replace(/\\/g, '\\\\')}')
    spec_dir = project_dir / '.auto-claude' / 'specs' / '${taskId}'

    # Get client
    client = get_graphiti_client_sync(str(project_dir))
    if not client:
        print(json.dumps({"error": "Failed to initialize Graphiti client"}))
        return

    # Initialize SessionContext
    session_context = SessionContext(spec_dir=spec_dir, project_dir=project_dir, graphiti_memory=client)
    await session_context.initialize()

    # Get code references
    if session_id:
        refs = await session_context.get_all_code_references_for_session(session_id)
    elif file_path:
        sessions = await session_context.get_sessions_for_file(file_path)
        refs = set()
        for s in sessions:
            refs.update(s.get("code_references", []))
    else:
        # Get all code references for this task
        refs = set()
        # Would need to query all sessions for this task
        # For now, return empty set
        refs = set()

    print(json.dumps({"code_references": list(refs)}))

asyncio.run(main())
              `.trim()
            ];

            const { promise } = runPythonSubprocess<{ code_references: string[] }>({
              pythonPath: pythonCommand,
              args: [...baseArgs, ...args],
              cwd: backendPath,
              env: { ...process.env, PYTHONPATH: backendPath }
            });

            const result = await promise;

            if (result.success) {
              try {
                const lines = result.stdout.split('\n');
                const jsonLine = lines.find(line => line.trim().startsWith('{'));
                if (jsonLine) {
                  const data = JSON.parse(jsonLine);
                  if (!data.error && data.code_references) {
                    return { success: true, data: data.code_references };
                  }
                }
              } catch (parseError) {
                console.warn('Failed to parse Python output, falling back to file-based:', parseError);
              }
            }
          } catch (error) {
            console.warn('Failed to get code refs from Python backend, falling back to file-based:', error);
          }
        }

        // Fall back to file-based storage
        const specDir = path.join(
          project.path,
          '.auto-claude',
          'specs',
          taskId
        );

        const histories = await loadConversationHistory(specDir, sessionId);

        // Collect all unique code references
        const allCodeRefs = new Set<string>();
        for (const history of histories) {
          if (history.all_code_references) {
            history.all_code_references.forEach(ref => allCodeRefs.add(ref));
          }
        }

        return {
          success: true,
          data: Array.from(allCodeRefs).sort()
        };
      } catch (error) {
        console.error('Failed to get code references:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );

  /**
   * Get all sessions for the project
   */
  ipcMain.handle(
    IPC_CHANNELS.SESSION_CONTEXT_GET_ALL_SESSIONS,
    async (
      _,
      projectId: string,
      limit: number = 20
    ): Promise<IPCResult<SessionContextSummary[]>> => {
      try {
        const project = projectStore.getProject(projectId);
        if (!project) {
          return { success: false, error: 'Project not found' };
        }

        const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
        const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

        // Try Python backend with Graphiti first
        if (graphitiEnabled) {
          try {
            const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
            const backendPath = path.join(project.path, 'apps', 'backend');

            // Prepare arguments for all sessions
            const args = [
              '-c',
              `
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from integrations.graphiti.queries_pkg.client import get_graphiti_client_sync
    from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_CONVERSATION_ROUND

    limit = ${limit}
    project_dir = Path('${project.path.replace(/\\/g, '\\\\')}')

    # Get client
    client = get_graphiti_client_sync(str(project_dir))
    if not client:
        print(json.dumps({"error": "Failed to initialize Graphiti client"}))
        return

    # Generate group_id from project path
    import hashlib
    project_name = project_dir.name
    path_hash = hashlib.md5(str(project_dir.resolve()).encode(), usedforsecurity=False).hexdigest()[:8]
    group_id = f"project_{project_name}_{path_hash}"

    # Get all episodes of type conversation_round
    episodes = await client.graphiti.get_episodes(
        group_id=group_id,
        limit=limit * 10
    )

    # Group by session_id and create summaries
    sessions = {}
    for ep in episodes:
        if ep.episode_body:
            try:
                body = json.loads(ep.episode_body)
                if body.get("type") == EPISODE_TYPE_CONVERSATION_ROUND:
                    session_id = body.get("session_id")
                    if session_id and session_id not in sessions:
                        sessions[session_id] = {
                            "session_id": session_id,
                            "subtask_id": body.get("subtask_id"),
                            "session_start": ep.created_at,
                            "total_rounds": 0,
                            "total_input_tokens": 0,
                            "total_output_tokens": 0,
                            "code_references": set()
                        }

                    if session_id in sessions:
                        sessions[session_id]["total_rounds"] += 1
                        round_data = body.get("round_data", {})
                        sessions[session_id]["total_input_tokens"] += round_data.get("input_tokens", 0)
                        sessions[session_id]["total_output_tokens"] += round_data.get("output_tokens", 0)
                        sessions[session_id]["code_references"].update(round_data.get("code_references", []))
            except:
                pass

    # Convert to list and sort by start time
    all_sessions = []
    for session_data in sessions.values():
        session_data["code_references"] = list(session_data["code_references"])
        all_sessions.append(session_data)

    all_sessions.sort(key=lambda x: x.get("session_start", ""), reverse=True)
    all_sessions = all_sessions[:limit]

    print(json.dumps({"sessions": all_sessions}))

asyncio.run(main())
              `.trim()
            ];

            const { promise } = runPythonSubprocess<{ sessions: SessionContextSummary[] }>({
              pythonPath: pythonCommand,
              args: [...baseArgs, ...args],
              cwd: backendPath,
              env: { ...process.env, PYTHONPATH: backendPath }
            });

            const result = await promise;

            if (result.success) {
              try {
                const lines = result.stdout.split('\n');
                const jsonLine = lines.find(line => line.trim().startsWith('{'));
                if (jsonLine) {
                  const data = JSON.parse(jsonLine);
                  if (!data.error && data.sessions) {
                    return { success: true, data: data.sessions };
                  }
                }
              } catch (parseError) {
                console.warn('Failed to parse Python output, falling back to file-based:', parseError);
              }
            }
          } catch (error) {
            console.warn('Failed to get all sessions from Python backend, falling back to file-based:', error);
          }
        }

        // Fall back to file-based storage
        const specsDir = path.join(project.path, '.auto-claude', 'specs');
        if (!(await fileExists(specsDir))) {
          return { success: true, data: [] };
        }

        const allSummaries: SessionContextSummary[] = [];

        // Iterate through all spec directories
        const specDirs = await fsPromises.readdir(specsDir);
        for (const specDir of specDirs) {
          const specPath = path.join(specsDir, specDir);
          const stat = await fsPromises.stat(specPath);

          if (stat.isDirectory()) {
            const summaries = await loadSessionContextSummaries(specPath);
            allSummaries.push(...summaries);
          }
        }

        // Sort by session start time (most recent first)
        allSummaries.sort(
          (a, b) =>
            new Date(b.session_start).getTime() -
            new Date(a.session_start).getTime()
        );

        // Apply limit
        const limitedSummaries = allSummaries.slice(0, limit);

        return {
          success: true,
          data: limitedSummaries
        };
      } catch (error) {
        console.error('Failed to get all sessions:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error'
        };
      }
    }
  );
}
