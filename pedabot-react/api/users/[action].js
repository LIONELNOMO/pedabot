import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ detail: 'Accès réservé aux professeurs' });

  const { action } = req.query;

  if (action === 'eleves') {
    const { data, error } = await supabase
      .from('user')
      .select('id, email, nom, created_at')
      .eq('role', 'eleve')
      .order('nom', { ascending: true });

    if (error) return res.status(500).json({ detail: 'Erreur récupération élèves' });

    return res.status(200).json(data ?? []);
  }

  return res.status(404).json({ detail: 'Action inconnue' });
}
