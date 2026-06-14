import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });

  const user = requireAuth(req);
  if (!user) return res.status(401).json({ detail: 'Non authentifié' });

  const { id } = req.query;
  if (!id) return res.status(400).json({ detail: 'ID requis' });

  const { data: a, error } = await supabase
    .from('assignment')
    .select('id, titre, teacher_nom, contenu, lang, difficulty, reponses, submitted_at, feedback, feedback_at, corrige_visible, created_at')
    .eq('id', Number(id))
    .eq('eleve_email', String(user.email).toLowerCase().trim())
    .maybeSingle();

  if (error || !a) return res.status(404).json({ detail: 'Exercice introuvable' });

  let exercise;
  try { exercise = JSON.parse(a.contenu); }
  catch { exercise = { title: a.titre, body: a.contenu, level: a.difficulty }; }

  return res.status(200).json({
    id: a.id,
    titre: a.titre,
    teacher_nom: a.teacher_nom,
    exercise,
    lang: a.lang,
    difficulty: a.difficulty,
    reponses: a.reponses ?? '',
    submitted: !!a.submitted_at,
    feedback: a.feedback ?? '',
    feedback_at: a.feedback_at,
    corrige_visible: !!a.corrige_visible,
    submitted_at: a.submitted_at,
    created_at: a.created_at,
  });
}
