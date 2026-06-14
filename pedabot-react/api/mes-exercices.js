import supabase from '../lib/supabase.js';
import { cors, requireAuth } from '../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user) return res.status(401).json({ detail: 'Non authentifié' });

  const { data: rows, error } = await supabase
    .from('assignment')
    .select('id, titre, teacher_nom, lang, difficulty, submitted_at, created_at')
    .eq('eleve_email', String(user.email).toLowerCase().trim())
    .order('created_at', { ascending: false });

  if (error) return res.status(500).json({ detail: 'Erreur récupération exercices' });

  const result = (rows ?? []).map(a => ({
    id: a.id,
    titre: a.titre,
    teacher_nom: a.teacher_nom,
    lang: a.lang,
    difficulty: a.difficulty,
    created_at: a.created_at,
    submitted: !!a.submitted_at,
  }));

  return res.status(200).json(result);
}
