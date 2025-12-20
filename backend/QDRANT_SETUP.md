# Qdrant Vector Store Setup Guide

This guide walks you through setting up the Qdrant vector store integration for Commander.

## Prerequisites

- Python 3.10+
- OpenAI API key
- Qdrant Cloud account (or local Qdrant instance)

## Step 1: Create Qdrant Cloud Cluster

1. Go to [Qdrant Cloud](https://cloud.qdrant.io/)
2. Sign up for a free account
3. Create a new cluster:
   - Choose **Free tier** (1GB RAM, 4GB disk, ~500k contexts)
   - Select a region close to you
   - Wait for cluster to be provisioned (~2 minutes)
4. Get your credentials:
   - Click on your cluster
   - Copy the **Cluster URL** (e.g., `https://xyz-example.qdrant.io`)
   - Copy the **API Key** from the cluster details

## Step 2: Update Environment Variables

Add these to your `backend/.env` file:

```bash
# Existing
OPENAI_API_KEY=sk-...

# Add these new ones
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key-here
EMBEDDING_MODEL=text-embedding-3-small
MAX_EMBEDDING_TOKENS=8000
```

## Step 3: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

This installs:
- `qdrant-client>=1.7.0` - Qdrant Python client
- `tiktoken>=0.5.0` - Token counting for embeddings

## Step 4: Initialize Qdrant Collection

Run the initialization script:

```bash
python -m backend.init_qdrant
```

Expected output:
```
======================================================================
Commander - Qdrant Collection Initialization
======================================================================

Checking configuration...
✓ Qdrant URL: https://your-cluster.qdrant.io
✓ Collection name: commander_contexts
✓ Embedding model: text-embedding-3-small
✓ Max embedding tokens: 8000

Testing connection to Qdrant...
✓ Successfully connected to Qdrant
  Found 0 existing collection(s)

Creating collection 'commander_contexts'...
Collection 'commander_contexts' created successfully
✓ Collection ready

Collection information:
  Name: commander_contexts
  Status: green
  Vector size: 1536
  Distance metric: Cosine
  Points count: 0
  Vectors count: 0

======================================================================
✓ Initialization complete!
...
======================================================================
```

## Step 5: Start the Backend Server

```bash
uvicorn backend.api:app --reload
```

## Step 6: Test the Integration

### Test 1: Ingest Contexts

Send a POST request to `/run` to ingest and process contexts:

```bash
curl -X POST "http://localhost:8000/run?limit=5&source=all"
```

This will:
1. Fetch contexts from mocked sources (Gmail, Slack, etc.)
2. Generate embeddings for each context
3. Store contexts + embeddings in Qdrant
4. Search for similar + recent contexts
5. Pass relevant history to LLM for action decisions
6. Save proposed actions to JSON

### Test 2: Similarity Search

Test the similarity search endpoint:

```bash
curl -X POST http://localhost:8000/api/contexts/similar \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Can we schedule a meeting to discuss the project?",
    "limit": 5
  }'
```

Expected response:
```json
{
  "results": [
    {
      "id": "ctx-123",
      "source_type": "gmail",
      "sender": "john@example.com",
      "summary": "Meeting request for Q4 planning",
      "context_text": "Hey team, let's schedule...",
      "timestamp": "2025-12-18T10:30:00Z",
      "similarity_score": 0.89
    },
    ...
  ],
  "count": 5
}
```

The results are ordered by similarity score (highest first).

### Test 3: Verify LLM Gets Relevant History

1. Ingest some contexts with similar content
2. Check the server logs when processing a new context
3. You should see the LLM prompt includes:
   - `=== RELEVANT HISTORY (similar + recent contexts) ===`
   - Semantically similar contexts appear first
   - Recent contexts appear after

Example log output:
```
=== RELEVANT HISTORY (similar + recent contexts) ===

[Context 1 - similar to current]
From: john@example.com
Subject: Project meeting
...
----- ACTIONS TAKEN -----
  - schedule_meeting: Q4 Planning (status: executed, confidence: 0.85)

[Context 2 - recent]
From: sarah@example.com
Subject: Daily standup notes
...
----- ACTIONS TAKEN -----
None

=== END HISTORY ===

=== CURRENT INPUT (decide actions for this) ===
[New context being processed]
```

## Troubleshooting

### "QDRANT_URL is not set"
- Make sure you've added `QDRANT_URL` to `backend/.env`
- Restart your terminal/IDE after updating `.env`

### "Failed to connect to Qdrant"
- Verify your cluster URL is correct (should start with `https://`)
- Check that your API key is valid
- Ensure your cluster is active (not suspended)

### "Maximum context length exceeded"
- This shouldn't happen with the truncation logic
- If it does, the text will be automatically truncated to 8,000 tokens
- Check logs for truncation messages

### Slow embedding generation
- First request is slower due to cold start
- Subsequent requests use cached OpenAI client
- Batch operations are more efficient (implemented in `generate_embeddings_batch`)

### High embedding costs
- text-embedding-3-small costs ~$0.02 per 1M tokens
- For 100 contexts/day at 300 tokens each: ~$0.02/month
- Monitor usage in OpenAI dashboard

## Architecture Overview

```
Ingest Flow:
  Gmail/Slack → Adapter → Context
                            ↓
  Embeddings Service ← context_text
      (truncate if > 8k tokens)
                            ↓
  Qdrant ← upsert(context + embedding)
                            ↓
  Similarity Search → get relevant history
                            ↓
  LLM (with history) → decide actions
                            ↓
  JSON Storage ← save actions
```

## Key Files

- `backend/embeddings.py` - Embedding generation, token counting, truncation
- `backend/vector_store.py` - Qdrant client wrapper, collection management
- `backend/context_storage.py` - Context CRUD + semantic search
- `backend/storage.py` - Action storage (JSON-based, unchanged)
- `backend/orchestrator.py` - Main processing loop
- `backend/api.py` - API endpoints including `/api/contexts/similar`
- `backend/init_qdrant.py` - One-time setup script

## Performance Notes

- **Point lookups**: ~10-50ms
- **Similarity search**: ~50-200ms
- **Embedding generation**: ~100-500ms (depends on text length)
- **End-to-end context ingestion**: ~500-1000ms

The free tier handles ~500-600 operations/day easily, which is well above your expected usage (~82 contexts/day).

## Migration from JSON

If you have existing contexts in `data/contexts.json`:
- They will NOT be automatically migrated
- Only new contexts going forward will be embedded and stored in Qdrant
- Old actions in `data/actions.json` remain accessible (no changes to action storage)

To manually migrate old contexts, you could create a script that:
1. Reads from `data/contexts.json`
2. Generates embeddings for each
3. Inserts into Qdrant

But this is optional - starting fresh is fine!

## What's Next?

- Monitor embedding costs in OpenAI dashboard
- Adjust `semantic_limit` and `recent_limit` in `get_relevant_history()` if needed
- Tune similarity score threshold if results aren't relevant enough
- Scale up Qdrant cluster when you exceed free tier limits

## Support

If you encounter issues:
1. Check Qdrant Cloud dashboard for cluster status
2. Review server logs for detailed error messages
3. Verify all environment variables are set correctly
4. Test connection with `python -m backend.init_qdrant`


