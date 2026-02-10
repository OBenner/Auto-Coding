/**
 * CreateSpec Page
 *
 * Page for creating new specifications in the web frontend.
 * Integrates the SpecForm component and handles navigation after submission.
 */

import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft } from 'lucide-react';
import { SpecForm, type SpecFormData } from '../components/SpecForm';
import { Button } from '../components/ui/button';
import { useSpecStore } from '../store/spec-store';
import { apiClient } from '../api/client';

export function CreateSpec() {
  const { t } = useTranslation(['common', 'navigation', 'dialogs']);
  const navigate = useNavigate();
  const { refreshSpecs } = useSpecStore();

  /**
   * Handle form submission
   * Creates a new spec and navigates to the tasks list
   */
  const handleSubmit = useCallback(async (data: SpecFormData) => {
    try {
      // TODO: Update this when the actual spec creation endpoint is available
      // For now, we'll call the agent run endpoint with the task description
      // This will need to be adjusted based on the actual API design
      await apiClient.runAgent({
        spec_id: data.taskDescription,
        agent_type: 'planner'
      });

      // Refresh the specs list to show the newly created spec
      await refreshSpecs();

      // Navigate to the tasks list to show the new spec
      navigate('/tasks');
    } catch (error) {
      // Error is handled by SpecForm component
      throw error;
    }
  }, [navigate, refreshSpecs]);

  /**
   * Handle cancel button
   * Navigates back to the tasks list
   */
  const handleCancel = useCallback(() => {
    navigate('/tasks');
  }, [navigate]);

  /**
   * Handle navigate back
   */
  const handleBack = useCallback(() => {
    navigate('/tasks');
  }, [navigate]);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto p-6">
        {/* Header */}
        <div className="mb-6">
          <Button
            onClick={handleBack}
            variant="ghost"
            className="mb-4 -ml-2"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common:actions.back')}
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {t('navigation:items.createSpec')}
            </h1>
            <p className="text-sm text-gray-600 mt-1">
              {t('dialogs:createSpec.description')}
            </p>
          </div>
        </div>

        {/* Form */}
        <SpecForm
          onSubmit={handleSubmit}
          onCancel={handleCancel}
        />
      </div>
    </div>
  );
}
