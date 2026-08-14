import { createContext } from 'react';
import { AuthError, User, Session } from '@supabase/supabase-js';

export interface AuthContextType {
  user: User | null;
  session: Session | null;
  signIn: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signUp: (email: string, password: string) => Promise<{ error: AuthError | null }>;
  signOut: () => Promise<void>;
  loading: boolean;
  /** True when `useAuth()` is returning the dev-only mock user instead of a real Supabase session. Always false in production builds. */
  devBypassActive: boolean;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
