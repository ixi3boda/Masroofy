package com.masroofy.voice;

/** Body of POST /api/voice-expenses/parse-text: {"text": "...", "reference_time": "...", "extractor": "rules"} */
public record ParseTextRequest(String text, String referenceTime, String extractor) {
}
