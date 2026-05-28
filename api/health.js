export default async function handler(req, res) {
  const required = [
    'ANTHROPIC_API_KEY',
    'SUPABASE_URL',
    'SUPABASE_SERVICE_KEY',
    'RESEND_API_KEY',
    'WEBHOOK_SECRET'
  ];

  const missing = required.filter((key) => !process.env[key]);

  res.status(missing.length ? 500 : 200).json({
    ok: missing.length === 0,
    service: 'benfit-autoflow',
    checkedAt: new Date().toISOString(),
    missing
  });
}
