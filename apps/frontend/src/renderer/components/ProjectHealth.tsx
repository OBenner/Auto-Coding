import { HealthDashboard } from './project-health/HealthDashboard';

interface ProjectHealthProps {
  projectId: string;
}

export function ProjectHealth({ projectId }: ProjectHealthProps) {
  return <HealthDashboard projectId={projectId} />;
}
