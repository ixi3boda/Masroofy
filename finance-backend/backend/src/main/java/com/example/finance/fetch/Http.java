package com.example.finance.fetch;

import org.jsoup.Connection;
import org.jsoup.Jsoup;

/** Shared settings for requests to the source websites. */
final class Http {
    static final String USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            + "(KHTML, like Gecko) Chrome/156.0.0.0 Safari/537.36";

    private Http() {}

    static Connection connect(String url) {
        return Jsoup.connect(url)
                .userAgent(USER_AGENT)
                .header("Accept-Language", "en-US,en;q=0.8")
                .timeout(30_000)
                .maxBodySize(10 * 1024 * 1024)
                .ignoreContentType(true);
    }
}
