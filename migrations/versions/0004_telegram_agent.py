"""Create Telegram idempotency, conversation, pending action, and audit tables."""

from alembic import op

revision = "0004_telegram_agent"
down_revision = "0003_blocks_spatial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep one SQL command per op.execute: asyncpg rejects multi-command prepared statements.
    op.execute(
        """
        create table palm.telegram_updates (
          update_id bigint primary key,
          chat_id bigint,
          telegram_user_id bigint,
          update_kind text not null,
          raw_update jsonb not null,
          status text not null default 'processing'
            check (status in ('processing','processed','failed')),
          attempts integer not null default 1 check (attempts > 0),
          error_message text,
          received_at timestamptz not null default now(),
          processed_at timestamptz
        )
        """
    )
    op.execute(
        "create index telegram_updates_status_idx on palm.telegram_updates(status,received_at)"
    )
    op.execute(
        """
        create table palm.conversations (
          chat_id bigint primary key,
          telegram_user_id bigint not null,
          user_id uuid references palm.users(id) on delete set null,
          state text not null default 'idle',
          context jsonb not null default '{}'::jsonb,
          current_farm_id uuid references palm.farms(id) on delete set null,
          current_block_id uuid references palm.blocks(id) on delete set null,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index conversations_user_idx on palm.conversations(telegram_user_id)")
    op.execute(
        """
        create trigger conversations_set_updated_at before update on palm.conversations
          for each row execute function palm.set_updated_at()
        """
    )
    op.execute(
        """
        create table palm.pending_actions (
          id uuid primary key default gen_random_uuid(),
          chat_id bigint not null references palm.conversations(chat_id) on delete cascade,
          telegram_user_id bigint not null,
          action_type text not null,
          payload jsonb not null,
          status text not null default 'pending'
            check (status in ('pending','confirmed','cancelled','expired')),
          expires_at timestamptz not null default (now() + interval '15 minutes'),
          resolved_at timestamptz,
          created_at timestamptz not null default now()
        )
        """
    )
    op.execute(
        "create index pending_actions_lookup_idx on palm.pending_actions(chat_id,status,expires_at)"
    )
    op.execute(
        """
        create table palm.agent_audit_logs (
          id uuid primary key default gen_random_uuid(),
          trace_id uuid not null,
          update_id bigint references palm.telegram_updates(update_id) on delete set null,
          chat_id bigint,
          telegram_user_id bigint,
          event_type text not null,
          intent text,
          tool_name text,
          input_data jsonb,
          output_data jsonb,
          status text not null check (status in ('started','succeeded','failed','rejected')),
          latency_ms integer check (latency_ms is null or latency_ms >= 0),
          error_message text,
          created_at timestamptz not null default now()
        )
        """
    )
    op.execute("create index agent_audit_trace_idx on palm.agent_audit_logs(trace_id,created_at)")
    op.execute("create index agent_audit_update_idx on palm.agent_audit_logs(update_id)")
    op.execute(
        "comment on table palm.telegram_updates is "
        "'Telegram update idempotency ledger; update_id is the source event key'"
    )
    op.execute(
        "comment on table palm.agent_audit_logs is "
        "'Auditable agent intent and allow-listed tool execution events'"
    )


def downgrade() -> None:
    op.execute("drop table if exists palm.agent_audit_logs")
    op.execute("drop table if exists palm.pending_actions")
    op.execute("drop trigger if exists conversations_set_updated_at on palm.conversations")
    op.execute("drop table if exists palm.conversations")
    op.execute("drop table if exists palm.telegram_updates")
