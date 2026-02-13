/**
 * Settings Page
 *
 * Main settings page with tabs for different configuration sections.
 * Includes Git connections, Account settings, and Usage & Billing.
 */

import { useState } from "react";
import { GitHubConnect } from "../components/GitHubConnect";
import { Button } from "../components/ui/button";
import {
	Card,
	CardContent,
	CardHeader,
	CardTitle,
} from "../components/ui/card";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Separator } from "../components/ui/separator";
import { Switch } from "../components/ui/switch";

type SettingsTab = "git" | "account" | "usage";

interface NotificationSettings {
	emailEnabled: boolean;
	pushEnabled: boolean;
	taskComplete: boolean;
	agentFailure: boolean;
	securityAlerts: boolean;
}

interface Preferences {
	theme: "light" | "dark" | "system";
	language: string;
	autoSave: boolean;
	autoSync: boolean;
}

export function Settings() {
	const [activeTab, setActiveTab] = useState<SettingsTab>("git");

	// Account settings state
	const [profileName, setProfileName] = useState("User");
	const [profileEmail, setProfileEmail] = useState("user@example.com");
	const [apiKey, setApiKey] = useState("");
	const [showApiKey, setShowApiKey] = useState(false);

	// Preferences state
	const [preferences, setPreferences] = useState<Preferences>({
		theme: "system",
		language: "en",
		autoSave: true,
		autoSync: true,
	});

	// Notifications state
	const [notifications, setNotifications] = useState<NotificationSettings>({
		emailEnabled: true,
		pushEnabled: true,
		taskComplete: true,
		agentFailure: true,
		securityAlerts: true,
	});

	const tabs: { id: SettingsTab; label: string; icon: string }[] = [
		{ id: "git", label: "Git Connections", icon: "🔗" },
		{ id: "account", label: "Account", icon: "👤" },
		{ id: "usage", label: "Usage & Billing", icon: "📊" },
	];

	const handleSaveProfile = () => {
		// TODO: Implement save to backend
		console.log("Saving profile:", { profileName, profileEmail, apiKey });
	};

	const handleSavePreferences = () => {
		// TODO: Implement save to backend
		console.log("Saving preferences:", preferences);
	};

	const handleSaveNotifications = () => {
		// TODO: Implement save to backend
		console.log("Saving notifications:", notifications);
	};

	return (
		<div className="min-h-screen bg-gray-50">
			{/* Header */}
			<div className="bg-white border-b border-gray-200">
				<div className="max-w-6xl mx-auto px-4 py-6">
					<div className="flex items-center justify-between">
						<div>
							<h1 className="text-3xl font-bold text-gray-900">Settings</h1>
							<p className="text-gray-600 mt-1">
								Manage your account and preferences
							</p>
						</div>
						<a
							href="/"
							className="text-blue-600 hover:text-blue-700 font-medium text-sm"
						>
							← Back to Home
						</a>
					</div>
				</div>
			</div>

			{/* Content */}
			<div className="max-w-6xl mx-auto px-4 py-8">
				<div className="grid grid-cols-1 md:grid-cols-4 gap-6">
					{/* Sidebar Navigation */}
					<div className="md:col-span-1">
						<nav className="space-y-1">
							{tabs.map((tab) => (
								<button
									key={tab.id}
									onClick={() => setActiveTab(tab.id)}
									className={`w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition-colors ${
										activeTab === tab.id
											? "bg-blue-50 text-blue-700 font-medium"
											: "text-gray-700 hover:bg-gray-100"
									}`}
								>
									<span className="text-xl">{tab.icon}</span>
									<span className="text-sm">{tab.label}</span>
								</button>
							))}
						</nav>
					</div>

					{/* Main Content */}
					<div className="md:col-span-3">
						{activeTab === "git" && (
							<div className="space-y-6">
								<div>
									<h2 className="text-xl font-semibold text-gray-900 mb-2">
										Git Connections
									</h2>
									<p className="text-gray-600 text-sm mb-6">
										Connect your GitHub or GitLab account to access repositories
									</p>
								</div>

								{/* GitHub Connection */}
								<GitHubConnect />

								{/* GitLab Connection (Placeholder) */}
								<Card className="opacity-60">
									<CardContent className="p-6">
										<div className="flex items-center gap-4">
											<div className="w-12 h-12 bg-orange-500 rounded-lg flex items-center justify-center shrink-0">
												<svg
													className="w-7 h-7 text-white"
													viewBox="0 0 24 24"
													fill="currentColor"
												>
													<path d="M23.955 13.587l-1.342-4.135-2.664-8.189a.455.455 0 00-.867 0L16.418 9.45H7.582L4.918 1.263a.455.455 0 00-.867 0L1.387 9.452.045 13.587a.924.924 0 00.331 1.023l11.359 8.251a.455.455 0 00.53 0l11.359-8.251a.924.924 0 00.331-1.023z" />
												</svg>
											</div>
											<div className="flex-1 min-w-0">
												<h3 className="text-lg font-semibold text-gray-900">
													GitLab
												</h3>
												<p className="text-sm text-gray-600">
													GitLab integration coming soon
												</p>
											</div>
											<span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 shrink-0">
												<span className="w-2 h-2 rounded-full bg-gray-400"></span>
												Coming Soon
											</span>
										</div>
									</CardContent>
								</Card>
							</div>
						)}

						{activeTab === "account" && (
							<div className="space-y-6">
								{/* Profile Section */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">Profile</CardTitle>
									</CardHeader>
									<CardContent className="space-y-4">
										<div className="space-y-2">
											<Label htmlFor="profileName">Display Name</Label>
											<Input
												id="profileName"
												value={profileName}
												onChange={(e) => setProfileName(e.target.value)}
												placeholder="Your display name"
											/>
										</div>
										<div className="space-y-2">
											<Label htmlFor="profileEmail">Email Address</Label>
											<Input
												id="profileEmail"
												type="email"
												value={profileEmail}
												onChange={(e) => setProfileEmail(e.target.value)}
												placeholder="your.email@example.com"
											/>
										</div>
										<div className="flex justify-end">
											<Button onClick={handleSaveProfile}>Save Profile</Button>
										</div>
									</CardContent>
								</Card>

								{/* API Keys Section */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">API Keys</CardTitle>
									</CardHeader>
									<CardContent className="space-y-4">
										<div className="space-y-2">
											<Label htmlFor="apiKey">Claude API Key</Label>
											<div className="flex gap-2">
												<Input
													id="apiKey"
													type={showApiKey ? "text" : "password"}
													value={apiKey}
													onChange={(e) => setApiKey(e.target.value)}
													placeholder="sk-ant-..."
													className="flex-1 font-mono"
												/>
												<Button
													variant="outline"
													onClick={() => setShowApiKey(!showApiKey)}
													type="button"
												>
													{showApiKey ? "Hide" : "Show"}
												</Button>
											</div>
											<p className="text-xs text-gray-500">
												Your API key is stored securely and used for agent
												operations.
											</p>
										</div>
										<div className="flex justify-end">
											<Button onClick={handleSaveProfile}>
												Update API Key
											</Button>
										</div>
									</CardContent>
								</Card>

								{/* Preferences Section */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">Preferences</CardTitle>
									</CardHeader>
									<CardContent className="space-y-6">
										{/* Theme Selection */}
										<div className="space-y-3">
											<Label>Theme</Label>
											<div className="flex gap-2">
												{(["light", "dark", "system"] as const).map(
													(themeOption) => (
														<button
															key={themeOption}
															onClick={() =>
																setPreferences({
																	...preferences,
																	theme: themeOption,
																})
															}
															className={`px-4 py-2 rounded-lg border-2 transition-colors capitalize ${
																preferences.theme === themeOption
																	? "border-blue-500 bg-blue-50 text-blue-700"
																	: "border-gray-200 hover:border-gray-300"
															}`}
														>
															{themeOption}
														</button>
													),
												)}
											</div>
										</div>

										{/* Language Selection */}
										<div className="space-y-2">
											<Label htmlFor="language">Language</Label>
											<select
												id="language"
												value={preferences.language}
												onChange={(e) =>
													setPreferences({
														...preferences,
														language: e.target.value,
													})
												}
												className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
											>
												<option value="en">English</option>
												<option value="fr">Français</option>
												<option value="es">Español</option>
												<option value="de">Deutsch</option>
												<option value="ja">日本語</option>
											</select>
										</div>

										{/* Auto-save Toggle */}
										<div className="flex items-center justify-between">
											<div className="space-y-1">
												<Label htmlFor="autoSave">Auto-save</Label>
												<p className="text-xs text-gray-500">
													Automatically save changes as you work
												</p>
											</div>
											<Switch
												id="autoSave"
												checked={preferences.autoSave}
												onCheckedChange={(checked) =>
													setPreferences({ ...preferences, autoSave: checked })
												}
											/>
										</div>

										{/* Auto-sync Toggle */}
										<div className="flex items-center justify-between">
											<div className="space-y-1">
												<Label htmlFor="autoSync">Auto-sync</Label>
												<p className="text-xs text-gray-500">
													Automatically sync with remote repositories
												</p>
											</div>
											<Switch
												id="autoSync"
												checked={preferences.autoSync}
												onCheckedChange={(checked) =>
													setPreferences({ ...preferences, autoSync: checked })
												}
											/>
										</div>

										<Separator />

										<div className="flex justify-end">
											<Button onClick={handleSavePreferences}>
												Save Preferences
											</Button>
										</div>
									</CardContent>
								</Card>
							</div>
						)}

						{activeTab === "usage" && (
							<div className="space-y-6">
								{/* Usage Stats */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">Current Usage</CardTitle>
									</CardHeader>
									<CardContent>
										<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
											<div className="text-center">
												<p className="text-3xl font-bold text-blue-600">847</p>
												<p className="text-sm text-gray-600 mt-1">
													API Requests Today
												</p>
											</div>
											<div className="text-center">
												<p className="text-3xl font-bold text-green-600">
													12.4K
												</p>
												<p className="text-sm text-gray-600 mt-1">
													Tokens Used This Week
												</p>
											</div>
											<div className="text-center">
												<p className="text-3xl font-bold text-purple-600">23</p>
												<p className="text-sm text-gray-600 mt-1">
													Tasks Completed
												</p>
											</div>
										</div>
									</CardContent>
								</Card>

								{/* Usage Limits */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">Usage Limits</CardTitle>
									</CardHeader>
									<CardContent className="space-y-6">
										<div className="space-y-2">
											<div className="flex items-center justify-between text-sm">
												<span className="text-gray-700">
													Daily API Requests
												</span>
												<span className="font-medium">847 / 1,000</span>
											</div>
											<div className="w-full bg-gray-200 rounded-full h-2">
												<div
													className="bg-blue-600 h-2 rounded-full"
													style={{ width: "84.7%" }}
												></div>
											</div>
											<p className="text-xs text-gray-500">Resets in 5 hours</p>
										</div>

										<div className="space-y-2">
											<div className="flex items-center justify-between text-sm">
												<span className="text-gray-700">
													Weekly Token Limit
												</span>
												<span className="font-medium">12.4K / 50K</span>
											</div>
											<div className="w-full bg-gray-200 rounded-full h-2">
												<div
													className="bg-green-600 h-2 rounded-full"
													style={{ width: "24.8%" }}
												></div>
											</div>
											<p className="text-xs text-gray-500">Resets in 3 days</p>
										</div>

										<Separator />

										<div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
											<h4 className="font-medium text-blue-900 mb-2">
												Pro Plan Available
											</h4>
											<p className="text-sm text-blue-700 mb-3">
												Upgrade to Pro for higher limits and priority support.
											</p>
											<Button className="w-full">Upgrade to Pro</Button>
										</div>
									</CardContent>
								</Card>

								{/* Billing Info */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">Billing</CardTitle>
									</CardHeader>
									<CardContent className="space-y-4">
										<div className="flex items-center justify-between py-3 border-b border-gray-100">
											<div>
												<p className="font-medium text-gray-900">Free Plan</p>
												<p className="text-sm text-gray-500">
													Basic access with standard limits
												</p>
											</div>
											<span className="text-lg font-semibold text-gray-900">
												$0/mo
											</span>
										</div>

										<div className="flex items-center justify-between py-3">
											<div>
												<p className="font-medium text-gray-900">Pro Plan</p>
												<p className="text-sm text-gray-500">
													Higher limits, priority support
												</p>
											</div>
											<span className="text-lg font-semibold text-blue-600">
												$29/mo
											</span>
										</div>

										<Separator />

										<div className="flex gap-3">
											<Button variant="outline" className="flex-1">
												View Invoices
											</Button>
											<Button variant="outline" className="flex-1">
												Payment Methods
											</Button>
										</div>
									</CardContent>
								</Card>

								{/* Notification Settings */}
								<Card>
									<CardHeader>
										<CardTitle className="text-xl">Notifications</CardTitle>
									</CardHeader>
									<CardContent className="space-y-6">
										<div className="flex items-center justify-between">
											<div className="space-y-1">
												<Label htmlFor="emailEnabled">
													Email Notifications
												</Label>
												<p className="text-xs text-gray-500">
													Receive updates via email
												</p>
											</div>
											<Switch
												id="emailEnabled"
												checked={notifications.emailEnabled}
												onCheckedChange={(checked) =>
													setNotifications({
														...notifications,
														emailEnabled: checked,
													})
												}
											/>
										</div>

										<div className="flex items-center justify-between">
											<div className="space-y-1">
												<Label htmlFor="pushEnabled">Push Notifications</Label>
												<p className="text-xs text-gray-500">
													Browser push notifications
												</p>
											</div>
											<Switch
												id="pushEnabled"
												checked={notifications.pushEnabled}
												onCheckedChange={(checked) =>
													setNotifications({
														...notifications,
														pushEnabled: checked,
													})
												}
											/>
										</div>

										<Separator />

										<div className="space-y-3">
											<p className="text-sm font-medium text-gray-700">
												Notify me when:
											</p>
											<div className="space-y-3">
												{[
													{ key: "taskComplete", label: "Task completes" },
													{
														key: "agentFailure",
														label: "Agent encounters an error",
													},
													{ key: "securityAlerts", label: "Security alerts" },
												].map(({ key, label }) => (
													<div
														key={key}
														className="flex items-center justify-between"
													>
														<span className="text-sm text-gray-700">
															{label}
														</span>
														<Switch
															checked={
																notifications[
																	key as keyof NotificationSettings
																] as boolean
															}
															onCheckedChange={(checked) =>
																setNotifications({
																	...notifications,
																	[key]: checked,
																})
															}
														/>
													</div>
												))}
											</div>
										</div>

										<Separator />

										<div className="flex justify-end">
											<Button onClick={handleSaveNotifications}>
												Save Notifications
											</Button>
										</div>
									</CardContent>
								</Card>
							</div>
						)}
					</div>
				</div>
			</div>
		</div>
	);
}
