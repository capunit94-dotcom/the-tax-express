/**
 * Cloudflare Pages Function — Tax Express Update Trigger
 * URL: https://the-tax-express.pages.dev/api/update?k=txe2026
 *
 * cron-job.org (free tier) hits this URL via GET every 3 hours.
 * This function then calls the GitHub API to dispatch the workflow.
 */

export async function onRequest(context) {
  const url    = new URL(context.request.url);
  const key    = url.searchParams.get('k');
  const SECRET = 'txe2026';

  // Basic key check — prevents random people from triggering updates
  if (key !== SECRET) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  // GitHub token — must be set as a Cloudflare Pages environment variable
  // Dashboard: Pages > the-tax-express > Settings > Environment variables
  // Variable name: GITHUB_TOKEN
  const token = context.env?.GITHUB_TOKEN;
  if (!token) {
    return new Response(JSON.stringify({ error: 'GITHUB_TOKEN env var not configured' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  try {
    const resp = await fetch(
      'https://api.github.com/repos/capunit94-dotcom/the-tax-express/actions/workflows/daily-update.yml/dispatches',
      {
        method: 'POST',
        headers: {
          'Authorization':  `Bearer ${token}`,
          'Accept':         'application/vnd.github.v3+json',
          'Content-Type':   'application/json',
          'User-Agent':     'TaxExpress-CronTrigger/1.0',
        },
        body: JSON.stringify({ ref: 'main' }),
      }
    );

    if (resp.status === 204) {
      return new Response(JSON.stringify({
        success: true,
        message: 'GitHub Actions workflow dispatched successfully',
        time:    new Date().toISOString(),
      }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = await resp.text();
    return new Response(JSON.stringify({
      success: false,
      github_status: resp.status,
      github_response: body,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });

  } catch (err) {
    return new Response(JSON.stringify({
      success: false,
      error: err.message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
