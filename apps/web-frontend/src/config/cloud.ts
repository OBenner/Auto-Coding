/**
 * Cloud Configuration
 *
 * Detects and manages cloud mode settings.
 * Cloud mode is enabled when the API URL is a remote server (not localhost).
 */

/**
 * Determines if the app is running in cloud mode
 * Cloud mode is detected when:
 * - VITE_CLOUD_MODE is explicitly set to 'true'
 * - API URL points to a remote server (not localhost/127.0.0.1)
 */
export function isCloudMode(): boolean {
	// Check explicit cloud mode flag
	const explicitMode = import.meta.env.VITE_CLOUD_MODE;
	if (explicitMode === "true" || explicitMode === "1") {
		return true;
	}
	if (explicitMode === "false" || explicitMode === "0") {
		return false;
	}

	// Auto-detect from API URL
	const apiUrl = import.meta.env.VITE_API_URL || "";

	// Empty API URL = local mode (no backend configured)
	if (!apiUrl) {
		return false;
	}

	// Check if URL points to localhost or local IP
	const isLocalHost =
		apiUrl.includes("localhost") ||
		apiUrl.includes("127.0.0.1") ||
		apiUrl.includes("0.0.0.0") ||
		apiUrl.includes("::1");

	// Cloud mode if NOT local
	return !isLocalHost;
}

/**
 * Get the cloud configuration
 */
export interface CloudConfig {
	isCloud: boolean;
	apiUrl: string;
	wsUrl: string;
	mode: "local" | "cloud";
}

export function getCloudConfig(): CloudConfig {
	const isCloud = isCloudMode();
	const apiUrl = import.meta.env.VITE_API_URL || "Not configured";
	const wsUrl = import.meta.env.VITE_WS_URL || "Not configured";

	return {
		isCloud,
		apiUrl,
		wsUrl,
		mode: isCloud ? "cloud" : "local",
	};
}

/**
 * Get display-friendly cloud status
 */
export function getCloudStatus(): {
	label: string;
	color: string;
	emoji: string;
} {
	const config = getCloudConfig();

	if (config.isCloud) {
		return {
			label: "Cloud Mode",
			color: "text-green-600",
			emoji: "☁️",
		};
	}

	return {
		label: "Local Mode",
		color: "text-blue-600",
		emoji: "💻",
	};
}
