import i18n from "i18next";
import { initReactI18next } from "react-i18next";

// Import translations
import commonEn from "./locales/en/common.json";
import navigationEn from "./locales/en/navigation.json";
import tasksEn from "./locales/en/tasks.json";
import settingsEn from "./locales/en/settings.json";
import dialogsEn from "./locales/en/dialogs.json";
import errorsEn from "./locales/en/errors.json";

// Initialize i18next for web
i18n
	.use(initReactI18next)
	.init({
		resources: {
			en: {
				common: commonEn,
				navigation: navigationEn,
				tasks: tasksEn,
				settings: settingsEn,
				dialogs: dialogsEn,
				errors: errorsEn,
			},
		},
		lng: "en",
		fallbackLng: "en",
		defaultNS: "common",
		interpolation: {
			escapeValue: false, // React already escapes values
		},
	})
	.catch((err) => {
		console.error("[i18n] Initialization failed:", err);
	});

export default i18n;
