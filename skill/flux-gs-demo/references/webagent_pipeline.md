# WebAgent Pipeline

Use this reference when wiring Flux-GS into a WebAgent framework. For `Personal-digital-assistant---A-Web-Agent`, use the copyable adapter in `integrations/personal-digital-assistant/`.

## Stages

1. Intake
   - Accept a dataset upload, local dataset path, or object-store URI.
   - Assign a stable `job_id` and sanitized `scene_name`.
   - Store the dataset under a server-controlled workspace.

2. Validation
   - Call `validate_flux_gs_dataset` in PDA, or `validate_dataset.py <dataset_path> --json` in the standalone server.
   - If invalid, return `errors`, `warnings`, and `next_actions` to the AI agent.
   - The AI agent should explain exactly which files are missing or malformed and ask the user to upload/fix only those items.

3. Training
   - Start training only after validation passes.
   - Run from `training/`.
   - Use a durable job queue or background worker; do not block the HTTP request, Agent loop, or channel callback.
   - Capture logs, status, start time, end time, GPU id, and model output path.

4. Output Check
   - Require `training/output/<scene_name>/comp.json`.
   - Optionally run `render.py --decode` for offline quality checking.

5. Web Publishing
   - Call `publish_web_demo.py`.
   - Serve the `web/` directory through Nginx, Caddy, a static file server, or the WebAgent host.
   - Return the final URL, for example `https://server.example.com/flux-gs/render_my_scene/`.

## Agent Behavior

The AI should be strict about data validity and gentle about repair guidance:

- If `images/` is missing, ask the user to upload the image folder.
- If `sparse/0/` is missing, explain that COLMAP/SfM reconstruction is required.
- If COLMAP files exist but image filenames do not match, ask for the matching undistorted images.
- If validation passes with warnings, explain the risk and offer to continue.

## Server Notes

- Never run training directly inside the chat request handler.
- In PDA, register `create_flux_gs_demo` through `ToolSpec` and call an independent HTTP Provider.
- Use an allowlisted workspace path for uploads.
- Sanitize `scene_name` to lowercase letters, numbers, `_`, and `-`.
- Keep datasets and training outputs out of Git.
- Configure a GPU worker timeout and expose logs to the WebAgent.
