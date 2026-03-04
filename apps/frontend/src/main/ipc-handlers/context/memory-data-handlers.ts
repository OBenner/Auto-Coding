import { ipcMain } from 'electron';
import type { BrowserWindow } from 'electron';
import path from 'path';
import { promises as fsPromises } from 'fs';
import { IPC_CHANNELS, getSpecsDir } from '../../../shared/constants';
import type {
  IPCResult,
  MemoryEpisode,
  ContextSearchResult,
  PatternSuggestion,
  KnowledgeBaseConfig,
  KnowledgeBaseConnectionTest,
  ProjectEnvConfig
} from '../../../shared/types';
import { projectStore } from '../../project-store';
import { getMemoryService, isKuzuAvailable } from '../../memory-service';
import {
  loadProjectEnvVars,
  isGraphitiEnabled,
  getGraphitiDatabaseDetails
} from './utils';
import { runPythonSubprocess } from '../github/utils/subprocess-runner';
import { parsePythonCommand } from '../../python-detector';
import { parseEnvFile } from '../utils';

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
 * Load file-based memories from spec directories
 */
export async function loadFileBasedMemories(
  specsDir: string,
  limit: number
): Promise<MemoryEpisode[]> {
  const memories: MemoryEpisode[] = [];

  if (!(await fileExists(specsDir))) {
    return memories;
  }

  const allFiles = await fsPromises.readdir(specsDir);
  const recentSpecDirs: string[] = [];

  for (const f of allFiles) {
    const specPath = path.join(specsDir, f);
    const stat = await fsPromises.stat(specPath);
    if (stat.isDirectory()) {
      recentSpecDirs.push(f);
    }
  }

  recentSpecDirs.sort((a, b) => b.localeCompare(a));
  const topSpecDirs = recentSpecDirs.slice(0, 10); // Last 10 specs

  for (const specDir of topSpecDirs) {
    const memoryDir = path.join(specsDir, specDir, 'memory');
    if (!(await fileExists(memoryDir))) continue;

    // Load session insights
    const sessionInsightsDir = path.join(memoryDir, 'session_insights');
    if (await fileExists(sessionInsightsDir)) {
      const allSessionFiles = await fsPromises.readdir(sessionInsightsDir);
      const sessionFiles = allSessionFiles
        .filter((f: string) => f.startsWith('session_') && f.endsWith('.json'))
        .sort()
        .reverse();

      for (const sessionFile of sessionFiles.slice(0, 3)) {
        try {
          const sessionPath = path.join(sessionInsightsDir, sessionFile);
          const sessionContent = await fsPromises.readFile(sessionPath, 'utf-8');
          const sessionData = JSON.parse(sessionContent);

          if (sessionData.session_number !== undefined) {
            memories.push({
              id: `${specDir}-${sessionFile}`,
              type: 'session_insight',
              timestamp: sessionData.timestamp || new Date().toISOString(),
              content: JSON.stringify({
                discoveries: sessionData.discoveries,
                what_worked: sessionData.what_worked,
                what_failed: sessionData.what_failed,
                recommendations: sessionData.recommendations_for_next_session,
                subtasks_completed: sessionData.subtasks_completed
              }, null, 2),
              session_number: sessionData.session_number
            });
          }
        } catch {
          // Skip invalid files
        }
      }
    }

    // Load codebase map
    const codebaseMapPath = path.join(memoryDir, 'codebase_map.json');
    if (await fileExists(codebaseMapPath)) {
      try {
        const mapContent = await fsPromises.readFile(codebaseMapPath, 'utf-8');
        const mapData = JSON.parse(mapContent);
        if (mapData.discovered_files && Object.keys(mapData.discovered_files).length > 0) {
          memories.push({
            id: `${specDir}-codebase_map`,
            type: 'codebase_map',
            timestamp: mapData.last_updated || new Date().toISOString(),
            content: JSON.stringify(mapData.discovered_files, null, 2),
            session_number: undefined
          });
        }
      } catch {
        // Skip invalid files
      }
    }
  }

  return memories.slice(0, limit);
}

/**
 * Search file-based memories for a query
 */
export async function searchFileBasedMemories(
  specsDir: string,
  query: string,
  limit: number
): Promise<ContextSearchResult[]> {
  const results: ContextSearchResult[] = [];
  const queryLower = query.toLowerCase();

  if (!(await fileExists(specsDir))) {
    return results;
  }

  const allFiles = await fsPromises.readdir(specsDir);
  const allSpecDirs: string[] = [];

  for (const f of allFiles) {
    const specPath = path.join(specsDir, f);
    const stat = await fsPromises.stat(specPath);
    if (stat.isDirectory()) {
      allSpecDirs.push(f);
    }
  }

  for (const specDir of allSpecDirs) {
    const memoryDir = path.join(specsDir, specDir, 'memory');
    if (!(await fileExists(memoryDir))) continue;

    const allMemFiles = await fsPromises.readdir(memoryDir);
    const memoryFiles = allMemFiles.filter((f: string) => f.endsWith('.json'));

    for (const memFile of memoryFiles) {
      try {
        const memPath = path.join(memoryDir, memFile);
        const memContent = await fsPromises.readFile(memPath, 'utf-8');

        if (memContent.toLowerCase().includes(queryLower)) {
          const memData = JSON.parse(memContent);
          results.push({
            content: JSON.stringify(memData.insights || memData, null, 2),
            score: 1.0,
            type: 'session_insight'
          });
        }
      } catch {
        // Skip invalid files
      }
    }
  }

  return results.slice(0, limit);
}

/**
 * Register memory data handlers
 */
export function registerMemoryDataHandlers(
  _getMainWindow: () => BrowserWindow | null
): void {
  // Get all memories
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_GET_MEMORIES,
    async (_, projectId: string, limit: number = 20): Promise<IPCResult<MemoryEpisode[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
      const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

      // Try LadybugDB first if available
      if (graphitiEnabled && isKuzuAvailable()) {
        try {
          const dbDetails = getGraphitiDatabaseDetails(projectEnvVars);
          const memoryService = getMemoryService({
            dbPath: dbDetails.dbPath,
            database: dbDetails.database,
          });
          const graphMemories = await memoryService.getEpisodicMemories(limit);
          if (graphMemories.length > 0) {
            return { success: true, data: graphMemories };
          }
        } catch (error) {
          console.warn('Failed to get memories from LadybugDB, falling back to file-based:', error);
        }
      }

      // Fall back to file-based memories
      const specsBaseDir = getSpecsDir(project.autoBuildPath);
      const specsDir = path.join(project.path, specsBaseDir);
      const memories = await loadFileBasedMemories(specsDir, limit);

      return { success: true, data: memories };
    }
  );

  // Search memories
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_SEARCH_MEMORIES,
    async (_, projectId: string, query: string): Promise<IPCResult<ContextSearchResult[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
      const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

      // Try LadybugDB search if available
      if (graphitiEnabled && isKuzuAvailable()) {
        try {
          const dbDetails = getGraphitiDatabaseDetails(projectEnvVars);
          const memoryService = getMemoryService({
            dbPath: dbDetails.dbPath,
            database: dbDetails.database,
          });
          const graphResults = await memoryService.searchMemories(query, 20);
          if (graphResults.length > 0) {
            return {
              success: true,
              data: graphResults.map(r => ({
                content: r.content,
                score: r.score || 1.0,
                type: r.type
              }))
            };
          }
        } catch (error) {
          console.warn('Failed to search LadybugDB, falling back to file-based:', error);
        }
      }

      // Fall back to file-based search
      const specsBaseDir = getSpecsDir(project.autoBuildPath);
      const specsDir = path.join(project.path, specsBaseDir);
      const results = await searchFileBasedMemories(specsDir, query, 20);

      return { success: true, data: results };
    }
  );

  // Get pattern suggestions
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_GET_PATTERN_SUGGESTIONS,
    async (
      _,
      projectId: string,
      query: string,
      categories?: string[],
      numResults: number = 5
    ): Promise<IPCResult<PatternSuggestion[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
      const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

      if (!graphitiEnabled) {
        return {
          success: false,
          error: 'Graphiti memory system is not enabled for this project'
        };
      }

      try {
        // Call Python backend to get pattern suggestions
        const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
        const backendPath = path.join(project.path, 'apps', 'backend');

        // Prepare arguments for pattern_suggester.py
        const args = [
          '-c',
          `
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from integrations.graphiti.pattern_suggester import suggest_patterns
    from integrations.graphiti.queries_pkg.client import get_graphiti_client_sync

    query = ${JSON.stringify(query)}
    categories = ${JSON.stringify(categories || null)}
    num_results = ${numResults}
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

    # Get pattern suggestions
    patterns = await suggest_patterns(
        client=client,
        group_id=group_id,
        spec_context_id="",
        query=query,
        categories=categories,
        num_results=num_results,
        min_score=0.5,
        include_project_context=True,
        project_dir=project_dir
    )

    print(json.dumps({"patterns": patterns}))

asyncio.run(main())
          `.trim()
        ];

        const { promise } = runPythonSubprocess<{ patterns: PatternSuggestion[] }>({
          pythonPath: pythonCommand,
          args: [...baseArgs, ...args],
          cwd: backendPath,
          env: { ...process.env, PYTHONPATH: backendPath }
        });

        const result = await promise;

        if (!result.success) {
          return {
            success: false,
            error: result.error || 'Failed to get pattern suggestions'
          };
        }

        // Parse Python output
        try {
          const lines = result.stdout.split('\n');
          const jsonLine = lines.find(line => line.trim().startsWith('{'));
          if (!jsonLine) {
            return { success: false, error: 'No JSON output from Python script' };
          }

          const data = JSON.parse(jsonLine);
          if (data.error) {
            return { success: false, error: data.error };
          }

          return { success: true, data: data.patterns || [] };
        } catch (parseError) {
          return {
            success: false,
            error: `Failed to parse pattern suggestions: ${parseError}`
          };
        }
      } catch (error) {
        return {
          success: false,
          error: `Failed to get pattern suggestions: ${error}`
        };
      }
    }
  );

  // Confirm pattern (user action)
  ipcMain.handle(
    IPC_CHANNELS.CONTEXT_CONFIRM_PATTERN,
    async (
      _,
      projectId: string,
      pattern: PatternSuggestion,
      action: 'confirmed' | 'rejected' | 'modified',
      modifiedPattern?: string
    ): Promise<IPCResult<void>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
      const graphitiEnabled = isGraphitiEnabled(projectEnvVars);

      if (!graphitiEnabled) {
        return {
          success: false,
          error: 'Graphiti memory system is not enabled for this project'
        };
      }

      try {
        // Call Python backend to record pattern confirmation
        const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
        const backendPath = path.join(project.path, 'apps', 'backend');

        // Prepare arguments to record pattern action
        const args = [
          '-c',
          `
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from integrations.graphiti.queries_pkg.client import get_graphiti_client_sync
    from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_PATTERN

    pattern_data = ${JSON.stringify(pattern)}
    action = ${JSON.stringify(action)}
    modified_pattern = ${JSON.stringify(modifiedPattern || null)}
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

    # Record pattern action as an episode
    episode_content = {
        "type": "pattern_action",
        "action": action,
        "original_pattern": pattern_data["pattern"],
        "category": pattern_data["category"],
        "spec_id": pattern_data.get("spec_id", ""),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    if modified_pattern:
        episode_content["modified_pattern"] = modified_pattern

    await client.graphiti.add_episode(
        name=f"Pattern {action}: {pattern_data['category']}",
        episode_body=json.dumps(episode_content),
        source_description="User pattern confirmation",
        reference_time=datetime.utcnow(),
        group_id=group_id
    )

    print(json.dumps({"success": True}))

asyncio.run(main())
          `.trim()
        ];

        const { promise } = runPythonSubprocess<{ success: boolean }>({
          pythonPath: pythonCommand,
          args: [...baseArgs, ...args],
          cwd: backendPath,
          env: { ...process.env, PYTHONPATH: backendPath }
        });

        const result = await promise;

        if (!result.success) {
          return {
            success: false,
            error: result.error || 'Failed to confirm pattern'
          };
        }

        // Parse Python output
        try {
          const lines = result.stdout.split('\n');
          const jsonLine = lines.find(line => line.trim().startsWith('{'));
          if (!jsonLine) {
            return { success: false, error: 'No JSON output from Python script' };
          }

          const data = JSON.parse(jsonLine);
          if (data.error) {
            return { success: false, error: data.error };
          }

          return { success: true, data: undefined };
        } catch (parseError) {
          return {
            success: false,
            error: `Failed to parse confirmation result: ${parseError}`
          };
        }
      } catch (error) {
        return {
          success: false,
          error: `Failed to confirm pattern: ${error}`
        };
      }
    }
  );

  // ============================================
  // Knowledge Base Configuration Operations
  // ============================================

  /**
   * Parse knowledge base configuration from project environment variables
   */
  const parseKnowledgeBaseConfig = (envVars: Record<string, string>): KnowledgeBaseConfig => {
    const config: KnowledgeBaseConfig = {};

    // Notion
    if (envVars['KNOWLEDGE_BASE_NOTION_API_KEY']) {
      config.notionEnabled = true;
      config.notionApiKey = envVars['KNOWLEDGE_BASE_NOTION_API_KEY'];
    }
    if (envVars['KNOWLEDGE_BASE_NOTION_WORKSPACE_ID']) {
      config.notionWorkspaceId = envVars['KNOWLEDGE_BASE_NOTION_WORKSPACE_ID'];
    }

    // Confluence
    if (envVars['KNOWLEDGE_BASE_CONFLUENCE_API_KEY']) {
      config.confluenceEnabled = true;
      config.confluenceApiKey = envVars['KNOWLEDGE_BASE_CONFLUENCE_API_KEY'];
    }
    if (envVars['KNOWLEDGE_BASE_CONFLUENCE_API_URL']) {
      config.confluenceApiUrl = envVars['KNOWLEDGE_BASE_CONFLUENCE_API_URL'];
    }
    if (envVars['KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY']) {
      config.confluenceSpaceKey = envVars['KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY'];
    }
    if (envVars['KNOWLEDGE_BASE_CONFLUENCE_EMAIL']) {
      config.confluenceEmail = envVars['KNOWLEDGE_BASE_CONFLUENCE_EMAIL'];
    }

    // GitHub Wiki
    if (envVars['KNOWLEDGE_BASE_GITHUB_WIKI_TOKEN']) {
      config.githubWikiEnabled = true;
      config.githubWikiToken = envVars['KNOWLEDGE_BASE_GITHUB_WIKI_TOKEN'];
    }
    if (envVars['KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY']) {
      config.githubWikiRepository = envVars['KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY'];
    }

    // GitBook
    if (envVars['KNOWLEDGE_BASE_GITBOOK_API_KEY']) {
      config.gitbookEnabled = true;
      config.gitbookApiKey = envVars['KNOWLEDGE_BASE_GITBOOK_API_KEY'];
    }
    if (envVars['KNOWLEDGE_BASE_GITBOOK_API_URL']) {
      config.gitbookApiUrl = envVars['KNOWLEDGE_BASE_GITBOOK_API_URL'];
    }

    // Global settings
    if (envVars['KNOWLEDGE_BASE_SYNC_INTERVAL']) {
      const interval = parseInt(envVars['KNOWLEDGE_BASE_SYNC_INTERVAL'], 10);
      if (!isNaN(interval)) {
        config.syncInterval = interval;
      }
    }
    if (envVars['KNOWLEDGE_BASE_MAX_DOCS']) {
      const maxDocs = parseInt(envVars['KNOWLEDGE_BASE_MAX_DOCS'], 10);
      if (!isNaN(maxDocs)) {
        config.maxDocs = maxDocs;
      }
    }

    return config;
  };

  /**
   * Generate .env file content for knowledge base configuration
   */
  const updateKnowledgeBaseEnvVars = (
    envVars: Record<string, string>,
    config: KnowledgeBaseConfig
  ): Record<string, string> => {
    // Notion
    if (config.notionApiKey !== undefined) {
      envVars['KNOWLEDGE_BASE_NOTION_API_KEY'] = config.notionApiKey;
    }
    if (config.notionWorkspaceId !== undefined) {
      envVars['KNOWLEDGE_BASE_NOTION_WORKSPACE_ID'] = config.notionWorkspaceId;
    }

    // Confluence
    if (config.confluenceApiKey !== undefined) {
      envVars['KNOWLEDGE_BASE_CONFLUENCE_API_KEY'] = config.confluenceApiKey;
    }
    if (config.confluenceApiUrl !== undefined) {
      envVars['KNOWLEDGE_BASE_CONFLUENCE_API_URL'] = config.confluenceApiUrl;
    }
    if (config.confluenceSpaceKey !== undefined) {
      envVars['KNOWLEDGE_BASE_CONFLUENCE_SPACE_KEY'] = config.confluenceSpaceKey;
    }
    if (config.confluenceEmail !== undefined) {
      envVars['KNOWLEDGE_BASE_CONFLUENCE_EMAIL'] = config.confluenceEmail;
    }

    // GitHub Wiki
    if (config.githubWikiToken !== undefined) {
      envVars['KNOWLEDGE_BASE_GITHUB_WIKI_TOKEN'] = config.githubWikiToken;
    }
    if (config.githubWikiRepository !== undefined) {
      envVars['KNOWLEDGE_BASE_GITHUB_WIKI_REPOSITORY'] = config.githubWikiRepository;
    }

    // GitBook
    if (config.gitbookApiKey !== undefined) {
      envVars['KNOWLEDGE_BASE_GITBOOK_API_KEY'] = config.gitbookApiKey;
    }
    if (config.gitbookApiUrl !== undefined) {
      envVars['KNOWLEDGE_BASE_GITBOOK_API_URL'] = config.gitbookApiUrl;
    }

    // Global settings
    if (config.syncInterval !== undefined) {
      envVars['KNOWLEDGE_BASE_SYNC_INTERVAL'] = String(config.syncInterval);
    }
    if (config.maxDocs !== undefined) {
      envVars['KNOWLEDGE_BASE_MAX_DOCS'] = String(config.maxDocs);
    }

    return envVars;
  };

  // Get knowledge base configuration
  ipcMain.handle(
    IPC_CHANNELS.KNOWLEDGE_BASE_GET_CONFIG,
    async (_, projectId: string): Promise<IPCResult<KnowledgeBaseConfig>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      if (!project.autoBuildPath) {
        return { success: false, error: 'Project not initialized' };
      }

      try {
        const projectEnvVars = loadProjectEnvVars(project.path, project.autoBuildPath);
        const config = parseKnowledgeBaseConfig(projectEnvVars);

        return { success: true, data: config };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to get knowledge base configuration'
        };
      }
    }
  );

  // Update knowledge base configuration
  ipcMain.handle(
    IPC_CHANNELS.KNOWLEDGE_BASE_UPDATE_CONFIG,
    async (_, projectId: string, config: KnowledgeBaseConfig): Promise<IPCResult<void>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      if (!project.autoBuildPath) {
        return { success: false, error: 'Project not initialized' };
      }

      try {
        const envPath = path.join(project.path, project.autoBuildPath, '.env');

        // Read existing .env file
        let existingContent: string | undefined;
        try {
          existingContent = await fsPromises.readFile(envPath, 'utf-8');
        } catch {
          // File doesn't exist yet, that's okay
        }

        // Parse existing environment variables
        const existingVars = existingContent ? parseEnvFile(existingContent) : {};

        // Update with knowledge base configuration
        const updatedVars = updateKnowledgeBaseEnvVars(existingVars, config);

        // Generate .env content (reuse generateEnvContent from env-handlers pattern)
        const content = Object.entries(updatedVars)
          .map(([key, value]) => `${key}=${value}`)
          .join('\n');

        // Write to file
        await fsPromises.writeFile(envPath, content, 'utf-8');

        return { success: true };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to update knowledge base configuration'
        };
      }
    }
  );

  // Test knowledge base connection
  ipcMain.handle(
    IPC_CHANNELS.KNOWLEDGE_BASE_TEST_CONNECTION,
    async (_, projectId: string, provider: string): Promise<IPCResult<KnowledgeBaseConnectionTest>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      if (!project.autoBuildPath) {
        return { success: false, error: 'Project not initialized' };
      }

      try {
        // Call Python backend to test connection
        const [pythonCommand, baseArgs] = parsePythonCommand(project.path);
        const backendPath = path.join(project.path, 'apps', 'backend');

        // Prepare arguments for knowledge base connection test
        const args = [
          '-c',
          `
import sys
import json
import asyncio
from pathlib import Path
sys.path.insert(0, '${backendPath.replace(/\\/g, '\\\\')}')

async def main():
    from integrations.knowledge_base import get_knowledge_base_manager

    provider = ${JSON.stringify(provider)}
    project_dir = Path('${project.path.replace(/\\/g, '\\\\')}')

    # Get manager (auto-detects provider from env)
    manager = get_knowledge_base_manager(str(project_dir))

    if not manager or not manager.connector:
        print(json.dumps({
            "success": False,
            "provider": provider,
            "message": f"{provider} is not configured"
        }))
        return

    # Test connection
    try:
        await manager.connector.connect()
        # Try fetching a small batch of documents to verify access
        docs = await manager.connector.fetch_documents(limit=1)

        details = {}
        if provider == "notion" and docs:
            details["workspaceName"] = "Notion Workspace"
        elif provider == "confluence" and docs:
            details["spaceName"] = manager.connector.config.space_key
        elif provider == "github_wiki":
            details["repository"] = manager.connector.config.repository
        elif provider == "gitbook":
            details["docsFound"] = len(docs) if docs else 0

        print(json.dumps({
            "success": True,
            "provider": provider,
            "message": f"Successfully connected to {provider}",
            "details": details
        }))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "provider": provider,
            "message": f"Connection failed: {str(e)}",
            "error": str(e)
        }))

asyncio.run(main())
          `.trim()
        ];

        const { promise } = runPythonSubprocess<KnowledgeBaseConnectionTest>({
          pythonPath: pythonCommand,
          args: [...baseArgs, ...args],
          cwd: backendPath,
          env: { ...process.env, PYTHONPATH: backendPath }
        });

        const result = await promise;

        if (!result.success) {
          return {
            success: false,
            error: result.error || 'Failed to test knowledge base connection'
          };
        }

        // Parse Python output
        try {
          const lines = result.stdout.split('\n');
          const jsonLine = lines.find(line => line.trim().startsWith('{'));
          if (!jsonLine) {
            return { success: false, error: 'No JSON output from Python script' };
          }

          const data = JSON.parse(jsonLine);
          return { success: true, data: data };
        } catch (parseError) {
          return {
            success: false,
            error: `Failed to parse connection test result: ${parseError}`
          };
        }
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to test knowledge base connection'
        };
      }
    }
  );
}
