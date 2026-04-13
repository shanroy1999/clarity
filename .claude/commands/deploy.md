---
name: deploy
description: >
  Deploy the Clarity frontend to Vercel. Runs build checks first,
  then deploys. Use when you want to push a new version live.
---

Deploy the Clarity frontend to Vercel.

## Pre-deploy checks
1. cd frontend && npx tsc --noEmit
   If TypeScript errors found, stop and list them.

2. cd frontend && npm run build
   If build fails, stop and show the error.

3. Check that these environment variables are set for Vercel:
   - NEXT_PUBLIC_API_URL (should point to Railway backend)
   - NEXT_PUBLIC_APP_NAME=Clarity

## Deploy
If all checks pass:
  cd frontend && npx vercel --prod

## After deploy
- Show the deployment URL
- Test the health endpoint: curl {url}/api/health
- Confirm the report page loads
