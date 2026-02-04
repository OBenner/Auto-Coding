import { useCallback, useMemo } from 'react';
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  Panel
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Database, Brain, Info } from 'lucide-react';
import { Card } from '../ui/card';
import { Badge } from '../ui/badge';
import type { GraphNode, GraphEdge } from '../../../shared/types';

interface MemoryGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Custom node styling based on node type
const getNodeStyle = (type: 'episodic' | 'entity') => {
  if (type === 'episodic') {
    return {
      background: 'hsl(var(--accent) / 0.1)',
      border: '2px solid hsl(var(--accent) / 0.3)',
      color: 'hsl(var(--foreground))',
      borderRadius: '8px',
      padding: '10px 15px',
      fontSize: '12px',
      fontWeight: 500
    };
  }
  return {
    background: 'hsl(var(--primary) / 0.1)',
    border: '2px solid hsl(var(--primary) / 0.3)',
    color: 'hsl(var(--foreground))',
    borderRadius: '8px',
    padding: '10px 15px',
    fontSize: '12px',
    fontWeight: 500
  };
};

// Transform GraphNode to ReactFlow Node
function transformNodes(graphNodes: GraphNode[]): Node[] {
  return graphNodes.map((node, index) => {
    const style = getNodeStyle(node.type);

    // Create a simple layout (grid-based for now)
    const col = index % 5;
    const row = Math.floor(index / 5);

    return {
      id: node.id,
      type: 'default',
      position: { x: col * 250, y: row * 150 },
      data: {
        label: (
          <div className="flex items-center gap-2">
            {node.type === 'episodic' ? (
              <Brain className="h-3 w-3" />
            ) : (
              <Database className="h-3 w-3" />
            )}
            <span className="truncate max-w-[150px]" title={node.label}>
              {node.label}
            </span>
          </div>
        )
      },
      style
    };
  });
}

// Transform GraphEdge to ReactFlow Edge
function transformEdges(graphEdges: GraphEdge[]): Edge[] {
  return graphEdges.map((edge) => ({
    id: edge.id,
    source: edge.source,
    target: edge.target,
    type: 'smoothstep',
    animated: true,
    style: { stroke: 'hsl(var(--muted-foreground) / 0.3)', strokeWidth: 2 },
    label: edge.type,
    labelStyle: {
      fill: 'hsl(var(--muted-foreground))',
      fontSize: 10,
      fontWeight: 500
    }
  }));
}

export function MemoryGraph({ nodes: graphNodes, edges: graphEdges }: MemoryGraphProps) {
  // Transform graph data to ReactFlow format
  const initialNodes = useMemo(() => transformNodes(graphNodes), [graphNodes]);
  const initialEdges = useMemo(() => transformEdges(graphEdges), [graphEdges]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update nodes and edges when graph data changes
  useMemo(() => {
    setNodes(transformNodes(graphNodes));
    setEdges(transformEdges(graphEdges));
  }, [graphNodes, graphEdges, setNodes, setEdges]);

  const onInit = useCallback(() => {
    // Auto-fit view on initialization
    // Note: fitView is handled by ReactFlow internally
  }, []);

  // Empty state
  if (graphNodes.length === 0) {
    return (
      <Card className="bg-muted/30 border-border/50 flex items-center justify-center h-[500px]">
        <div className="text-center text-muted-foreground space-y-2">
          <Database className="h-12 w-12 mx-auto opacity-50" />
          <p className="text-sm">No graph data available</p>
          <p className="text-xs">Memory nodes will appear here as they are created</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="bg-muted/30 border-border/50 h-[500px] overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onInit={onInit}
        connectionMode={ConnectionMode.Loose}
        fitView
        attributionPosition="bottom-left"
        minZoom={0.1}
        maxZoom={2}
      >
        <Background
          color="hsl(var(--muted-foreground) / 0.1)"
          gap={16}
        />
        <Controls
          showInteractive={false}
          style={{
            button: {
              backgroundColor: 'hsl(var(--background))',
              border: '1px solid hsl(var(--border))',
              color: 'hsl(var(--foreground))'
            }
          }}
        />
        <MiniMap
          nodeColor={(node) => {
            const graphNode = graphNodes.find(gn => gn.id === node.id);
            return graphNode?.type === 'episodic'
              ? 'hsl(var(--accent))'
              : 'hsl(var(--primary))';
          }}
          maskColor="hsl(var(--background) / 0.8)"
          style={{
            backgroundColor: 'hsl(var(--muted))',
            border: '1px solid hsl(var(--border))'
          }}
        />
        <Panel position="top-right" className="bg-background/80 backdrop-blur-sm border border-border rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2 text-xs">
            <Info className="h-3 w-3 text-muted-foreground" />
            <span className="text-muted-foreground font-medium">Legend</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Brain className="h-3 w-3 text-accent" />
            <Badge variant="outline" className="bg-accent/10 text-accent border-accent/30 text-xs">
              Episodic
            </Badge>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Database className="h-3 w-3 text-primary" />
            <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 text-xs">
              Entity
            </Badge>
          </div>
        </Panel>
      </ReactFlow>
    </Card>
  );
}
