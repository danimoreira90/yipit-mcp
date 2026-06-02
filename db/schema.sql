-- YipitData KPI schema (Postgres 16). Transcribed verbatim from DATA-MODEL.md §4.
-- One table for both estimate kinds, discriminated by estimate_type, with two
-- partial-unique indexes for the two different natural keys.

CREATE TABLE companies (
    ticker        TEXT PRIMARY KEY,
    company_name  TEXT NOT NULL,
    sector        TEXT NOT NULL
);
CREATE INDEX idx_companies_sector ON companies (sector);

CREATE TABLE kpi_estimates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker        TEXT NOT NULL REFERENCES companies (ticker),
    kpi           TEXT NOT NULL,
    unit          TEXT NOT NULL,                 -- determined by kpi; stored for convenience
    period        TEXT NOT NULL,                 -- 'YYYYQn', e.g. '2026Q1'
    period_start  DATE NOT NULL,                 -- filter/sort on this
    period_end    DATE NOT NULL,
    estimate_type TEXT NOT NULL CHECK (estimate_type IN ('historical','qtd')),
    value         NUMERIC NOT NULL,
    as_of         DATE,                           -- NULL for historical, set for qtd
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT as_of_matches_type CHECK (
        (estimate_type = 'historical' AND as_of IS NULL)
     OR (estimate_type = 'qtd'        AND as_of IS NOT NULL)
    )
);

-- one settled value per finished quarter
CREATE UNIQUE INDEX uq_hist ON kpi_estimates (ticker, kpi, period)
    WHERE estimate_type = 'historical';
-- one value per intra-quarter snapshot
CREATE UNIQUE INDEX uq_qtd  ON kpi_estimates (ticker, kpi, period, as_of)
    WHERE estimate_type = 'qtd';

-- query helpers
CREATE INDEX idx_hist_series ON kpi_estimates (ticker, kpi, period_start)
    WHERE estimate_type = 'historical';
CREATE INDEX idx_qtd_latest  ON kpi_estimates (ticker, kpi, as_of DESC)
    WHERE estimate_type = 'qtd';
