import supabase from '../lib/supabase.js';
import { cors, requireAuth } from '../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user || user.role !== 'eleve') return res.status(403).json({ error: 'Accès réservé aux élèves' });

  const { data: assignments, error } = await supabase
    .from('assignment')
    .select(`
      id, statut, created_at,
      exercisedb (id, nom, contenu)
    `)
    .eq('eleve_id', user.sub)
    .order('created_at', { ascending: false });

  if (error) return res.status(500).json({ error: 'Erreur récupération exercices' });

  const result = assignments.map(a => ({
    assignment_id: a.id,
    statut: a.statut,
    created_at: a.created_at,
    exercise_id: a.exercisedb.id,
    nom: a.exercisedb.nom,
    contenu: a.exercisedb.contenu,
  }));

  return res.status(200).json(result);
}
