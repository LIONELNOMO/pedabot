import { v4 as uuidv4 } from 'uuid';
import supabase from '../../lib/supabase.js';
import { cors, requireAuth } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();

  const user = requireAuth(req);
  if (!user || user.role !== 'prof') return res.status(403).json({ detail: 'Accès réservé aux professeurs' });

  const { action } = req.query;

  const teacherId = Number(user.sub);

  // ─── GET /api/exercises/mine ───
  if (action === 'mine' && req.method === 'GET') {
    const { data: exercises, error } = await supabase
      .from('exercisedb')
      .select('id, titre, contenu, lang, difficulty, created_at')
      .eq('teacher_id', teacherId)
      .order('created_at', { ascending: false });

    if (error) return res.status(500).json({ detail: 'Erreur récupération exercices' });

    if (!exercises.length) return res.status(200).json([]);

    const exIds = exercises.map(e => e.id);
    const { data: links } = await supabase
      .from('sharedlink')
      .select('token, exercise_id')
      .in('exercise_id', exIds);

    const tokens = (links ?? []).map(l => l.token);
    const counts = {};
    if (tokens.length) {
      const { data: subs } = await supabase
        .from('submission')
        .select('token')
        .in('token', tokens);
      (subs ?? []).forEach(s => { counts[s.token] = (counts[s.token] ?? 0) + 1; });
    }

    const tokenByExId = {};
    (links ?? []).forEach(l => { tokenByExId[l.exercise_id] = l.token; });

    const result = exercises.map(ex => {
      const token = tokenByExId[ex.id] ?? null;
      return {
        id: ex.id,
        titre: ex.titre,
        contenu: ex.contenu,
        lang: ex.lang,
        difficulty: ex.difficulty,
        created_at: ex.created_at,
        token,
        submission_count: token ? (counts[token] ?? 0) : 0,
      };
    });

    return res.status(200).json(result);
  }

  // ─── POST /api/exercises/share ───
  if (action === 'share' && req.method === 'POST') {
    const { titre, exercise, lang, difficulty } = req.body || {};
    if (!titre || !exercise) return res.status(400).json({ detail: 'Titre et exercice requis' });

    const contenu = typeof exercise === 'string' ? exercise : JSON.stringify(exercise);

    const { data: ex, error: exErr } = await supabase
      .from('exercisedb')
      .insert({
        teacher_id: teacherId,
        teacher_nom: user.nom,
        titre,
        contenu,
        lang: lang ?? '',
        difficulty: difficulty ?? '',
      })
      .select('id')
      .single();

    if (exErr) {
      console.error('share/exercisedb insert error:', exErr);
      return res.status(500).json({ detail: 'Erreur sauvegarde exercice' });
    }

    const token = uuidv4();
    const { error: linkErr } = await supabase
      .from('sharedlink')
      .insert({ token, exercise_id: ex.id, teacher_id: teacherId });

    if (linkErr) return res.status(500).json({ detail: 'Erreur création lien' });

    return res.status(201).json({ token, exercise_id: ex.id });
  }

  // ─── POST /api/exercises/assign ───
  if (action === 'assign' && req.method === 'POST') {
    const { exercise_id, eleve_emails } = req.body || {};
    if (!exercise_id || !Array.isArray(eleve_emails) || eleve_emails.length === 0)
      return res.status(400).json({ detail: 'exercise_id et eleve_emails requis' });

    const { data: ex, error: exErr } = await supabase
      .from('exercisedb')
      .select('titre, contenu, lang, difficulty')
      .eq('id', Number(exercise_id))
      .eq('teacher_id', teacherId)
      .maybeSingle();

    if (exErr || !ex) {
      console.error('assign/exercise lookup error:', exErr, 'exercise_id:', exercise_id, 'teacher_id:', teacherId);
      return res.status(404).json({ detail: 'Exercice introuvable' });
    }

    const rows = eleve_emails.map(email => ({
      teacher_id: teacherId,
      teacher_nom: user.nom,
      eleve_email: String(email).toLowerCase().trim(),
      titre: ex.titre,
      contenu: ex.contenu,
      lang: ex.lang,
      difficulty: ex.difficulty,
    }));

    const { error } = await supabase.from('assignment').insert(rows);
    if (error) {
      console.error('assign/assignment insert error:', error);
      return res.status(500).json({ detail: 'Erreur assignation' });
    }

    return res.status(201).json({ message: `Exercice assigné à ${eleve_emails.length} élève(s)` });
  }

  // ─── GET /api/exercises/assignments ───
  if (action === 'assignments' && req.method === 'GET') {
    const { data, error } = await supabase
      .from('assignment')
      .select('id, eleve_email, titre, contenu, lang, difficulty, reponses, submitted_at, feedback, feedback_at, corrige_visible, created_at')
      .eq('teacher_id', teacherId)
      .order('created_at', { ascending: false });

    if (error) {
      console.error('assignments fetch error:', error);
      return res.status(500).json({ detail: 'Erreur récupération devoirs' });
    }

    return res.status(200).json(data ?? []);
  }

  return res.status(404).json({ detail: 'Action inconnue' });
}
