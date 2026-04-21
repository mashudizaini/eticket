-- PostgreSQL schema untuk E-Ticket application
-- v2: tambah kolom SSO (keycloak_id, employee_number, dll.)

CREATE TABLE IF NOT EXISTS users (
    id              SERIAL PRIMARY KEY,
    keycloak_id     VARCHAR(255) UNIQUE,
    username        VARCHAR(100) UNIQUE,
    email           VARCHAR(255),
    full_name       VARCHAR(200),
    role            VARCHAR(20) DEFAULT 'user',
    is_active       BOOLEAN DEFAULT TRUE,
    -- Data Oracle EBS (di-sync saat first login)
    person_id       INTEGER,
    employee_number VARCHAR(50),
    jabatan         VARCHAR(100),
    divisi          VARCHAR(100),
    department      VARCHAR(50),
    team            VARCHAR(50),
    -- Legacy fields (dipertahankan agar tidak break existing data)
    password        VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_users_id          ON users(id);
CREATE INDEX IF NOT EXISTS ix_users_keycloak_id ON users(keycloak_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username);

-- Tickets table
CREATE TABLE IF NOT EXISTS tickets (
    id                 SERIAL PRIMARY KEY,
    ticket_id          VARCHAR(50) NOT NULL UNIQUE,
    title              VARCHAR(200) NOT NULL,
    description        TEXT,
    department         VARCHAR(50),
    category           VARCHAR(50),
    priority           VARCHAR(20),
    status             VARCHAR(20) DEFAULT 'new',
    requester_id       INTEGER,
    requester_name     VARCHAR(100),
    requester_fullname VARCHAR(200),
    team_id            VARCHAR(50),
    team_desc          VARCHAR(200),
    pic_id             INTEGER,
    pic_name           VARCHAR(100),
    pic_fullname       VARCHAR(200),
    pic_assigned_at    TIMESTAMPTZ,
    resolution         TEXT,
    resolution_status  VARCHAR(20),
    cancel_reason      TEXT,
    cancelled_at       TIMESTAMPTZ,
    created_at         TIMESTAMPTZ DEFAULT NOW(),
    updated_at         TIMESTAMPTZ,
    closed_at          TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_tickets_id        ON tickets(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tickets_ticket_id ON tickets(ticket_id);
CREATE INDEX IF NOT EXISTS ix_tickets_status    ON tickets(status);
CREATE INDEX IF NOT EXISTS ix_tickets_department ON tickets(department);

-- Ticket attachments table
CREATE TABLE IF NOT EXISTS ticket_attachments (
    id        SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ticket_attachments_id        ON ticket_attachments(id);
CREATE INDEX IF NOT EXISTS ix_ticket_attachments_ticket_id ON ticket_attachments(ticket_id);

-- Ticket history table
CREATE TABLE IF NOT EXISTS ticket_history (
    id          SERIAL PRIMARY KEY,
    ticket_id   INTEGER NOT NULL REFERENCES tickets(id),
    action      VARCHAR(50) NOT NULL,
    description TEXT,
    old_status  VARCHAR(20),
    new_status  VARCHAR(20),
    actor_id    INTEGER,
    actor_name  VARCHAR(100),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ticket_history_id        ON ticket_history(id);
CREATE INDEX IF NOT EXISTS ix_ticket_history_ticket_id ON ticket_history(ticket_id);
