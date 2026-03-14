"""JSON Schema 定义，用于约束 LLM 输出格式。"""

TOPIC_CLASSIFIER_SCHEMA = {
    "type": "object",
    "required": ["primary_topic", "secondary_topics", "content_type", "business_relevance"],
    "properties": {
        "primary_topic": {"type": "string"},
        "secondary_topics": {"type": "array", "items": {"type": "string"}},
        "content_type": {
            "type": "string",
            "enum": ["观点输出", "教程讲解", "案例分析", "行业分析", "产品推荐", "其他"]
        },
        "business_relevance": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "skip_reason": {"type": ["string", "null"]}
    },
    "additionalProperties": False
}

VIDEO_ANALYZER_SCHEMA = {
    "type": "object",
    "required": ["core_signals", "cognition_framework", "methodology_fragments", "high_value_quotes", "overall_quality"],
    "properties": {
        "core_signals": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["signal", "evidence", "confidence_score"],
                "properties": {
                    "signal": {"type": "string"},
                    "evidence": {"type": "string"},
                    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                }
            }
        },
        "cognition_framework": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["framework", "reasoning_chain", "confidence_score"],
                "properties": {
                    "framework": {"type": "string"},
                    "reasoning_chain": {"type": "string"},
                    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                }
            }
        },
        "methodology_fragments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["method", "applicable_scenario", "confidence_score"],
                "properties": {
                    "method": {"type": "string"},
                    "applicable_scenario": {"type": "string"},
                    "confidence_score": {"type": "number", "minimum": 0.0, "maximum": 1.0}
                }
            }
        },
        "high_value_quotes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["quote", "context"],
                "properties": {
                    "quote": {"type": "string"},
                    "context": {"type": "string"}
                }
            }
        },
        "overall_quality": {"type": "number", "minimum": 0.0, "maximum": 1.0}
    },
    "additionalProperties": False
}

AGGREGATOR_MODE1_SCHEMA = {
    "type": "object",
    "required": ["core_signals", "cognition_framework", "methodology_fragments",
                 "business_opportunities", "high_value_quotes", "insights_for_me", "quality_summary"],
    "properties": {
        "core_signals": {"type": "array", "items": {"type": "object"}},
        "cognition_framework": {"type": "array", "items": {"type": "object"}},
        "methodology_fragments": {"type": "array", "items": {"type": "object"}},
        "business_opportunities": {
            "type": "object",
            "properties": {
                "direction_judgment": {"type": "array", "items": {"type": "object"}},
                "verifiable_hypotheses": {"type": "array", "items": {"type": "object"}}
            }
        },
        "high_value_quotes": {"type": "array", "items": {"type": "object"}},
        "insights_for_me": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "quality_summary": {
            "type": "object",
            "properties": {
                "overall_confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                "low_quality_signals_count": {"type": "integer"},
                "notes": {"type": "string"}
            }
        }
    }
}

AGGREGATOR_MODE2_SCHEMA = {
    "type": "object",
    "required": ["trend_signals", "consensus_and_divergence", "common_methodology",
                 "business_opportunities", "high_value_quotes", "insights_for_me", "quality_summary"],
    "properties": {
        "trend_signals": {"type": "array", "items": {"type": "object"}},
        "consensus_and_divergence": {
            "type": "object",
            "properties": {
                "consensus": {"type": "array", "items": {"type": "object"}},
                "divergence": {"type": "array", "items": {"type": "object"}}
            }
        },
        "common_methodology": {"type": "array", "items": {"type": "object"}},
        "business_opportunities": {"type": "object"},
        "high_value_quotes": {"type": "array", "items": {"type": "object"}},
        "insights_for_me": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 5},
        "quality_summary": {"type": "object"}
    }
}
