-- Privacy Eraser Database Schema
-- PostgreSQL 15+

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    -- Subscription
    plan VARCHAR(50) DEFAULT 'free',
    stripe_customer_id VARCHAR(255),
    subscription_ends_at TIMESTAMP,

    -- Status
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

-- User profiles (personal info to protect)
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE CASCADE,

    -- Name variations
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    middle_name VARCHAR(100),
    maiden_name VARCHAR(100),
    nicknames TEXT[],

    -- Contact
    emails TEXT[],
    phone_numbers TEXT[],

    -- Addresses
    addresses JSONB,

    -- Other
    date_of_birth DATE,
    relatives TEXT[],

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);

-- Data brokers
CREATE TABLE data_brokers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    domain VARCHAR(255) NOT NULL UNIQUE,
    category VARCHAR(50),

    -- Search
    search_url_pattern VARCHAR(500),

    -- Opt-out info
    opt_out_url VARCHAR(500),
    opt_out_method VARCHAR(50) DEFAULT 'form',
    opt_out_email VARCHAR(255),
    opt_out_instructions TEXT,

    -- Requirements
    requires_verification BOOLEAN DEFAULT false,
    requires_id BOOLEAN DEFAULT false,
    processing_days INTEGER DEFAULT 30,

    -- Automation
    can_automate BOOLEAN DEFAULT false,
    form_selectors JSONB,
    captcha_type VARCHAR(50),

    -- Rating
    difficulty INTEGER DEFAULT 3,

    -- Status
    is_active BOOLEAN DEFAULT true,
    last_verified TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_data_brokers_domain ON data_brokers(domain);
CREATE INDEX idx_data_brokers_category ON data_brokers(category);

-- Broker exposures (found data)
CREATE TABLE broker_exposures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    broker_id UUID REFERENCES data_brokers(id) ON DELETE CASCADE,

    status VARCHAR(50) DEFAULT 'found',
    profile_url VARCHAR(500),
    data_found JSONB,
    screenshot_url VARCHAR(500),

    first_detected_at TIMESTAMP DEFAULT NOW(),
    last_checked_at TIMESTAMP DEFAULT NOW(),
    removed_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_broker_exposures_user_id ON broker_exposures(user_id);
CREATE INDEX idx_broker_exposures_broker_id ON broker_exposures(broker_id);
CREATE INDEX idx_broker_exposures_status ON broker_exposures(status);

-- Removal requests
CREATE TABLE removal_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    broker_id UUID REFERENCES data_brokers(id) ON DELETE CASCADE,
    exposure_id UUID REFERENCES broker_exposures(id) ON DELETE SET NULL,

    request_type VARCHAR(50) DEFAULT 'opt_out',
    status VARCHAR(50) DEFAULT 'pending',

    submitted_at TIMESTAMP,
    confirmation_number VARCHAR(100),
    expected_completion DATE,
    completed_at TIMESTAMP,

    instructions TEXT,
    requires_user_action BOOLEAN DEFAULT false,
    method_used VARCHAR(50),
    notes TEXT,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_removal_requests_user_id ON removal_requests(user_id);
CREATE INDEX idx_removal_requests_status ON removal_requests(status);

-- Alerts
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,

    alert_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) DEFAULT 'medium',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    source_url VARCHAR(500),

    is_read BOOLEAN DEFAULT false,
    is_dismissed BOOLEAN DEFAULT false,
    read_at TIMESTAMP,

    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_is_read ON alerts(is_read);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_data_brokers_updated_at
    BEFORE UPDATE ON data_brokers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_broker_exposures_updated_at
    BEFORE UPDATE ON broker_exposures
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_removal_requests_updated_at
    BEFORE UPDATE ON removal_requests
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
