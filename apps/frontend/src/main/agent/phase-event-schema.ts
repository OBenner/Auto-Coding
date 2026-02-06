import { z } from 'zod';
import { BACKEND_PHASES } from '../../shared/constants/phase-protocol';

const BackendPhaseSchema = z.enum(BACKEND_PHASES as unknown as [string, ...string[]]);

const ResourceMetricsSchema = z.object({
  cpu_percent: z.number().optional(),
  memory_mb: z.number().optional(),
  memory_percent: z.number().optional(),
  elapsed_seconds: z.number().optional()
}).optional();

export const PhaseEventSchema = z.object({
  phase: BackendPhaseSchema,
  message: z.string().default(''),
  progress: z.number().int().min(0).max(100).optional(),
  subtask: z.string().optional(),
  resources: ResourceMetricsSchema
});

export type PhaseEventPayload = z.infer<typeof PhaseEventSchema>;

export interface ValidationResult {
  success: true;
  data: PhaseEventPayload;
}

export interface ValidationError {
  success: false;
  error: z.ZodError;
}

export type ParseResult = ValidationResult | ValidationError;

export function validatePhaseEvent(data: unknown): ParseResult {
  const result = PhaseEventSchema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data as PhaseEventPayload };
  }
  return { success: false, error: result.error };
}

export function isValidPhasePayload(data: unknown): data is PhaseEventPayload {
  return PhaseEventSchema.safeParse(data).success;
}
