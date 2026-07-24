import { createBrowserClient } from '@supabase/ssr'

// Create one browser client for the lifetime of the application. Supabase
// persists the session and refreshes access tokens through this client.
const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY!
)

export function createClient() {
  return supabase
}

export { supabase }
