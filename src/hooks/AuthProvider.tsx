
import React, { useEffect, useState } from 'react';
import { User, Session } from '@supabase/supabase-js';
import { supabase } from '@/integrations/supabase/client';
import { AuthContext } from '@/hooks/auth-context';
import { DEV_MOCK_USER, clearDevAuthBypass, resolveDevAuthBypass } from '@/hooks/dev-auth-bypass';

export const AuthProvider = ({ children }: { children: React.ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [devBypassActive, setDevBypassActive] = useState(false);

  useEffect(() => {
    if (resolveDevAuthBypass()) {
      console.info(
        '%c🔓 Dev auth bypass active — signed in as a mock user, no real Supabase session. Add ?devauth=0 to the URL to disable.',
        'color: #b45309; font-weight: bold;'
      );
      setDevBypassActive(true);
      setUser(DEV_MOCK_USER);
      setSession(null);
      setLoading(false);
      return;
    }

    // Set up auth state listener
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        setSession(session);
        setUser(session?.user ?? null);
        setLoading(false);
      }
    );

    // Check for existing session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    return { error };
  };

  const signUp = async (email: string, password: string) => {
    const redirectUrl = `${window.location.origin}/dashboard`;

    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: redirectUrl
      }
    });
    return { error };
  };

  const signOut = async () => {
    if (devBypassActive) {
      clearDevAuthBypass();
      setDevBypassActive(false);
      setUser(null);
      setSession(null);
      return;
    }
    await supabase.auth.signOut();
  };

  const value = {
    user,
    session,
    signIn,
    signUp,
    signOut,
    loading,
    devBypassActive,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
