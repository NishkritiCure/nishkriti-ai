-- Nishkriti AI — Canonical Database Schema
-- Run in Supabase SQL Editor (Dashboard → SQL Editor → New Query → Run)
-- Safe to re-run: all statements are IF NOT EXISTS

-- ─── patients ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS patients (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone       TEXT UNIQUE NOT NULL,       -- E.164: +91XXXXXXXXXX
    name        TEXT,
    age         INTEGER,
    gender      TEXT,                       -- 'male' | 'female' | 'other'
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── calls ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS calls (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       UUID NOT NULL REFERENCES patients(id),
    exotel_call_id   TEXT UNIQUE NOT NULL,  -- CallSid from Exotel webhook
    layer            INTEGER NOT NULL,      -- 1 | 2 | 3
    status           TEXT NOT NULL,         -- 'initiated' | 'in_progress' | 'completed' | 'failed'
    recording_url    TEXT,                  -- Exotel recording URL (populated on call-complete)
    transcript_raw   TEXT,                  -- full Sarvam AI transcript
    transcript_json  JSONB,                 -- Agent 1 structured output
    started_at       TIMESTAMPTZ,
    ended_at         TIMESTAMPTZ,
    duration_secs    INTEGER,
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS calls_patient_id_idx ON calls(patient_id);

-- ─── clinical_notes ──────────────────────────────────────────────────────────
-- One row per call. Agents 1–4 populate their respective JSONB columns
-- sequentially; the row is created by Agent 1 and updated by Agents 2–4.
CREATE TABLE IF NOT EXISTS clinical_notes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id          UUID NOT NULL REFERENCES calls(id),
    patient_id       UUID NOT NULL REFERENCES patients(id),
    structured_data  JSONB,    -- Agent 1 output
    hypotheses       JSONB,    -- Agent 2 output
    red_flags        JSONB,    -- Agent 3 output
    protocol         JSONB,    -- Agent 4 output
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS clinical_notes_call_id_idx ON clinical_notes(call_id);
CREATE INDEX IF NOT EXISTS clinical_notes_patient_id_idx ON clinical_notes(patient_id);

-- ─── plans ───────────────────────────────────────────────────────────────────
-- Status lifecycle:
--   draft → pending_approval → approved
--     plan_1: approved → released immediately
--     plan_2: approved → held → released (after both consents received)
--     plan_3: approved → active (when plan_2 released)
CREATE TABLE IF NOT EXISTS plans (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id   UUID NOT NULL REFERENCES patients(id),
    call_id      UUID NOT NULL REFERENCES calls(id),
    plan_type    TEXT NOT NULL,    -- 'plan_1' | 'plan_2' | 'plan_3'
    status       TEXT NOT NULL,    -- 'draft' | 'pending_approval' | 'approved' | 'held' | 'released' | 'active'
    content      JSONB NOT NULL,   -- plan line items
    pdf_url      TEXT,             -- Cloudflare R2 signed URL
    approved_by  TEXT,             -- JWT sub claim of approving doctor
    approved_at  TIMESTAMPTZ,
    released_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS plans_patient_id_idx ON plans(patient_id);
CREATE INDEX IF NOT EXISTS plans_call_id_idx ON plans(call_id);

-- ─── consents ────────────────────────────────────────────────────────────────
-- Plan 2 requires TWO consent rows: whatsapp_confirmation + digital_signature.
-- Both must be status='received' before Plan 2 transitions held → released.
-- UNIQUE on (plan_id, consent_type) enforces idempotency.
CREATE TABLE IF NOT EXISTS consents (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id    UUID NOT NULL REFERENCES patients(id),
    plan_id       UUID NOT NULL REFERENCES plans(id),
    consent_type  TEXT NOT NULL,    -- 'whatsapp_confirmation' | 'digital_signature'
    status        TEXT NOT NULL,    -- 'pending' | 'received' | 'rejected'
    received_at   TIMESTAMPTZ,
    signature_url TEXT,             -- R2 URL (digital_signature type only)
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT consents_plan_consent_unique UNIQUE (plan_id, consent_type)
);

CREATE INDEX IF NOT EXISTS consents_patient_id_idx ON consents(patient_id);
CREATE INDEX IF NOT EXISTS consents_plan_id_idx ON consents(plan_id);

-- ─── follow_ups ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS follow_ups (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       UUID NOT NULL REFERENCES patients(id),
    plan_3_id        UUID NOT NULL REFERENCES plans(id),
    scheduled_at     TIMESTAMPTZ NOT NULL,
    status           TEXT NOT NULL,    -- 'scheduled' | 'completed' | 'missed' | 'rescheduled'
    call_id          UUID REFERENCES calls(id),    -- populated after call occurs
    adherence_score  INTEGER,          -- 1–5 (1=non-adherent, 5=fully adherent)
    frequency_days   INTEGER NOT NULL, -- current call cadence in days
    created_at       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS follow_ups_patient_id_idx ON follow_ups(patient_id);
CREATE INDEX IF NOT EXISTS follow_ups_plan_3_id_idx ON follow_ups(plan_3_id);
CREATE INDEX IF NOT EXISTS follow_ups_status_scheduled_at_idx ON follow_ups(status, scheduled_at);

-- ─── reports ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id   UUID NOT NULL REFERENCES patients(id),
    file_url     TEXT NOT NULL,        -- Cloudflare R2 URL
    file_name    TEXT,
    uploaded_via TEXT DEFAULT 'whatsapp',
    uploaded_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS reports_patient_id_idx ON reports(patient_id);
