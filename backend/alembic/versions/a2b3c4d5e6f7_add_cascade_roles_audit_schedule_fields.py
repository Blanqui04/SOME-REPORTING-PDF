"""add_cascade_roles_audit_schedule_fields

Revision ID: a2b3c4d5e6f7
Revises: 776166b7436c
Create Date: 2026-02-24 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: str = "776166b7436c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add audit_logs table, user role, schedule extra fields, and ON DELETE CASCADE."""
    # --- New table: audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("resource_id", sa.String(length=36), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_resource_type"), "audit_logs", ["resource_type"], unique=False
    )

    # --- Users: add role column ---
    op.add_column("users", sa.Column("role", sa.String(length=20), nullable=True))
    op.execute("UPDATE users SET role = 'editor' WHERE role IS NULL")
    op.alter_column("users", "role", nullable=False, server_default="editor")

    # --- Schedules: add extra columns ---
    op.add_column("schedules", sa.Column("email_recipients", sa.JSON(), nullable=True))
    op.add_column(
        "schedules", sa.Column("webhook_url", sa.String(length=2048), nullable=True)
    )
    op.add_column(
        "schedules",
        sa.Column("language", sa.String(length=5), nullable=False, server_default="ca"),
    )
    op.add_column(
        "schedules", sa.Column("template_id", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "schedules",
        sa.Column("width", sa.Integer(), nullable=False, server_default="1000"),
    )
    op.add_column(
        "schedules",
        sa.Column("height", sa.Integer(), nullable=False, server_default="500"),
    )
    op.add_column("schedules", sa.Column("description", sa.Text(), nullable=True))
    op.add_column(
        "schedules", sa.Column("dashboard_title", sa.String(length=500), nullable=True)
    )

    # --- Reports: add index on created_by_id and switch FK to CASCADE ---
    op.create_index(
        op.f("ix_reports_created_by_id"), "reports", ["created_by_id"], unique=False
    )
    op.drop_constraint("reports_created_by_id_fkey", "reports", type_="foreignkey")
    op.create_foreign_key(
        "reports_created_by_id_fkey",
        "reports",
        "users",
        ["created_by_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # --- Schedules: add index on user_id and switch FK to CASCADE ---
    op.create_index(
        op.f("ix_schedules_user_id"), "schedules", ["user_id"], unique=False
    )
    op.drop_constraint("schedules_user_id_fkey", "schedules", type_="foreignkey")
    op.create_foreign_key(
        "schedules_user_id_fkey",
        "schedules",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Revert cascade, roles, extra schedule fields, and audit_logs table."""
    # --- Revert schedules FK ---
    op.drop_constraint("schedules_user_id_fkey", "schedules", type_="foreignkey")
    op.create_foreign_key(
        "schedules_user_id_fkey", "schedules", "users", ["user_id"], ["id"]
    )
    op.drop_index(op.f("ix_schedules_user_id"), table_name="schedules")

    # --- Revert reports FK ---
    op.drop_constraint("reports_created_by_id_fkey", "reports", type_="foreignkey")
    op.create_foreign_key(
        "reports_created_by_id_fkey", "reports", "users", ["created_by_id"], ["id"]
    )
    op.drop_index(op.f("ix_reports_created_by_id"), table_name="reports")

    # --- Remove schedule extra columns ---
    op.drop_column("schedules", "dashboard_title")
    op.drop_column("schedules", "description")
    op.drop_column("schedules", "height")
    op.drop_column("schedules", "width")
    op.drop_column("schedules", "template_id")
    op.drop_column("schedules", "language")
    op.drop_column("schedules", "webhook_url")
    op.drop_column("schedules", "email_recipients")

    # --- Remove user role ---
    op.drop_column("users", "role")

    # --- Drop audit_logs ---
    op.drop_index(op.f("ix_audit_logs_resource_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_table("audit_logs")
