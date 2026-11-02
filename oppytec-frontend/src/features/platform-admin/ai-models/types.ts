export type AiModelEngineTier = "SYSTEM_1_JEV" | "SYSTEM_2_LLM" | "EMBEDDING";

export type AiModelProvider = "google" | "anthropic" | "openai" | "oppytec" | (string & {});

export interface AiModelItem {
  readonly id: number;
  readonly model_slug: string;
  readonly display_name: string;
  readonly provider: AiModelProvider;
  readonly engine_tier: AiModelEngineTier;
  readonly input_cost_per_1m_usd: number | string;
  readonly cached_cost_per_1m_usd: number | string;
  readonly output_cost_per_1m_usd: number | string;
  readonly embedding_cost_per_1m_usd: number | string;
  readonly latency_p95_ms: number;
  readonly min_confidence_score: number | string | null;
  readonly max_context_tokens: number;
  readonly is_default: boolean;
  readonly is_fallback: boolean;
  readonly description: string | null;
  readonly is_enabled: boolean;
  readonly is_deleted: boolean;
  readonly created_at?: string;
  readonly updated_at?: string;
}

export interface AiModelCreatePayload {
  readonly model_slug: string;
  readonly display_name: string;
  readonly provider: string;
  readonly engine_tier: string;
  readonly input_cost_per_1m_usd: number;
  readonly cached_cost_per_1m_usd: number;
  readonly output_cost_per_1m_usd: number;
  readonly embedding_cost_per_1m_usd: number;
  readonly latency_p95_ms: number;
  readonly min_confidence_score?: number | null;
  readonly max_context_tokens: number;
  readonly is_default: boolean;
  readonly is_fallback: boolean;
  readonly description?: string | null;
  readonly is_enabled: boolean;
}

export interface AiModelUpdatePayload {
  readonly display_name?: string;
  readonly provider?: string;
  readonly engine_tier?: string;
  readonly input_cost_per_1m_usd?: number;
  readonly cached_cost_per_1m_usd?: number;
  readonly output_cost_per_1m_usd?: number;
  readonly embedding_cost_per_1m_usd?: number;
  readonly latency_p95_ms?: number;
  readonly min_confidence_score?: number | null;
  readonly max_context_tokens?: number;
  readonly is_default?: boolean;
  readonly is_fallback?: boolean;
  readonly description?: string | null;
  readonly is_enabled?: boolean;
}

export const MOCK_AI_MODELS: readonly AiModelItem[] = [
  {
    id: 1,
    model_slug: "gemini-3.8-flash",
    display_name: "Gemini 3.8 Flash",
    provider: "google",
    engine_tier: "SYSTEM_2_LLM",
    input_cost_per_1m_usd: 0.15,
    cached_cost_per_1m_usd: 0.0375,
    output_cost_per_1m_usd: 0.6,
    embedding_cost_per_1m_usd: 0.0,
    latency_p95_ms: 450,
    min_confidence_score: null,
    max_context_tokens: 1048576,
    is_default: true,
    is_fallback: false,
    description: "Google Gemini 3.8 Flash - Alta velocidad y bajo costo para razonamiento operativo general.",
    is_enabled: true,
    is_deleted: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: 2,
    model_slug: "gemini-4-argon",
    display_name: "Gemini 4 Argon",
    provider: "google",
    engine_tier: "SYSTEM_2_LLM",
    input_cost_per_1m_usd: 1.25,
    cached_cost_per_1m_usd: 0.3125,
    output_cost_per_1m_usd: 5.0,
    embedding_cost_per_1m_usd: 0.0,
    latency_p95_ms: 1200,
    min_confidence_score: null,
    max_context_tokens: 2097152,
    is_default: false,
    is_fallback: false,
    description: "Google Gemini 4 Argon - Razonamiento avanzado para análisis financiero y diagnósticos complejos.",
    is_enabled: true,
    is_deleted: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: 3,
    model_slug: "claude-3-7-sonnet",
    display_name: "Claude 3.7 Sonnet",
    provider: "anthropic",
    engine_tier: "SYSTEM_2_LLM",
    input_cost_per_1m_usd: 3.0,
    cached_cost_per_1m_usd: 0.75,
    output_cost_per_1m_usd: 15.0,
    embedding_cost_per_1m_usd: 0.0,
    latency_p95_ms: 1500,
    min_confidence_score: null,
    max_context_tokens: 200000,
    is_default: false,
    is_fallback: false,
    description: "Anthropic Claude 3.7 Sonnet - Razonamiento híbrido estándar y de pensamiento extendido.",
    is_enabled: true,
    is_deleted: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: 4,
    model_slug: "gpt-4o",
    display_name: "GPT-4o",
    provider: "openai",
    engine_tier: "SYSTEM_2_LLM",
    input_cost_per_1m_usd: 2.5,
    cached_cost_per_1m_usd: 1.25,
    output_cost_per_1m_usd: 10.0,
    embedding_cost_per_1m_usd: 0.0,
    latency_p95_ms: 800,
    min_confidence_score: null,
    max_context_tokens: 128000,
    is_default: false,
    is_fallback: true,
    description: "OpenAI GPT-4o - Modelo multimodal de respaldo empresarial y alta fidelidad.",
    is_enabled: true,
    is_deleted: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: 5,
    model_slug: "jev-fast-classifier",
    display_name: "JEV Fast Classifier",
    provider: "oppytec",
    engine_tier: "SYSTEM_1_JEV",
    input_cost_per_1m_usd: 0.0,
    cached_cost_per_1m_usd: 0.0,
    output_cost_per_1m_usd: 0.0,
    embedding_cost_per_1m_usd: 0.0,
    latency_p95_ms: 50,
    min_confidence_score: 0.85,
    max_context_tokens: 8192,
    is_default: false,
    is_fallback: false,
    description: "Motor local JEV System 1 determinista y sub-simbólico de ultra-baja latencia y cero costo de proveedor.",
    is_enabled: true,
    is_deleted: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
  {
    id: 6,
    model_slug: "text-embedding-004",
    display_name: "Text Embedding 004",
    provider: "google",
    engine_tier: "EMBEDDING",
    input_cost_per_1m_usd: 0.0,
    cached_cost_per_1m_usd: 0.0,
    output_cost_per_1m_usd: 0.0,
    embedding_cost_per_1m_usd: 0.025,
    latency_p95_ms: 100,
    min_confidence_score: null,
    max_context_tokens: 8192,
    is_default: false,
    is_fallback: false,
    description: "Google Text Embedding 004 - Embeddings vectoriales de 768 dimensiones para RAG.",
    is_enabled: true,
    is_deleted: false,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-03-01T00:00:00Z",
  },
];
