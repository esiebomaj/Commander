-- Commander Database Schema for Supabase
-- Run this in the Supabase SQL Editor

-- ============================================================================
-- PROFILES TABLE
-- Extended user profile (auth.users is managed by Supabase)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    email TEXT,
    full_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-create profile on user signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.email,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on signup
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- ACTIONS TABLE
-- Stores proposed actions (replaces actions.json)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.actions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    context_id TEXT NOT NULL,
    type TEXT NOT NULL,
    payload JSONB DEFAULT '{}'::jsonb,
    confidence FLOAT DEFAULT 0.5,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'executed', 'skipped', 'error')),
    source_type TEXT NOT NULL,
    sender TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for common queries
CREATE INDEX IF NOT EXISTS idx_actions_user_id ON public.actions(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_status ON public.actions(status);
CREATE INDEX IF NOT EXISTS idx_actions_context_id ON public.actions(context_id);
CREATE INDEX IF NOT EXISTS idx_actions_created_at ON public.actions(created_at DESC);

-- ============================================================================
-- INTEGRATION TOKENS TABLE
-- Stores OAuth tokens per user per service (replaces tokens.json)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.integration_tokens (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    service TEXT NOT NULL,
    token_data JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, service)
);

-- Index for lookups
CREATE INDEX IF NOT EXISTS idx_integration_tokens_user_service ON public.integration_tokens(user_id, service);

-- ============================================================================
-- PUSH SUBSCRIPTIONS TABLE
-- Stores web push subscriptions per user (replaces push_subscriptions.json)
-- ============================================================================
CREATE TABLE IF NOT EXISTS public.push_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES auth.users ON DELETE CASCADE NOT NULL,
    endpoint TEXT NOT NULL UNIQUE,
    keys JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for user lookups
CREATE INDEX IF NOT EXISTS idx_push_subscriptions_user_id ON public.push_subscriptions(user_id);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS)
-- Users can only access their own data
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.integration_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.push_subscriptions ENABLE ROW LEVEL SECURITY;

-- Profiles policies
CREATE POLICY "Users can view own profile" 
    ON public.profiles FOR SELECT 
    USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" 
    ON public.profiles FOR UPDATE 
    USING (auth.uid() = id);

-- Actions policies
CREATE POLICY "Users can view own actions" 
    ON public.actions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own actions" 
    ON public.actions FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own actions" 
    ON public.actions FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own actions" 
    ON public.actions FOR DELETE 
    USING (auth.uid() = user_id);

-- Integration tokens policies
CREATE POLICY "Users can view own tokens" 
    ON public.integration_tokens FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tokens" 
    ON public.integration_tokens FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tokens" 
    ON public.integration_tokens FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tokens" 
    ON public.integration_tokens FOR DELETE 
    USING (auth.uid() = user_id);

-- Push subscriptions policies
CREATE POLICY "Users can view own subscriptions" 
    ON public.push_subscriptions FOR SELECT 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own subscriptions" 
    ON public.push_subscriptions FOR INSERT 
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own subscriptions" 
    ON public.push_subscriptions FOR UPDATE 
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own subscriptions" 
    ON public.push_subscriptions FOR DELETE 
    USING (auth.uid() = user_id);


-- Add webhook data column to integration tokens table
ALTER TABLE public.integration_tokens 
ADD COLUMN IF NOT EXISTS webhook_data JSONB DEFAULT '{}'::jsonb;

-- Index for webhook email lookups
CREATE INDEX IF NOT EXISTS idx_integration_tokens_webhook_email 
ON public.integration_tokens ((webhook_data->>'email'))
WHERE service = 'gmail';


-- Add result column to actions table
ALTER TABLE public.actions 
ADD COLUMN IF NOT EXISTS result JSONB DEFAULT '{}'::jsonb;