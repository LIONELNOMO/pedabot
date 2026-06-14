import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ error: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user) return res.status(401).json({ error: 'Non authentifié' });

  const { id } = req.query;
  if (!id) return res.status(400).json({ error: 'ID requis' });

  const { data: assignment, error } = await supabase
    .from('assignment')
    .select(`
      id, statut, created_at,
      exercisedb (id, nom, contenu)
    `)
    .eq('id', id)
    .eq('eleve_id', user.sub)
    .single();

  if (error || !assignment) return res.status(404).json({ error: 'Exercice introuvable' });

  return res.status(200).json({
    assignment_id: assignment.id,
    statut: assignment.statut,
    created_at: assignment.created_at,
    exercise_id: assignment.exercisedb.id,
    nom: assignment.exercisedb.nom,
    contenu: assignment.exercisedb.contenu,
  });
}
