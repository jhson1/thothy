"use client";

import React, {
    createContext,
    useContext,
    useState,
    useEffect,
    ReactNode,
    useCallback,
} from "react";
import { User, Session } from "@supabase/supabase-js";
import { createClient } from "@/utils/supabase/client";
import { useRouter, usePathname } from "next/navigation";

const STORAGE_KEY = "thothy_auth_state";

interface AuthContextType {
    user: User | null;
    session: Session | null;
    signIn: () => Promise<void>;
    signUp: () => Promise<void>;
    signOut: () => Promise<void>;
    loading: boolean;
    supabase: any;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper function to save auth state to localStorage
const saveAuthState = (user: User | null, session: Session | null) => {
    if (typeof window !== "undefined") {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ user, session }));
    }
};

// Helper function to load auth state from localStorage
const loadAuthState = () => {
    if (typeof window !== "undefined") {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            try {
                return JSON.parse(stored);
            } catch (error) {
                console.error("Error parsing stored auth state:", error);
                return null;
            }
        }
    }
    return null;
};

// Helper function to fetch session from API
async function fetchSessionFromApi() {
    try {
        const res = await fetch('/api/auth/session');
        const { session } = await res.json();
        return session;
    } catch (error) {
        console.error('Error fetching session from API:', error);
        return null;
    }
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [session, setSession] = useState<Session | null>(null);
    const [loading, setLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();
    const supabase = createClient();

    useEffect(() => {
        // Initialize session from localStorage to prevent flash of unauthenticated state
        const storedState = loadAuthState();
        if (storedState) {
            setUser(storedState.user);
            setSession(storedState.session);
        }

        // Check for active session and get user
        const initializeAuth = async () => {
            setLoading(true);
            try {
                // First check if there's an active session
                const { data: { session }, error: sessionError } = await supabase.auth.getSession();
                
                if (sessionError) {
                    // Handle session errors gracefully
                    console.warn("Session error:", sessionError);
                    setSession(null);
                    setUser(null);
                    localStorage.removeItem(STORAGE_KEY);
                    return;
                }

                if (session?.user) {
                    // Only try to get user if we have a valid session
                    const { data: { user: supabaseUser }, error: userError } = await supabase.auth.getUser();
                    
                    if (userError) {
                        // Handle cases where session exists but getUser fails
                        console.warn("User fetch error:", userError);
                        setSession(null);
                        setUser(null);
                        localStorage.removeItem(STORAGE_KEY);
                        return;
                    }

                    if (supabaseUser) {
                        // Extract user metadata from Google OAuth
                        const userMetadata = supabaseUser.user_metadata || {};
                        // Update user with Google profile information
                        const updatedUser = {
                            ...supabaseUser,
                            user_metadata: {
                                ...userMetadata,
                                full_name:
                                    userMetadata?.full_name ||
                                    userMetadata?.name ||
                                    supabaseUser.email,
                                avatar_url:
                                    userMetadata?.avatar_url ||
                                    userMetadata?.picture,
                            },
                        };
                        setSession(session);
                        setUser(updatedUser);
                        saveAuthState(updatedUser, session);
                    } else {
                        setSession(null);
                        setUser(null);
                        localStorage.removeItem(STORAGE_KEY);
                    }
                } else {
                    // No session or user, clear everything
                    setSession(null);
                    setUser(null);
                    localStorage.removeItem(STORAGE_KEY);
                    // If on a protected path, redirect to login
                    const protectedPaths = ['/team', '/find', '/inbox', '/staff', '/blog'];
                    if (protectedPaths.some(path => pathname?.startsWith(path))) {
                        router.push(`/auth/login?redirectTo=${encodeURIComponent(pathname || '/')}`);
                    }
                }
            } catch (error) {
                // Handle any unexpected errors gracefully
                console.error("Error initializing auth:", error);
                setSession(null);
                setUser(null);
                localStorage.removeItem(STORAGE_KEY);
            } finally {
                setLoading(false);
            }
        };

        initializeAuth();

        // Set up auth state change listener (this handles token refreshes)
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            async (event, currentSession) => {
                if (currentSession?.user) {
                    // Extract user metadata from Google OAuth
                    const userMetadata = currentSession.user.user_metadata || {};

                    // Update user with Google profile information
                    const updatedUser = {
                        ...currentSession.user,
                        user_metadata: {
                            ...userMetadata,
                            full_name:
                                userMetadata?.full_name ||
                                userMetadata?.name ||
                                currentSession.user.email,
                            avatar_url:
                                userMetadata?.avatar_url ||
                                userMetadata?.picture,
                        },
                    };

                    setSession(currentSession);
                    setUser(updatedUser);
                    saveAuthState(updatedUser, currentSession);

                    // If there's a redirectTo parameter, navigate there
                    const params = new URLSearchParams(window.location.search);
                    const redirectTo = params.get('redirectTo');
                    if (redirectTo && window.location.pathname.startsWith('/auth')) {
                        router.push(redirectTo);
                    }
                } else if (event === 'SIGNED_OUT') {
                    setSession(null);
                    setUser(null);
                    localStorage.removeItem(STORAGE_KEY);
                    router.push('/auth/login');
                }
            }
        );

        // Clean up subscription when component unmounts
        return () => {
            subscription.unsubscribe();
        };
    }, [pathname]);

    // Rehydrate session from API on every route change if missing
    useEffect(() => {
        const checkSession = async () => {
            if (!session) {
                const apiSession = await fetchSessionFromApi();
                if (apiSession) {
                    setSession(apiSession);
                    setUser(apiSession.user);
                    saveAuthState(apiSession.user, apiSession);
                }
            }
        };
        checkSession();
    }, [pathname, session]);

    const signIn = useCallback(async () => {
        try {
            // Get the redirectTo parameter from the URL if it exists
            const searchParams = new URLSearchParams(window.location.search);
            const redirectTo = searchParams.get('redirectTo') || '/';
            
            // Redirect to the sign-in API endpoint with the redirectTo parameter
            window.location.href = `/api/auth/signin?provider=google&redirectTo=${encodeURIComponent(redirectTo)}`;
        } catch (error) {
            console.error("Error signing in:", error);
        }
    }, []);

    const signUp = useCallback(async () => {
        try {
            const response = await fetch("/api/auth/signup", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (!response.ok) {
                throw new Error("Sign up failed");
            }

            const data = await response.json();
            setSession(data.session);
            setUser(data.user);
            saveAuthState(data.user, data.session);
        } catch (error) {
            console.error("Error signing up:", error);
            throw error;
        }
    }, []);

    const signOut = useCallback(async () => {
        try {
            // Use Supabase's signOut method which properly handles tokens
            const { error } = await supabase.auth.signOut();
            if (error && error.message !== "Auth session missing!") {
                // Only throw error if it's not about missing session (which is expected during logout)
                console.warn("Sign out error:", error);
            }
            
            // Also call the API to clear server-side cookies
            try {
                await fetch("/api/auth/signout", {
                    method: "POST",
                });
            } catch (apiError) {
                console.warn("Error clearing server-side cookies:", apiError);
                // Don't throw here, we still want to complete the logout
            }

            // Always clear local state regardless of API errors
            setSession(null);
            setUser(null);
            localStorage.removeItem(STORAGE_KEY);
        } catch (error) {
            console.error("Error signing out:", error);
            // Even if sign out fails, clear local state to ensure user is logged out
            setSession(null);
            setUser(null);
            localStorage.removeItem(STORAGE_KEY);
            // Don't throw the error - we want logout to always succeed from UI perspective
        }
    }, [supabase.auth]);

    return (
        <AuthContext.Provider
            value={{
                user,
                session,
                signIn,
                signUp,
                signOut,
                loading,
                supabase,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
