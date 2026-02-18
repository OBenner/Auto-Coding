import i18n from "i18next";
import { initReactI18next } from "react-i18next";

// Import translations
import commonEn from "./locales/en/common.json";

// Initialize i18next for web
i18n
	.use(initReactI18next)
	.init({
		resources: {
			en: {
				common: commonEn,
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
