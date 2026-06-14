import supabase from '../../lib/supabase.js';
import { cors } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const { token } = req.query;
  if (!token) return res.status(400).json({ error: 'Token requis' });

  const { data: link, error } = await supabase
    .from('sharedlink')
    .select('exercise_id, exercisedb (nom, contenu)')
    .eq('token', token)
    .single();

  if (error || !link) return res.status(404).json({ error: 'Lien invalide ou expiré' });

  return res.status(200).json({
    nom: link.exercisedb.nom,
    contenu: link.exercisedb.contenu,
  });
}
