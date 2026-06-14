import supabase from '../../../lib/supabase.js';
import { cors, requireAuth } from '../../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ error: 'Accès réservé aux professeurs' });

  const { token } = req.query;
  if (!token) return res.status(400).json({ error: 'Token requis' });

  const { data: link, error: linkErr } = await supabase
    .from('sharedlink')
    .select('exercise_id')
    .eq('token', token)
    .eq('prof_id', user.sub)
    .single();

  if (linkErr || !link) return res.status(404).json({ error: 'Lien introuvable' });

  const { data: subs, error } = await supabase
    .from('submission')
    .select('id, nom_eleve, reponse, created_at')
    .eq('exercise_id', link.exercise_id)
    .order('created_at', { ascending: false });

  if (error) return res.status(500).json({ error: 'Erreur récupération soumissions' });

  return res.status(200).json(subs);
}
