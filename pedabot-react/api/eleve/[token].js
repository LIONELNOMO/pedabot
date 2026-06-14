import supabase from '../../lib/supabase.js';
import { cors } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });

  const { token } = req.query;
  if (!token) return res.status(400).json({ detail: 'Token requis' });

  const { data: link } = await supabase
    .from('sharedlink')
    .select('exercise_id')
    .eq('token', token)
    .maybeSingle();

  if (!link) return res.status(404).json({ detail: 'Lien invalide ou expiré' });

  const { data: ex } = await supabase
    .from('exercisedb')
    .select('titre, contenu, teacher_nom, lang, difficulty')
    .eq('id', link.exercise_id)
    .maybeSingle();

  if (!ex) return res.status(404).json({ detail: 'Exercice introuvable' });

  let exercise;
  try { exercise = JSON.parse(ex.contenu); }
  catch { exercise = { title: ex.titre, body: ex.contenu, level: ex.difficulty }; }

  return res.status(200).json({
    titre: ex.titre,
    teacher_nom: ex.teacher_nom,
    exercise,
    lang: ex.lang,
    difficulty: ex.difficulty,
  });
}
