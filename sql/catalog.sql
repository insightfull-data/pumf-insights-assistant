-- Variable catalog for the PUMF Insights Assistant
-- PostgreSQL 16+ with pgvector (Aurora PostgreSQL or Cloud SQL for PostgreSQL)

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS ltree;

CREATE SCHEMA IF NOT EXISTS catalog;
SET search_path = catalog, public;

-- One row per source survey
CREATE TABLE survey (
    survey_id      text PRIMARY KEY,            -- 'cius', 'census_individuals', 'census_hierarchical'
    name           text NOT NULL,
    producer       text NOT NULL DEFAULT 'Statistics Canada',
    unit           text NOT NULL,               -- 'person', 'household'
    population     text NOT NULL                -- e.g. 'Individuals 15+ in the ten provinces'
);

-- One row per survey release; the assistant reads only status = 'published'
CREATE TYPE release_status AS ENUM ('ingesting', 'staged', 'published', 'retired', 'failed');

CREATE TABLE release (
    release_id        text PRIMARY KEY,         -- 'cius_2022'
    survey_id         text NOT NULL REFERENCES survey,
    ref_period        text NOT NULL,            -- '2022'
    status            release_status NOT NULL DEFAULT 'ingesting',
    source_sha256     char(64) NOT NULL,
    licence_uri       text,
    pipeline_version  text NOT NULL,
    record_count      integer,
    weight_total      numeric,
    has_bootstrap     boolean NOT NULL DEFAULT false,
    published_at      timestamptz,
    approved_by       text,
    UNIQUE (survey_id, ref_period)
);

-- Only one published release per survey at a time is the default for new questions
CREATE UNIQUE INDEX one_default_release ON release (survey_id) WHERE status = 'published';

CREATE TYPE measure_type AS ENUM ('categorical', 'continuous', 'weight', 'identifier');
CREATE TYPE review_status AS ENUM ('draft', 'approved', 'rejected');

-- One row per variable code per release
CREATE TABLE variable (
    variable_id        bigserial PRIMARY KEY,
    release_id         text NOT NULL REFERENCES release ON DELETE CASCADE,
    code               text NOT NULL,           -- lower-cased StatCan code, never renamed
    label_en           text NOT NULL,
    label_fr           text,
    question_text      text,
    universe_text      text,                    -- as published
    universe_expr      jsonb,                   -- same filter syntax as the query spec
    topic_path         ltree,                   -- e.g. 'online_activities.media.streaming'
    measure_type       measure_type NOT NULL,
    weight_code        text,                    -- weight to use with this variable
    description_plain  text,                    -- steward-approved or machine-drafted
    synonyms           text[] NOT NULL DEFAULT '{}',
    review_status      review_status NOT NULL DEFAULT 'draft',
    machine_drafted    boolean NOT NULL DEFAULT false,
    search_text        text,                    -- what was embedded
    search_tsv         tsvector,                -- maintained by trigger below
    embedding          vector(1024),
    UNIQUE (release_id, code)
);

CREATE OR REPLACE FUNCTION variable_search_tsv_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    NEW.search_tsv := to_tsvector('simple',
        coalesce(NEW.code,'') || ' ' || coalesce(NEW.label_en,'') || ' ' || coalesce(NEW.label_fr,'') || ' ' ||
        coalesce(NEW.question_text,'') || ' ' || coalesce(NEW.description_plain,'') || ' ' ||
        array_to_string(NEW.synonyms, ' '));
    RETURN NEW;
END $$;

CREATE TRIGGER variable_search_tsv_trg BEFORE INSERT OR UPDATE ON variable
    FOR EACH ROW EXECUTE FUNCTION variable_search_tsv_update();

CREATE INDEX variable_embedding_hnsw ON variable USING hnsw (embedding vector_cosine_ops);
CREATE INDEX variable_search_tsv ON variable USING gin (search_tsv);
CREATE INDEX variable_topic ON variable USING gist (topic_path);

CREATE TYPE missing_type AS ENUM ('valid', 'valid_skip', 'dont_know', 'refusal', 'not_stated');

-- One row per code value of a categorical variable
CREATE TABLE value_label (
    variable_id   bigint NOT NULL REFERENCES variable ON DELETE CASCADE,
    code          text NOT NULL,
    label_en      text NOT NULL,
    label_fr      text,
    missing_type  missing_type NOT NULL DEFAULT 'valid',
    sort_order    integer NOT NULL,
    PRIMARY KEY (variable_id, code)
);

-- Logical concepts that link the same question across releases (for trends)
CREATE TABLE concept (
    concept_id   bigserial PRIMARY KEY,
    name         text NOT NULL UNIQUE,
    description  text
);

CREATE TABLE concept_variable (
    concept_id          bigint NOT NULL REFERENCES concept ON DELETE CASCADE,
    variable_id         bigint NOT NULL REFERENCES variable ON DELETE CASCADE,
    comparability_note  text,                   -- wording or universe changes between cycles
    PRIMARY KEY (concept_id, variable_id)
);

-- Shared demographic dimensions across surveys (h_ columns)
CREATE TABLE harmonized_dim (
    dim        text PRIMARY KEY,               -- 'h_age_band', 'h_province', 'h_income_quintile'
    label_en   text NOT NULL
);

CREATE TABLE harmonized_value (
    dim         text NOT NULL REFERENCES harmonized_dim,
    h_code      text NOT NULL,
    label_en    text NOT NULL,
    sort_order  integer NOT NULL,
    PRIMARY KEY (dim, h_code)
);

CREATE TABLE crosswalk (
    variable_id  bigint NOT NULL REFERENCES variable ON DELETE CASCADE,
    source_code  text NOT NULL,
    dim          text NOT NULL,
    h_code       text NOT NULL,
    rule_note    text,
    PRIMARY KEY (variable_id, source_code),
    FOREIGN KEY (dim, h_code) REFERENCES harmonized_value (dim, h_code)
);

-- Steward-approved recodes, e.g. 'heavy streamer'
CREATE TABLE derived_variable (
    derived_id       bigserial PRIMARY KEY,
    release_id       text NOT NULL REFERENCES release,
    code             text NOT NULL,             -- must not collide with source codes
    label_en         text NOT NULL,
    definition_json  jsonb NOT NULL,            -- filter syntax over source codes
    approved_by      text,
    approved_at      timestamptz,
    UNIQUE (release_id, code)
);

-- Release-independent audiences users save and reuse
CREATE TABLE saved_target (
    target_id        bigserial PRIMARY KEY,
    owner_hash       text NOT NULL,             -- salted hash of the user id
    name             text NOT NULL,
    definition_json  jsonb NOT NULL,            -- in harmonized or concept terms
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- Approximate CVs from each release's sampling-variability tables (when no bootstrap weights)
CREATE TABLE cv_lookup (
    release_id      text NOT NULL REFERENCES release,
    geography       text NOT NULL,              -- 'CA' or province code
    estimate_min    numeric NOT NULL,
    estimate_max    numeric NOT NULL,
    approx_cv_pct   numeric NOT NULL,
    PRIMARY KEY (release_id, geography, estimate_min)
);

-- Reliability cut-offs per release, taken from its user guide
CREATE TABLE reliability_rule (
    release_id        text PRIMARY KEY REFERENCES release,
    caution_cv_pct    numeric NOT NULL,         -- e.g. 16.6
    suppress_cv_pct   numeric NOT NULL,         -- e.g. 33.3
    min_unweighted_n  integer NOT NULL
);

-- Hybrid retrieval: vector + full text, merged with reciprocal rank fusion.
-- $1 = query embedding, $2 = query text, $3 = survey_id
CREATE OR REPLACE FUNCTION search_variables(q_emb vector(1024), q_text text, q_survey text, k integer DEFAULT 20)
RETURNS TABLE (variable_id bigint, code text, label_en text, score double precision)
LANGUAGE sql STABLE
SET search_path = catalog, public
AS $$
    WITH pub AS (
        SELECT release_id FROM release WHERE survey_id = q_survey AND status = 'published'
    ),
    vec AS (
        SELECT v.variable_id, row_number() OVER (ORDER BY v.embedding <=> q_emb) AS r
        FROM variable v JOIN pub USING (release_id)
        ORDER BY v.embedding <=> q_emb LIMIT 50
    ),
    txt AS (
        SELECT v.variable_id,
               row_number() OVER (ORDER BY ts_rank(v.search_tsv, plainto_tsquery('simple', q_text)) DESC) AS r
        FROM variable v JOIN pub USING (release_id)
        WHERE v.search_tsv @@ plainto_tsquery('simple', q_text)
        LIMIT 50
    ),
    exact AS (
        SELECT v.variable_id FROM variable v JOIN pub USING (release_id) WHERE v.code = lower(q_text)
    ),
    fused AS (
        SELECT variable_id, sum(1.0 / (60 + r)) AS s
        FROM (SELECT * FROM vec UNION ALL SELECT * FROM txt) u
        GROUP BY variable_id
    )
    SELECT v.variable_id, v.code, v.label_en,
           CASE WHEN e.variable_id IS NOT NULL THEN 1e6 ELSE coalesce(f.s, 0) END AS score
    FROM variable v
    LEFT JOIN fused f USING (variable_id)
    LEFT JOIN exact e USING (variable_id)
    WHERE f.variable_id IS NOT NULL OR e.variable_id IS NOT NULL
    ORDER BY score DESC
    LIMIT k;
$$;
