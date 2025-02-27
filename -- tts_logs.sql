-- tts_logs 表
create table tts_logs (
    id bigint generated by default as identity primary key,
    text text not null,
    voice_id text,
    model text,
    duration float,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- llm_logs 表
create table llm_logs (
    id bigint generated by default as identity primary key,
    prompt text not null,
    response text not null,
    model text,
    tokens_used int,
    duration float,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- stt_logs 表
create table stt_logs (
    id bigint generated by default as identity primary key,
    audio_duration float,
    transcription text not null,
    model text,
    duration float,
    created_at timestamp with time zone default timezone('utc'::text, now())
);

-- API 使用记录表
CREATE TABLE usage_logs (
    id SERIAL PRIMARY KEY,
    api_key VARCHAR(255) NOT NULL,
    user_uuid VARCHAR(255) NOT NULL,      -- 关联到租户
    service_type VARCHAR(50) NOT NULL,     -- 'llm', 'tts', 'stt', 'vad'
    usage_amount FLOAT NOT NULL,           -- tokens for LLM, characters for TTS, seconds for STT
    cost FLOAT NOT NULL,                  -- 实际消耗的美元金额
    created_at timestamptz DEFAULT NOW(),
    request_id VARCHAR(255),
    model VARCHAR(255),
    status VARCHAR(50),                   -- 'success', 'error'
    error_message TEXT,
    FOREIGN KEY (api_key) REFERENCES apikeys(api_key),
    FOREIGN KEY (user_uuid) REFERENCES users(uuid)
);