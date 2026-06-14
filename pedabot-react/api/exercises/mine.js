import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ error: 'Accès réservé aux professeurs' });

  const { data: exercises, error } = await supabase
    .from('exercisedb')
    .select(`
      id, nom, contenu, created_at,
      sharedlink (token),
      submission (count)
    `)
    .eq('prof_id', user.sub)
    .order('created_at', { ascending: false });

  if (error) return res.status(500).json({ error: 'Erreur récupération exercices' });

  const result = exercises.map(ex => ({
    id: ex.id,
    nom: ex.nom,
    contenu: ex.contenu,
    created_at: ex.created_at,
    token: ex.sharedlink?.[0]?.token ?? null,
    nb_soumissions: ex.submission?.[0]?.count ?? 0,
  }));

  return res.status(200).json(result);
}
