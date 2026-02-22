/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly VITE_API_URL?: string;
	readonly VITE_WS_URL?: string;
	readonly VITE_JWT_SECRET?: string;
	readonly VITE_DEBUG?: string;
	readonly VITE_ENABLE_WEBSOCKET?: string;
	readonly VITE_SENTRY_DSN?: string;
	readonly VITE_SENTRY_TRACES_SAMPLE_RATE?: string;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
