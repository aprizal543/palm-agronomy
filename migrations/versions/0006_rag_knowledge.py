"""Create verified agronomy knowledge and auditable RAG retrieval tables."""

from alembic import op

revision = "0006_rag_knowledge"
down_revision = "0005_production_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Supabase exposes pgvector through the shared extensions schema.
    op.execute("create extension if not exists vector with schema extensions")
    op.execute(
        """
        create table palm.knowledge_sources (
          id uuid primary key default gen_random_uuid(),
          title varchar(300) not null,
          publisher varchar(200) not null,
          source_type text not null
            check (source_type in ('guideline','regulation','manual','article','research')),
          source_url text not null,
          publication_year integer
            check (publication_year is null or publication_year between 1900 and 2100),
          language varchar(10) not null default 'id',
          version_label varchar(100),
          license_label varchar(150),
          checksum_sha256 char(64) not null unique,
          origin_type text not null
            check (origin_type in ('public_document','user_supplied','synthetic')),
          verification_status text not null default 'pending'
            check (verification_status in ('pending','verified','rejected')),
          verification_note varchar(500),
          verified_at timestamptz,
          metadata jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint verified_source_has_timestamp check (
            verification_status <> 'verified' or verified_at is not null
          )
        )
        """
    )
    op.execute(
        "create index knowledge_sources_verification_idx "
        "on palm.knowledge_sources(verification_status,source_type)"
    )
    op.execute(
        """
        create table palm.knowledge_chunks (
          id uuid primary key default gen_random_uuid(),
          source_id uuid not null references palm.knowledge_sources(id) on delete cascade,
          chunk_index integer not null check (chunk_index >= 0),
          section_title varchar(300),
          content text not null check (char_length(content) between 40 and 4000),
          content_hash char(64) not null,
          token_count integer check (token_count is null or token_count > 0),
          search_vector tsvector generated always as (
            to_tsvector('simple', coalesce(section_title,'') || ' ' || content)
          ) stored,
          embedding extensions.vector(1536),
          created_at timestamptz not null default now(),
          unique(source_id,chunk_index),
          unique(source_id,content_hash)
        )
        """
    )
    op.execute(
        "create index knowledge_chunks_search_idx "
        "on palm.knowledge_chunks using gin(search_vector)"
    )
    op.execute("create index knowledge_chunks_source_idx on palm.knowledge_chunks(source_id)")
    op.execute(
        """
        create table palm.rag_query_logs (
          id uuid primary key default gen_random_uuid(),
          trace_id uuid not null,
          update_id bigint references palm.telegram_updates(update_id) on delete set null,
          chat_id bigint,
          telegram_user_id bigint,
          channel text not null check (channel in ('telegram','api','evaluation')),
          query_text varchar(500) not null,
          retrieval_status text not null
            check (retrieval_status in ('answered','insufficient_evidence','failed')),
          retrieved_chunk_ids uuid[] not null default '{}'::uuid[],
          retrieval_scores double precision[] not null default '{}'::double precision[],
          top_k integer not null check (top_k between 1 and 5),
          created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index rag_query_logs_trace_idx on palm.rag_query_logs(trace_id)")
    op.execute("create index rag_query_logs_created_idx on palm.rag_query_logs(created_at desc)")
    op.execute(
        """
        create trigger knowledge_sources_set_updated_at before update
        on palm.knowledge_sources for each row execute function palm.set_updated_at()
        """
    )
    op.execute(
        "comment on table palm.knowledge_sources is "
        "'Curated agronomy sources; only verified sources are eligible for retrieval'"
    )
    op.execute(
        "comment on table palm.rag_query_logs is "
        "'Evidence trace for retrieval evaluation and hallucination audits'"
    )


def downgrade() -> None:
    op.execute(
        "drop trigger if exists knowledge_sources_set_updated_at on palm.knowledge_sources"
    )
    op.execute("drop table if exists palm.rag_query_logs")
    op.execute("drop table if exists palm.knowledge_chunks")
    op.execute("drop table if exists palm.knowledge_sources")
    # The shared vector extension is intentionally preserved.
