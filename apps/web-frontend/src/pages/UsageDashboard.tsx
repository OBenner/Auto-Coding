/**
 * Usage Dashboard Page
 *
 * Displays API usage statistics and analytics for cloud-hosted Auto Code.
 * Shows request counts, usage trends, and quota information.
 */

import { useEffect, useState } from "react";
import {
	CartesianGrid,
	Line,
	LineChart,
	ResponsiveContainer,
	Tooltip,
	XAxis,
	YAxis,
} from "recharts";

interface UsagePeriodStats {
	period: string;
	total_requests: number;
	metrics: Record<string, unknown>;
}

interface UsageStatsData {
	user_id: number | null;
	period: string;
	days_back: number;
	usage_data: UsagePeriodStats[];
	total_requests: number;
	redis_healthy: boolean;
}

interface DashboardData {
	total_requests_today: number;
	total_requests_this_month: number;
	redis_healthy: boolean;
}

export function UsageDashboard() {
	const [isLoading, setIsLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [dashboardData, setDashboardData] = useState<DashboardData | null>(
		null,
	);
	const [statsData, setStatsData] = useState<UsageStatsData | null>(null);
	const [period, setPeriod] = useState<"hourly" | "daily" | "monthly">("daily");
	const [daysBack, setDaysBack] = useState(7);

	const fetchDashboardData = async () => {
		try {
			const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
			const response = await fetch(`${apiUrl}/api/usage/dashboard?user_id=1`);

			if (!response.ok) {
				throw new Error("Failed to fetch dashboard data");
			}

			const data = await response.json();
			setDashboardData(data);
		} catch (err) {
			console.error("Error fetching dashboard data:", err);
			setError(
				err instanceof Error ? err.message : "Failed to load dashboard data",
			);
		}
	};

	const fetchStatsData = async () => {
		try {
			const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
			const response = await fetch(
				`${apiUrl}/api/usage/stats?user_id=1&period=${period}&days_back=${daysBack}`,
			);

			if (!response.ok) {
				throw new Error("Failed to fetch usage statistics");
			}

			const data = await response.json();
			setStatsData(data);
		} catch (err) {
			console.error("Error fetching stats data:", err);
			setError(
				err instanceof Error ? err.message : "Failed to load usage statistics",
			);
		}
	};

	useEffect(() => {
		const loadData = async () => {
			setIsLoading(true);
			setError(null);

			await Promise.all([fetchDashboardData(), fetchStatsData()]);

			setIsLoading(false);
		};

		loadData();
	}, [period, daysBack]);

	// Format chart data
	const chartData =
		statsData?.usage_data.map((item) => ({
			date: item.period,
			requests: item.total_requests,
		})) || [];

	return (
		<div className="min-h-screen bg-gray-50">
			{/* Header */}
			<div className="bg-white border-b border-gray-200">
				<div className="max-w-7xl mx-auto px-4 py-6">
					<div className="flex items-center justify-between">
						<div>
							<h1 className="text-3xl font-bold text-gray-900">
								Usage Dashboard
							</h1>
							<p className="text-gray-600 mt-1">
								Monitor your API usage and track consumption
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
			<div className="max-w-7xl mx-auto px-4 py-8">
				{/* Error State */}
				{error && (
					<div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
						<p className="text-sm text-red-600">{error}</p>
					</div>
				)}

				{/* Loading State */}
				{isLoading ? (
					<div className="flex items-center justify-center py-12">
						<div className="text-center">
							<div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
							<p className="text-gray-600">Loading usage data...</p>
						</div>
					</div>
				) : (
					<div className="space-y-6">
						{/* Summary Cards */}
						<div className="grid grid-cols-1 md:grid-cols-3 gap-6">
							{/* Today's Requests */}
							<div className="bg-white rounded-lg shadow-md p-6">
								<div className="flex items-center justify-between">
									<div>
										<p className="text-sm font-medium text-gray-600 mb-1">
											Requests Today
										</p>
										<p className="text-3xl font-bold text-gray-900">
											{dashboardData?.total_requests_today?.toLocaleString() ||
												"0"}
										</p>
									</div>
									<div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
										<span className="text-2xl">📊</span>
									</div>
								</div>
							</div>

							{/* Monthly Requests */}
							<div className="bg-white rounded-lg shadow-md p-6">
								<div className="flex items-center justify-between">
									<div>
										<p className="text-sm font-medium text-gray-600 mb-1">
											Requests This Month
										</p>
										<p className="text-3xl font-bold text-gray-900">
											{dashboardData?.total_requests_this_month?.toLocaleString() ||
												"0"}
										</p>
									</div>
									<div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center">
										<span className="text-2xl">📈</span>
									</div>
								</div>
							</div>

							{/* Total Requests */}
							<div className="bg-white rounded-lg shadow-md p-6">
								<div className="flex items-center justify-between">
									<div>
										<p className="text-sm font-medium text-gray-600 mb-1">
											Total Requests
										</p>
										<p className="text-3xl font-bold text-gray-900">
											{statsData?.total_requests?.toLocaleString() || "0"}
										</p>
										<p className="text-xs text-gray-500 mt-1">
											Last {daysBack} days
										</p>
									</div>
									<div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
										<span className="text-2xl">✨</span>
									</div>
								</div>
							</div>
						</div>

						{/* System Status */}
						<div className="bg-white rounded-lg shadow-md p-6">
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-3">
									<span className="text-lg">⚡</span>
									<div>
										<h3 className="text-sm font-semibold text-gray-900">
											System Status
										</h3>
										<p className="text-xs text-gray-600">
											Usage tracking service
										</p>
									</div>
								</div>
								<span
									className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
										dashboardData?.redis_healthy
											? "bg-green-100 text-green-700"
											: "bg-red-100 text-red-700"
									}`}
								>
									<span
										className={`w-2 h-2 rounded-full ${
											dashboardData?.redis_healthy
												? "bg-green-500"
												: "bg-red-500"
										}`}
									></span>
									{dashboardData?.redis_healthy ? "Healthy" : "Degraded"}
								</span>
							</div>
						</div>

						{/* Usage Chart */}
						<div className="bg-white rounded-lg shadow-md p-6">
							<div className="mb-6">
								<div className="flex items-center justify-between mb-4">
									<h2 className="text-xl font-semibold text-gray-900">
										Usage Trends
									</h2>

									{/* Chart Controls */}
									<div className="flex items-center gap-4">
										{/* Period Selector */}
										<select
											value={period}
											onChange={(e) =>
												setPeriod(
													e.target.value as "hourly" | "daily" | "monthly",
												)
											}
											className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="hourly">Hourly</option>
											<option value="daily">Daily</option>
											<option value="monthly">Monthly</option>
										</select>

										{/* Days Back Selector */}
										<select
											value={daysBack}
											onChange={(e) => setDaysBack(Number(e.target.value))}
											className="px-3 py-1.5 text-sm border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
										>
											<option value="7">Last 7 days</option>
											<option value="14">Last 14 days</option>
											<option value="30">Last 30 days</option>
											<option value="90">Last 90 days</option>
										</select>
									</div>
								</div>

								{/* Chart */}
								{chartData.length > 0 ? (
									<ResponsiveContainer width="100%" height={300}>
										<LineChart data={chartData}>
											<CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
											<XAxis
												dataKey="date"
												stroke="#6b7280"
												fontSize={12}
												tickLine={false}
											/>
											<YAxis
												stroke="#6b7280"
												fontSize={12}
												tickLine={false}
												axisLine={false}
											/>
											<Tooltip
												contentStyle={{
													backgroundColor: "white",
													border: "1px solid #e5e7eb",
													borderRadius: "8px",
													padding: "8px 12px",
												}}
												labelStyle={{ color: "#374151", fontWeight: 600 }}
											/>
											<Line
												type="monotone"
												dataKey="requests"
												stroke="#3b82f6"
												strokeWidth={2}
												dot={{ fill: "#3b82f6", r: 4 }}
												activeDot={{ r: 6 }}
											/>
										</LineChart>
									</ResponsiveContainer>
								) : (
									<div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
										<div className="text-center">
											<span className="text-4xl mb-2 block">📊</span>
											<p className="text-gray-600">No usage data available</p>
											<p className="text-sm text-gray-500 mt-1">
												Start making API requests to see usage trends
											</p>
										</div>
									</div>
								)}
							</div>
						</div>

						{/* Usage Details Table */}
						{chartData.length > 0 && (
							<div className="bg-white rounded-lg shadow-md p-6">
								<h2 className="text-xl font-semibold text-gray-900 mb-4">
									Usage Details
								</h2>
								<div className="overflow-x-auto">
									<table className="min-w-full divide-y divide-gray-200">
										<thead>
											<tr>
												<th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
													Period
												</th>
												<th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
													Requests
												</th>
											</tr>
										</thead>
										<tbody className="bg-white divide-y divide-gray-200">
											{chartData.map((item, index) => (
												<tr key={index} className="hover:bg-gray-50">
													<td className="px-4 py-3 text-sm text-gray-900">
														{item.date}
													</td>
													<td className="px-4 py-3 text-sm text-gray-900 text-right font-medium">
														{item.requests.toLocaleString()}
													</td>
												</tr>
											))}
										</tbody>
									</table>
								</div>
							</div>
						)}
					</div>
				)}
			</div>
		</div>
	);
}
