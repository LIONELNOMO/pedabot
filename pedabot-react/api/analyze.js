import { analyzeCourse } from '../lib/engine.js';
import { cors } from '../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' });

  const { courseText, text } = req.body || {};
  const payload = courseText ?? text;
  if (!payload || typeof payload !== 'string' || !payload.trim())
    return res.status(400).json({ detail: 'Texte requis' });

  try {
    const result = await analyzeCourse(payload);
    return res.status(200).json(result);
  } catch (e) {
    return res.status(500).json({ detail: 'Erreur analyse du cours' });
  }
}
