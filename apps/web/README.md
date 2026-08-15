# React UI source

The immediately runnable Wave 1 demo UI is served by FastAPI from `apps/api/app/static/` so the product can be demonstrated without a Node build step.

This directory is reserved for the production split React/Vite UI. The first deployment can remain single-container while the interaction model stabilizes; splitting the frontend is an optimization, not a prerequisite for student value.
