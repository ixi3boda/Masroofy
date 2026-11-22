# Finance backend (Spring Boot)

Fetches CBE exchange rates, EGX stock prices and the EGX30 index (TradingView, plus Yahoo
Finance and EGX when they answer), and gold and silver prices (gold-api.com, converted to EGP
with the CBE dollar rate) at **09:00, 15:00 and 21:00 Cairo time**, saves them in a
database, and serves them as JSON to the Android app.

The schedule is a Spring `@Scheduled` cron (`app.update.cron` in
`src/main/resources/application.properties`) with `zone = Africa/Cairo`, so it is right
whatever the server's timezone is, summer time included. It also runs once at startup.

## Run

    ./mvnw spring-boot:run            # development (Windows: mvnw.cmd spring-boot:run)
    ./mvnw package                    # runs the tests, builds target/finance-backend-1.0.0.jar
    java -jar target/finance-backend-1.0.0.jar

Needs Java 21 and PostgreSQL. You don't need Maven installed: `mvnw` downloads it the first time.

Create the database once (in `psql`, as the `postgres` user):

    CREATE USER finance WITH PASSWORD 'choose-a-password';
    CREATE DATABASE finance OWNER finance;

Then start the server with the password in `DB_PASSWORD` (and `DB_URL` / `DB_USER` if yours
differ from `jdbc:postgresql://localhost:5432/finance` / `finance`):

    DB_PASSWORD=choose-a-password ./mvnw spring-boot:run              # macOS / Linux
    $env:DB_PASSWORD="choose-a-password"; .\mvnw.cmd spring-boot:run  # Windows PowerShell

The tables are created on the first start. Run **one** copy of the server: two copies
would both run the schedule.

## API (all GET, dates are YYYY-MM-DD, from/to default to the last 30 days)

| Path | Returns |
|---|---|
| `/api/fx/latest` | newest rate for every currency |
| `/api/fx?currency=US Dollar&from=&to=` | rate history (currency optional) |
| `/api/stocks/latest` | newest price for every ticker and EGX30 |
| `/api/stocks?ticker=COMI.CA&from=&to=` | price history for one ticker |
| `/api/metals/latest` | newest gold and silver prices together (404 before the first) |
| `/api/metals?from=&to=` | gold and silver history, one entry per day |
| `/api/status` | how each source did in the last update |

Example: `{"date":"2026-11-20","currency":"US Dollar","buy":47.55,"sell":47.65,"source":"CBE","fetchedAt":"2026-11-20T07:00:02Z"}`

### Gold and silver

    {"date":"2026-11-22","pricedAt":"2026-11-22T04:26:39",
     "gold":  {"ounceUsd":3539.0,"24":6122.67,"21":5357.33,"18":4592.0,"pound":42858.67},
     "silver":{"ounceUsd":41.08,"999":71.0,"925":65.74,"800":56.86},
     "usdEgp":53.81075,"usdEgpDate":"2026-11-19","source":"gold-api.com","fetchedAt":"..."}

World prices come from gold-api.com (`https://api.gold-api.com/price/XAU` for gold,
`/price/XAG` for silver, US$ per troy ounce). They are turned into EGP per gram with the newest
CBE US Dollar rate (average of buy and sell): 24K = ounce x rate / 31.1035; 21K and 18K are 21/24
and 18/24 of that; the gold pound is 8 g of 21K. Silver 999, 925 and 800 are 99.9%, 92.5% and 80%
pure. These are world-market values: shop prices in Egypt are usually a little higher, and
jewellery adds workmanship. `pricedAt` is when gold-api.com last updated the gold price (Cairo time).

## Android (Retrofit, Kotlin)

```kotlin
data class FxRate(val date: String, val currency: String, val buy: Double, val sell: Double)
data class StockPrice(val date: String, val ticker: String, val open: Double?, val high: Double?,
                      val low: Double?, val close: Double, val volume: Long?)
// gold:   keys "ounceUsd", "24", "21", "18", "pound"   silver: keys "ounceUsd", "999", "925", "800"
data class Metals(val date: String, val pricedAt: String?, val gold: Map<String, Double>,
                  val silver: Map<String, Double>, val usdEgp: Double?, val usdEgpDate: String?)

interface FinanceApi {
    @GET("api/fx/latest") suspend fun fxLatest(): List<FxRate>
    @GET("api/fx") suspend fun fx(@Query("currency") currency: String? = null,
                                  @Query("from") from: String? = null,
                                  @Query("to") to: String? = null): List<FxRate>
    @GET("api/stocks/latest") suspend fun stocksLatest(): List<StockPrice>
    @GET("api/stocks") suspend fun stocks(@Query("ticker") ticker: String,
                                          @Query("from") from: String? = null,
                                          @Query("to") to: String? = null): List<StockPrice>
    @GET("api/metals/latest") suspend fun metalsLatest(): Metals
    @GET("api/metals") suspend fun metals(@Query("from") from: String? = null,
                                          @Query("to") to: String? = null): List<Metals>
}

val api = Retrofit.Builder()
    .baseUrl("https://your-server.example.com/")   // emulator + local server: http://10.0.2.2:8080/
    .addConverterFactory(GsonConverterFactory.create())
    .build()
    .create(FinanceApi::class.java)

// Example: val m = api.metalsLatest(); val gram21 = m.gold["21"]; val silver999 = m.silver["999"]
```

Use HTTPS in production; Android blocks plain `http://` unless you allow it.
