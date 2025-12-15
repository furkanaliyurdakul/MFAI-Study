# Analytics System Setup Guide

This guide explains how to set up the analytics database and access session data from a mobile app or dashboard.

## Overview

The analytics system automatically syncs all session data to Supabase tables, providing real-time access to:
- Session progress and completion status
- Profile survey demographics
- Knowledge test scores and question-level results
- UEQ satisfaction scores
- Learning interaction metrics
- Time spent on each page

## Step 1: Create Database Tables

1. **Log into Supabase Dashboard**
   - Go to https://supabase.com/dashboard
   - Select your project

2. **Run the Schema SQL**
   - Click on "SQL Editor" in the left sidebar
   - Click "New Query"
   - Copy the entire contents of `docs/supabase_analytics_schema.sql`
   - Paste into the query editor
   - Click "Run"

This will create:
- **Tables**: `session_analytics`, `ueq_scores`, `knowledge_test_results`, `learning_interactions`
- **Views**: `completed_sessions`, `session_progress`, `daily_statistics`, `language_comparison`

## Step 2: Verify Integration (Already Done)

The following files have been updated to automatically sync data:

- ✅ `session_manager.py` - Syncs profile, knowledge test, UEQ data
- ✅ `main.py` - Syncs consent and completion status
- ✅ `analytics_syncer.py` - Handles all database operations

**No additional code changes needed!** Data will automatically sync when:
- Session starts (creates record)
- Consent is given
- Profile is submitted
- Knowledge test is completed
- UEQ survey is submitted
- Learning session ends
- Session completes

## Step 3: Access Data

### Option A: Supabase Dashboard (Web)

1. Go to https://supabase.com/dashboard
2. Select your project
3. Click "Table Editor"
4. Select any table/view:
   - `completed_sessions` - See all finished sessions
   - `session_progress` - Monitor active sessions
   - `daily_statistics` - View aggregated daily metrics
   - `language_comparison` - Compare performance across languages

### Option B: Python Script

```python
from supabase import create_client
import streamlit as st

# Initialize client
supabase = create_client(
    st.secrets["supabase"]["url"],
    st.secrets["supabase"]["service_key"]
)

# Get today's completed sessions
result = supabase.table("completed_sessions").select("*").execute()
for session in result.data:
    print(f"{session['user_id']}: {session['knowledge_test_score']}%")

# Get active sessions
result = supabase.table("session_progress").select("*").eq("status", "active").execute()
print(f"{len(result.data)} sessions currently active")

# Get language comparison stats
result = supabase.table("language_comparison").select("*").execute()
for lang in result.data:
    print(f"{lang['language_code']}: avg score {lang['avg_knowledge_score']}%")
```

### Option C: Mobile App (Android/iOS)

You can create a mobile app using:
- **React Native** + Supabase JS SDK
- **Flutter** + Supabase Flutter package
- **Kotlin/Swift** + Supabase REST API

#### Example: React Native

```javascript
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'YOUR_SUPABASE_URL',
  'YOUR_ANON_KEY'
)

// Get completed sessions
const { data, error } = await supabase
  .from('completed_sessions')
  .select('*')
  .order('completed_at', { ascending: false })
  .limit(20)

// Get today's stats
const { data: today } = await supabase
  .from('daily_statistics')
  .select('*')
  .eq('date', new Date().toISOString().split('T')[0])
  .single()
```

#### Example: Flutter

```dart
import 'package:supabase_flutter/supabase_flutter.dart';

// Initialize
await Supabase.initialize(
  url: 'YOUR_SUPABASE_URL',
  anonKey: 'YOUR_ANON_KEY',
);

final supabase = Supabase.instance.client;

// Query completed sessions
final response = await supabase
  .from('completed_sessions')
  .select()
  .order('completed_at', ascending: false)
  .limit(20);
```

## Step 4: Build Mobile App (Optional)

### Quick Start with Expo (React Native)

1. **Install Expo CLI**
   ```bash
   npm install -g expo-cli
   ```

2. **Create New App**
   ```bash
   expo init study-monitor
   cd study-monitor
   npm install @supabase/supabase-js
   ```

3. **Add Supabase Config** (`app.config.js`)
   ```javascript
   export default {
     name: 'Study Monitor',
     extra: {
       supabaseUrl: 'YOUR_URL',
       supabaseAnonKey: 'YOUR_KEY'
     }
   }
   ```

4. **Create Dashboard Screen** (`App.js`)
   ```javascript
   import { useEffect, useState } from 'react'
   import { View, Text, FlatList } from 'react-native'
   import { createClient } from '@supabase/supabase-js'
   import Constants from 'expo-constants'

   const supabase = createClient(
     Constants.expoConfig.extra.supabaseUrl,
     Constants.expoConfig.extra.supabaseAnonKey
   )

   export default function App() {
     const [sessions, setSessions] = useState([])
     const [stats, setStats] = useState(null)

     useEffect(() => {
       fetchData()
     }, [])

     async function fetchData() {
       // Get completed sessions
       const { data: sessions } = await supabase
         .from('completed_sessions')
         .select('*')
         .limit(10)
       setSessions(sessions || [])

       // Get today's stats
       const today = new Date().toISOString().split('T')[0]
       const { data: stats } = await supabase
         .from('daily_statistics')
         .select('*')
         .eq('date', today)
         .single()
       setStats(stats)
     }

     return (
       <View style={{ padding: 20 }}>
         <Text style={{ fontSize: 24, fontWeight: 'bold' }}>
           Study Monitor
         </Text>
         
         {stats && (
           <View style={{ marginVertical: 20 }}>
             <Text>Today: {stats.sessions_completed} completed</Text>
             <Text>Avg Score: {stats.avg_knowledge_score}%</Text>
           </View>
         )}

         <FlatList
           data={sessions}
           keyExtractor={item => item.session_id}
           renderItem={({ item }) => (
             <View style={{ padding: 10, borderBottomWidth: 1 }}>
               <Text>{item.user_id}</Text>
               <Text>Score: {item.knowledge_test_score}%</Text>
               <Text>Language: {item.language_code}</Text>
             </View>
           )}
         />
       </View>
     )
   }
   ```

5. **Run App**
   ```bash
   expo start
   ```
   Scan QR code with Expo Go app on your phone!

### Alternative: Flutter

```bash
flutter create study_monitor
cd study_monitor
flutter pub add supabase_flutter
flutter run
```

## Common Queries

### Get Recent Completions
```sql
SELECT 
  session_id,
  user_id,
  language_code,
  knowledge_test_score,
  completed_at
FROM completed_sessions
ORDER BY completed_at DESC
LIMIT 10;
```

### Monitor Active Sessions
```sql
SELECT 
  session_id,
  user_id,
  current_stage,
  progress_percent,
  minutes_elapsed
FROM session_progress
WHERE status = 'active'
ORDER BY started_at DESC;
```

### Language Performance
```sql
SELECT 
  language_code,
  total_sessions,
  avg_knowledge_score,
  avg_total_minutes
FROM language_comparison
ORDER BY language_code;
```

### Today's Progress
```sql
SELECT *
FROM daily_statistics
WHERE date = CURRENT_DATE;
```

### Individual Session Details
```sql
-- Get full session info
SELECT * FROM session_analytics WHERE session_id = 'YOUR_SESSION_ID';

-- Get UEQ scores
SELECT * FROM ueq_scores WHERE session_id = 'YOUR_SESSION_ID';

-- Get knowledge test details
SELECT * FROM knowledge_test_results WHERE session_id = 'YOUR_SESSION_ID';

-- Get learning interactions
SELECT * FROM learning_interactions WHERE session_id = 'YOUR_SESSION_ID';
```

## Security Notes

- **Use Row Level Security (RLS)** in Supabase to restrict access
- **Never expose service_key** - only use anon_key in mobile apps
- **Set up authentication** for your monitoring app
- **Enable read-only access** for mobile apps

Example RLS policy for read-only access:
```sql
CREATE POLICY "Allow read access to analytics"
ON session_analytics
FOR SELECT
USING (true);  -- Or add authentication check
```

## Troubleshooting

### Data not syncing?
1. Check Supabase credentials in `.streamlit/secrets.toml`
2. Verify tables exist: Go to Supabase > Table Editor
3. Check Python logs for error messages
4. Ensure `service_key` is used (not `anon_key`)

### Mobile app can't connect?
1. Verify `supabaseUrl` and `supabaseAnonKey` are correct
2. Check network connection
3. Enable CORS in Supabase settings
4. Verify RLS policies allow SELECT

### Performance issues?
1. Add indexes on frequently queried columns
2. Use views instead of complex queries
3. Implement pagination (LIMIT/OFFSET)
4. Cache results in mobile app

## Next Steps

1. ✅ Run `supabase_analytics_schema.sql` in Supabase
2. ✅ Test with a complete session (already integrated)
3. 📱 Build mobile app (follow Quick Start above)
4. 📊 Create custom dashboards (Supabase has built-in charts)
5. 📧 Set up email alerts for completed sessions (Supabase Functions)

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [React Native + Supabase](https://supabase.com/docs/guides/with-react-native)
- [Flutter + Supabase](https://supabase.com/docs/guides/with-flutter)
- [Expo Documentation](https://docs.expo.dev/)
