-- PostgreSQL schema for E-Ticket application

-- Users table (for local reference, auth is via Oracle)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(100),
    department VARCHAR(50),
    role VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_users_id ON users(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username);

-- Tickets table
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    ticket_id VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    department VARCHAR(50),
    category VARCHAR(50),
    priority VARCHAR(20),
    status VARCHAR(20) DEFAULT 'new',
    requester_id INTEGER,  -- Oracle person_id, no FK (users from Oracle)
    requester_name VARCHAR(100),
    requester_fullname VARCHAR(200),  -- last_name from Oracle per_people_f
    team_id VARCHAR(50),  -- Oracle PER_ALL_ASSIGNMENTS_F.ass_attribute30
    team_desc VARCHAR(200),  -- Oracle fnd_flex_values_vl.description
    pic_id INTEGER,  -- Oracle person_id, no FK (users from Oracle)
    pic_name VARCHAR(100),
    pic_fullname VARCHAR(200),  -- last_name from Oracle per_people_f
    pic_assigned_at TIMESTAMPTZ,
    resolution TEXT,
    resolution_status VARCHAR(20),
    cancel_reason TEXT,
    cancelled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_tickets_id ON tickets(id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_tickets_ticket_id ON tickets(ticket_id);
CREATE INDEX IF NOT EXISTS ix_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS ix_tickets_department ON tickets(department);

-- Ticket attachments table
CREATE TABLE IF NOT EXISTS ticket_attachments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    file_name VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ticket_attachments_id ON ticket_attachments(id);
CREATE INDEX IF NOT EXISTS ix_ticket_attachments_ticket_id ON ticket_attachments(ticket_id);

-- Ticket history table
CREATE TABLE IF NOT EXISTS ticket_history (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id),
    action VARCHAR(50) NOT NULL,
    description TEXT,
    old_status VARCHAR(20),
    new_status VARCHAR(20),
    actor_id INTEGER,  -- Oracle person_id, no FK (users from Oracle)
    actor_name VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ticket_history_id ON ticket_history(id);
CREATE INDEX IF NOT EXISTS ix_ticket_history_ticket_id ON ticket_history(ticket_id);

-- Insert default admin user (password: admin123)
INSERT INTO users (username, password, full_name, department, role, is_active)
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G', 'Administrator', 'IT', 'admin', true)
ON CONFLICT (username) DO NOTHING;
