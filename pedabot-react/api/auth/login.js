import supabase from '../../lib/supabase.js';
import { verifyPassword, createToken, cors } from '../../lib/auth.js';

export default async function handler(req, res) {
  cors(res);
  if (req.method === 'OPTIONS') return res.status(200).end();
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  const { email, password } = req.body || {};
  if (!email || !password) return res.status(400).json({ error: 'Email et mot de passe requis' });

  const { data: user, error } = await supabase
    .from('user')
    .select('id, email, nom, role, password_hash')
    .eq('email', email.toLowerCase().trim())
    .single();

  if (error || !user) return res.status(401).json({ error: 'Identifiants invalides' });

  if (!verifyPassword(password, user.password_hash))
    return res.status(401).json({ error: 'Identifiants invalides' });

  const token = createToken(user.id, user.email, user.nom, user.role);
  return res.status(200).json({ token, nom: user.nom, role: user.role, email: user.email });
}
