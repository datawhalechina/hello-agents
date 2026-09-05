-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- God Logs table
CREATE TABLE IF NOT EXISTS god_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    god_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    details TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (god_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Personas table
CREATE TABLE IF NOT EXISTS personas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    title TEXT,
    bio TEXT,
    theories TEXT, -- JSON string
    stance TEXT,
    system_prompt TEXT,
    is_public BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Moderators table
CREATE TABLE IF NOT EXISTS moderators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    title TEXT DEFAULT '主持人',
    bio TEXT,
    system_prompt TEXT,
    greeting_template TEXT,
    closing_template TEXT,
    summary_template TEXT,
    creator_id INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Forums table
CREATE TABLE IF NOT EXISTS forums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic TEXT NOT NULL,
    creator_id INTEGER NOT NULL,
    moderator_id INTEGER,
    status TEXT DEFAULT 'active',
    summary_history TEXT DEFAULT '[]',
    ablation_flags TEXT DEFAULT '{}',
    start_time DATETIME,
    end_time DATETIME,
    duration_minutes INTEGER DEFAULT 30,
    FOREIGN KEY (creator_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (moderator_id) REFERENCES moderators(id)
);

-- Forum Participants table
CREATE TABLE IF NOT EXISTS forum_participants (
    forum_id INTEGER NOT NULL,
    persona_id INTEGER NOT NULL,
    thoughts_history TEXT DEFAULT '[]',
    PRIMARY KEY (forum_id, persona_id),
    FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE,
    FOREIGN KEY (persona_id) REFERENCES personas(id) ON DELETE CASCADE
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forum_id INTEGER NOT NULL,
    persona_id INTEGER,
    moderator_id INTEGER,
    speaker_name TEXT NOT NULL,
    content TEXT NOT NULL,
    turn_count INTEGER DEFAULT 0,
    thought TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE,
    FOREIGN KEY (persona_id) REFERENCES personas(id),
    FOREIGN KEY (moderator_id) REFERENCES moderators(id)
);

-- Observations table
CREATE TABLE IF NOT EXISTS observations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    forum_id INTEGER NOT NULL,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    left_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE
);

-- System Logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    forum_id INTEGER NOT NULL,
    level TEXT DEFAULT 'info',
    source TEXT,
    content TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (forum_id) REFERENCES forums(id) ON DELETE CASCADE
);
