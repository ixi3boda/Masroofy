package com.masroofy;

import com.masroofy.transaction.TransactionRepository;
import com.masroofy.voice.VoiceServiceClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.ResourceAccessException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.ZoneId;

import static org.assertj.core.api.Assertions.assertThat;
import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.hasSize;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/** Whole API on an in-memory database; the Python voice service is replaced by a mock. */
@SpringBootTest
@AutoConfigureMockMvc
class ApiTest {

    private static final JsonMapper JSON = JsonMapper.builder().build();

    @Autowired
    MockMvc mvc;

    @Autowired
    TransactionRepository repository;

    @MockitoBean
    VoiceServiceClient voice;

    @BeforeEach
    void emptyDatabase() {
        repository.deleteAll();
    }

    /** What the Python service returns from /v1/expenses/confirm (shortened). */
    private static JsonNode pythonConfirmed(double asrMs) {
        return JSON.readTree("""
                {"id": 7, "transaction_type": "expense", "amount": 160.0, "currency": "EGP", "merchant": "Uber",
                 "category": "transport", "date": "2026-11-26", "time": "21:30", "payment_method": "card",
                 "note": null, "transcript": "دفعت 150 جنيه في Uber امبارح", "language": "mixed",
                 "extraction_method": "hybrid:rules", "user_edited_fields": ["amount", "payment_method"],
                 "timings_ms": {"asr": %s, "total": 3200.0}}
                """.formatted(asrMs));
    }

    private String create(String body) throws Exception {
        return mvc.perform(post("/api/transactions").contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().isCreated())
                .andReturn().getResponse().getContentAsString();
    }

    // ---------------- voice ----------------

    @Test
    void confirmSavesTheVoiceTransaction() throws Exception {
        when(voice.confirm(any())).thenReturn(pythonConfirmed(3100.0));

        mvc.perform(post("/api/voice-expenses/confirm").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"draft\": {}, \"corrections\": {\"amount\": \"160\"}}"))
                .andExpect(status().isCreated())
                .andExpect(header().string("Location", containsString("/api/transactions/")))
                .andExpect(jsonPath("$.id").isNumber())
                .andExpect(jsonPath("$.amount").value(160.0))
                .andExpect(jsonPath("$.merchant").value("Uber"))
                .andExpect(jsonPath("$.date").value("2026-11-26"))
                .andExpect(jsonPath("$.time").value("21:30"))
                .andExpect(jsonPath("$.payment_method").value("card"))
                .andExpect(jsonPath("$.source").value("voice"))
                .andExpect(jsonPath("$.edited_fields", hasSize(2)))
                .andExpect(jsonPath("$.voice_record_id").value(7));

        assertThat(repository.count()).isEqualTo(1);
        mvc.perform(get("/api/transactions"))
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].transcript").value("دفعت 150 جنيه في Uber امبارح"));
    }

    @Test
    void typedSentenceIsSavedWithSourceText() throws Exception {
        when(voice.confirm(any())).thenReturn(pythonConfirmed(0.0));
        mvc.perform(post("/api/voice-expenses/confirm").contentType(MediaType.APPLICATION_JSON).content("{\"draft\": {}}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.source").value("text"));
    }

    @Test
    void voiceServiceErrorIsPassedThroughAndNothingIsSaved() throws Exception {
        byte[] body = "{\"error_code\":\"amount_required\",\"message\":\"An amount is required before saving.\"}"
                .getBytes(StandardCharsets.UTF_8);
        when(voice.confirm(any())).thenThrow(HttpClientErrorException.create(
                HttpStatus.UNPROCESSABLE_CONTENT, "Unprocessable", HttpHeaders.EMPTY, body, StandardCharsets.UTF_8));

        mvc.perform(post("/api/voice-expenses/confirm").contentType(MediaType.APPLICATION_JSON).content("{\"draft\": {}}"))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.error_code").value("amount_required"));
        assertThat(repository.count()).isZero();
    }

    @Test
    void voiceServiceDownGives503() throws Exception {
        when(voice.parseText(any(), any(), any())).thenThrow(new ResourceAccessException("Connection refused"));
        mvc.perform(post("/api/voice-expenses/parse-text").contentType(MediaType.APPLICATION_JSON).content("{\"text\": \"paid 80\"}"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.error_code").value("voice_service_unavailable"));
    }

    @Test
    void healthReportsDatabaseAndVoiceService() throws Exception {
        when(voice.health()).thenThrow(new ResourceAccessException("Connection refused"));
        mvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("degraded"))
                .andExpect(jsonPath("$.database", containsString("ok")))
                .andExpect(jsonPath("$.voice_service", containsString("unavailable")));
    }

    // ---------------- transactions ----------------

    @Test
    void manualTransactionGetsDefaults() throws Exception {
        String today = LocalDate.now(ZoneId.of("Africa/Cairo")).toString();
        mvc.perform(post("/api/transactions").contentType(MediaType.APPLICATION_JSON).content("{\"amount\": 50}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.amount").value(50.0))
                .andExpect(jsonPath("$.transaction_type").value("expense"))
                .andExpect(jsonPath("$.currency").value("EGP"))
                .andExpect(jsonPath("$.category").value("other"))
                .andExpect(jsonPath("$.payment_method").value("unknown"))
                .andExpect(jsonPath("$.date").value(today))
                .andExpect(jsonPath("$.source").value("manual"));

        mvc.perform(post("/api/transactions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": 9000, \"transaction_type\": \"income\"}"))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.category").value("income"));
    }

    @Test
    void invalidTransactionsAreRejected() throws Exception {
        mvc.perform(post("/api/transactions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": -5, \"payment_method\": \"visa\", \"currency\": \"EGYPT\"}"))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.error_code").value("validation_error"))
                .andExpect(jsonPath("$.message", containsString("amount:")))
                .andExpect(jsonPath("$.message", containsString("payment_method:")))
                .andExpect(jsonPath("$.message", containsString("currency:")));

        mvc.perform(post("/api/transactions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": 5, \"category\": \"food\"}"))
                .andExpect(status().isUnprocessableContent())
                .andExpect(jsonPath("$.error_code").value("invalid_field"));

        mvc.perform(post("/api/transactions").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": 5, \"time\": \"25:99\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error_code").value("invalid_json"));
        assertThat(repository.count()).isZero();
    }

    @Test
    void listFiltersAndMonthlySummary() throws Exception {
        create("{\"amount\": 100, \"category\": \"transport\", \"date\": \"2026-11-03\"}");
        create("{\"amount\": 250.5, \"category\": \"groceries\", \"date\": \"2026-11-20\"}");
        create("{\"amount\": 50, \"category\": \"transport\", \"date\": \"2026-11-25\"}");
        create("{\"amount\": 9000, \"transaction_type\": \"income\", \"date\": \"2026-11-01\"}");
        create("{\"amount\": 30, \"currency\": \"usd\", \"category\": \"subscriptions\", \"date\": \"2026-11-10\"}");
        create("{\"amount\": 999, \"category\": \"travel\", \"date\": \"2026-10-31\"}");

        mvc.perform(get("/api/transactions").param("from", "2026-11-01").param("to", "2026-11-30").param("category", "transport"))
                .andExpect(jsonPath("$", hasSize(2)))
                .andExpect(jsonPath("$[0].date").value("2026-11-25"));
        mvc.perform(get("/api/transactions").param("limit", "2")).andExpect(jsonPath("$", hasSize(2)));
        mvc.perform(get("/api/transactions").param("limit", "0")).andExpect(status().isUnprocessableContent());
        mvc.perform(get("/api/transactions").param("from", "yesterday")).andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.error_code").value("invalid_parameter"));

        mvc.perform(get("/api/transactions/summary").param("month", "2026-11"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.month").value("2026-11"))
                .andExpect(jsonPath("$.currencies", hasSize(2)))
                .andExpect(jsonPath("$.currencies[0].currency").value("EGP"))
                .andExpect(jsonPath("$.currencies[0].total_expense").value(400.5))
                .andExpect(jsonPath("$.currencies[0].total_income").value(9000.0))
                .andExpect(jsonPath("$.currencies[0].net").value(8599.5))
                .andExpect(jsonPath("$.currencies[0].expenses_by_category[0].category").value("groceries"))
                .andExpect(jsonPath("$.currencies[0].expenses_by_category[1].total").value(150.0))
                .andExpect(jsonPath("$.currencies[1].currency").value("USD"));
    }

    @Test
    void updateAndDelete() throws Exception {
        long id = JSON.readTree(create("{\"amount\": 100, \"category\": \"transport\", \"date\": \"2026-11-03\"}"))
                .path("id").longValue();

        mvc.perform(put("/api/transactions/" + id).contentType(MediaType.APPLICATION_JSON)
                        .content("{\"amount\": 120, \"category\": \"fuel\", \"merchant\": \"Total\", \"time\": \"08:15\"}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.amount").value(120.0))
                .andExpect(jsonPath("$.category").value("fuel"))
                .andExpect(jsonPath("$.time").value("08:15"))
                .andExpect(jsonPath("$.date").value("2026-11-03"))   // no date sent = date kept
                .andExpect(jsonPath("$.source").value("manual"));

        mvc.perform(delete("/api/transactions/" + id)).andExpect(status().isNoContent());
        mvc.perform(get("/api/transactions/" + id))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error_code").value("not_found"));
        mvc.perform(delete("/api/transactions/" + id)).andExpect(status().isNotFound());
    }

    @Test
    void unknownUrlUsesTheSameErrorShape() throws Exception {
        mvc.perform(get("/api/nope"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.error_code").value("not_found"));
    }
}
