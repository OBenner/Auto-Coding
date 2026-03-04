/**
 * Shared Page State Components
 *
 * Reusable loading and error state components for full-page states.
 * Used across TaskList, Kanban, GitOperations, Roadmap, and Changelog pages.
 */

import { AlertCircle, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Button } from "./ui/button";

/**
 * Full-page loading spinner state
 */
export function PageLoadingState() {
	const { t } = useTranslation(["common"]);

	return (
		<div className="min-h-screen bg-gray-50 flex items-center justify-center">
			<div className="text-center">
				<div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4" />
				<p className="text-gray-600">{t("common:loading")}</p>
			</div>
		</div>
	);
}

/**
 * Full-page error state with retry button
 */
export function PageErrorState({
	error,
	onRetry,
}: {
	error: string;
	onRetry: () => void;
}) {
	const { t } = useTranslation(["common"]);

	return (
		<div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
			<div className="text-center max-w-md">
				<AlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
				<h2 className="text-xl font-semibold text-gray-900 mb-2">
					{t("common:error")}
				</h2>
				<p className="text-gray-600 mb-4">{error}</p>
				<Button onClick={onRetry}>
					<RefreshCw className="h-4 w-4 mr-2" />
					Try Again
				</Button>
			</div>
		</div>
	);
}
