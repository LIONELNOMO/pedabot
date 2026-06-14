-- ══════════════════════════════════════════════════════
--  PédaBot — Schéma Supabase
--  Coller ce SQL dans Supabase > SQL Editor > New query
-- ══════════════════════════════════════════════════════

-- 1. Utilisateurs (profs et élèves)
CREATE TABLE IF NOT EXISTS "user" (
  id            SERIAL PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  nom           TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'prof',
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Exercices sauvegardés (liés aux SharedLinks)
CREATE TABLE IF NOT EXISTS exercisedb (
  id          SERIAL PRIMARY KEY,
  teacher_id  INTEGER NOT NULL,
  teacher_nom TEXT NOT NULL,
  titre       TEXT NOT NULL,
  contenu     TEXT NOT NULL,
  lang        TEXT DEFAULT '',
  difficulty  TEXT DEFAULT '',
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Liens de partage (token anonyme → exercice)
CREATE TABLE IF NOT EXISTS sharedlink (
  token       TEXT PRIMARY KEY,
  exercise_id INTEGER NOT NULL REFERENCES exercisedb(id),
  teacher_id  INTEGER NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Copies anonymes (élève sans compte)
CREATE TABLE IF NOT EXISTS submission (
  id            SERIAL PRIMARY KEY,
  token         TEXT NOT NULL REFERENCES sharedlink(token),
  eleve_prenom  TEXT NOT NULL,
  reponses      TEXT NOT NULL,
  submitted_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Assignations (élève avec compte)
CREATE TABLE IF NOT EXISTS assignment (
  id              SERIAL PRIMARY KEY,
  teacher_id      INTEGER NOT NULL,
  teacher_nom     TEXT NOT NULL,
  eleve_email     TEXT NOT NULL,
  titre           TEXT NOT NULL,
  contenu         TEXT NOT NULL,
  lang            TEXT DEFAULT '',
  difficulty      TEXT DEFAULT '',
  reponses        TEXT,
  submitted_at    TIMESTAMPTZ,
  corrige_visible BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Index utiles
CREATE INDEX IF NOT EXISTS idx_submission_token      ON submission(token);
CREATE INDEX IF NOT EXISTS idx_assignment_eleve_email ON assignment(eleve_email);
CREATE INDEX IF NOT EXISTS idx_assignment_teacher_id  ON assignment(teacher_id);
CREATE INDEX IF NOT EXISTS idx_sharedlink_teacher_id  ON sharedlink(teacher_id);

-- ══════════════════════════════════════════════════════
--  Comptes démo (mots de passe : demo123)
--  Hash bcrypt de "demo123"
-- ══════════════════════════════════════════════════════
INSERT INTO "user" (email, nom, password_hash, role) VALUES
  ('demo@pedabot.com',  'Prof. Demo', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhQGrm6R.VBRoUhWjHhXIm', 'prof'),
  ('kamga@pedabot.com', 'M. Kamga',   '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhQGrm6R.VBRoUhWjHhXIm', 'prof'),
  ('ngono@pedabot.com', 'Mme Ngono',  '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMqJqhQGrm6R.VBRoUhWjHhXIm', 'prof')
ON CONFLICT (email) DO NOTHING;
