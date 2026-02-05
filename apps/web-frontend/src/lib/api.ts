/**
 * API Client for Auto Claude Web Frontend
 *
 * Provides functions to interact with the backend API for user authentication
 * and account management.
 */

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Response type for user registration
 */
export interface SignupResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    is_active: boolean;
    is_verified: boolean;
    created_at: string;
  };
}

/**
 * Response type for user login
 */
export interface LoginResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
    is_active: boolean;
    is_verified: boolean;
    created_at: string;
  };
}

/**
 * Sign up a new user
 *
 * @param email - User email address
 * @param password - User password (min 8 characters)
 * @param organization - Optional organization name
 * @returns SignupResponse with access token and user data
 * @throws Error if signup fails
 */
export async function signup(
  email: string,
  password: string,
  organization?: string
): Promise<SignupResponse> {
  const response = await fetch(`${API_URL}/api/users/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, organization })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Signup failed' }));
    throw new Error(error.detail || 'Signup failed');
  }

  return response.json();
}

/**
 * Log in an existing user
 *
 * @param email - User email address
 * @param password - User password
 * @returns LoginResponse with access token and user data
 * @throws Error if login fails
 */
export async function login(
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await fetch(`${API_URL}/api/users/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }));
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
}
