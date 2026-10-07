-- ====================================================================
-- PostgreSQL Database Table Definition: apt_users_b
-- Connection URL: postgresql://apt_auth_app:Auth@intern_aepttas@100.112.49.39:5432/aepttas_xdr
-- ====================================================================

CREATE TABLE IF NOT EXISTS apt_users_b (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'PARENT',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for high-performance login queries on email
CREATE INDEX IF NOT EXISTS idx_apt_users_b_email ON apt_users_b (email);

-- Sample SQL INSERT query used by backend to insert a new user:
-- INSERT INTO apt_users_b (username, name, email, password_hash, role) 
-- VALUES ('venuk', 'Venuk', 'venuk@gmail.com', '$2b$12$eImiTXuWVxfM37uY4JANjOQe32a...', 'PARENT');
