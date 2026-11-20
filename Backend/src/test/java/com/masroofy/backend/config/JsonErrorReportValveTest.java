package com.masroofy.backend.config;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

class JsonErrorReportValveTest {

    @Test
    void quotedValuesAreValidJsonEvenWithControlCharacters() throws Exception {
        String path = "/api/v1/users/me\u0000\"\\x";
        JsonNode node = new ObjectMapper().readTree("{\"path\":" + JsonErrorReportValve.quote(path) + "}");

        assertThat(node.path("path").asText()).isEqualTo(path);
    }
}
