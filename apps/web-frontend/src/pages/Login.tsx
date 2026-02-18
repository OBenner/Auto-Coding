/**
 * Login Page
 *
 * User authentication form for cloud-hosted Auto Code.
 * Handles email/password login and redirects to dashboard.
 */

import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import { login } from "../lib/api";

export function Login() {
	const navigate = useNavigate();
	const [email, setEmail] = useState("");
	const [password, setPassword] = useState("");
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
		e.preventDefault();
		setError(null);

		// Validation
		if (!email || !password) {
			setError("Please fill in all fields");
			return;
		}

		setIsLoading(true);

		try {
			// Call backend login endpoint
			const result = await login(email, password);

			// Store JWT token in localStorage
			localStorage.setItem("token", result.access_token);
			localStorage.setItem("user", JSON.stringify(result.user));

			// Redirect to home page (or dashboard)
			navigate("/");
		} catch (err) {
			setError(err instanceof Error ? err.message : "Login failed");
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
			<div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8">
				{/* Logo */}
				<div className="flex justify-center mb-6">
					<div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
						<span className="text-3xl text-white font-bold">AC</span>
					</div>
				</div>

				{/* Title */}
				<div className="text-center mb-8">
					<h1 className="text-3xl font-bold text-gray-900 mb-2">
						Welcome Back
					</h1>
					<p className="text-gray-600">Sign in to your Auto Code account</p>
				</div>

				{/* Error Message */}
				{error && (
					<div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
						<p className="text-sm text-red-600">{error}</p>
					</div>
				)}

				{/* Login Form */}
				<form onSubmit={handleSubmit} className="space-y-4">
					{/* Email */}
					<div>
						<label
							htmlFor="email"
							className="block text-sm font-medium text-gray-700 mb-2"
						>
							Email Address
						</label>
						<input
							id="email"
							type="email"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							placeholder="you@example.com"
							required
							disabled={isLoading}
						/>
					</div>

					{/* Password */}
					<div>
						<label
							htmlFor="password"
							className="block text-sm font-medium text-gray-700 mb-2"
						>
							Password
						</label>
						<input
							id="password"
							type="password"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
							placeholder="Enter your password"
							required
							disabled={isLoading}
						/>
					</div>

					{/* Forgot Password Link */}
					<div className="flex items-center justify-between">
						<div className="flex items-center">
							<input
								id="remember"
								type="checkbox"
								className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
							/>
							<label
								htmlFor="remember"
								className="ml-2 block text-sm text-gray-700"
							>
								Remember me
							</label>
						</div>
						<a
							href="/forgot-password"
							className="text-sm text-blue-600 hover:text-blue-700"
						>
							Forgot password?
						</a>
					</div>

					{/* Submit Button */}
					<Button type="submit" className="w-full" disabled={isLoading}>
						{isLoading ? "Signing In..." : "Sign In"}
					</Button>
				</form>

				{/* Signup Link */}
				<div className="mt-6 text-center">
					<p className="text-sm text-gray-600">
						Don't have an account?{" "}
						<a
							href="/signup"
							className="text-blue-600 hover:text-blue-700 font-medium"
						>
							Sign Up
						</a>
					</p>
				</div>

				{/* Divider */}
				<div className="mt-6 relative">
					<div className="absolute inset-0 flex items-center">
						<div className="w-full border-t border-gray-200"></div>
					</div>
					<div className="relative flex justify-center text-sm">
						<span className="px-2 bg-white text-gray-500">
							Or continue with
						</span>
					</div>
				</div>

				{/* OAuth Buttons (Placeholder) */}
				<div className="mt-6 grid grid-cols-2 gap-3">
					<Button type="button" variant="outline" disabled className="w-full">
						<svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
							<path
								fill="currentColor"
								d="M12.545,10.239v3.821h5.445c-0.712,2.315-2.647,3.972-5.445,3.972c-3.332,0-6.033-2.701-6.033-6.032s2.701-6.032,6.033-6.032c1.498,0,2.866,0.549,3.921,1.453l2.814-2.814C17.503,2.988,15.139,2,12.545,2C7.021,2,2.543,6.477,2.543,12s4.478,10,10.002,10c8.396,0,10.249-7.85,9.426-11.748L12.545,10.239z"
							/>
						</svg>
						Google
					</Button>
					<Button type="button" variant="outline" disabled className="w-full">
						<svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
							<path
								fill="currentColor"
								d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"
							/>
						</svg>
						GitHub
					</Button>
				</div>
			</div>
		</div>
	);
}
