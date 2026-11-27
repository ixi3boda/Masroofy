# Finance backend (Spring Boot)

Fetches exchange rates for every currency (AllRatesToday daily reference rate), EGX stock prices and
the EGX30 index (TradingView, plus Yahoo Finance and EGX when they answer), and gold and silver prices
(gold-api.com, converted to EGP with the dollar rate) at **09:00, 15:00 and 21:00 Cairo time**, saves
them in a database, and serves them as JSON to the Android app.

**Prices are saved per day for charts.** The tables `fx_rates`, `stock_prices` and `metal_prices`
hold the current price of each thing (one row per currency, per ticker, and one for gold and silver;
a price older than the saved one is ignored). Every saved price also goes into `price_history`, one
price per item per day: the day's latest, so the 3 runs of a day update the same point. Nothing is
fetched from the sources' history APIs: the history is what this backend has saved, day by day.

Upgrading from a version that kept every day in the three tables: at startup those days are copied
into `price_history` (so they show in the charts) and then removed from the three tables.

**Charts:** open **http://localhost:8080/charts.html** (or the "Charts" button on the main page).
Gold, silver, every currency and every stock, with 1M / 3M / 6M / 1Y / All ranges, a hover readout,
and a table view. The address remembers the chart, e.g. `/charts.html#gold/21/3M`.

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

Then start the server with the password in `DB_PASSWORD` (and `DB_URL` / `DB_USERNAME` if yours
differ from `jdbc:postgresql://localhost:5432/finance` / `finance`):

    DB_PASSWORD=choose-a-password ./mvnw spring-boot:run   # macOS / Linux
    $env:DB_PASSWORD="choose-a-password"; .\mvnw.cmd spring-boot:run  # Windows PowerShell

The tables are created on the first start. Then open **http://localhost:8080** in a browser for
today's prices and the savings calculator (the page's source code is in the separate
`prices-web` folder, React + TypeScript). Run **one** copy of the server: two copies
would both run the schedule.

## Run with Docker

Everything in containers: PostgreSQL and the backend. Needs Docker with Compose (Docker Desktop, or
Docker Engine 23+). From this folder:

    cp .env.example .env      # then set DB_PASSWORD (and the ports if 5432 / 8080 are taken)
    docker compose up --build

Then open http://localhost:8080 (or your `BACKEND_PORT`), and `/charts.html` for the charts.
The database lives in the `finance_db-data` volume, so prices and their history survive
`docker compose down` and rebuilds (`docker compose down -v` deletes it). The backend waits until
PostgreSQL is ready, and both restart on their own unless you stop them. `DB_PORT` publishes
PostgreSQL on your computer too (for psql or a GUI); the backend reaches it inside Docker as `db:5432`.

| File | What it is |
|---|---|
| `Dockerfile` | builds the jar with Maven (tests skipped), runs it on Java 21 (Alpine, non-root, healthcheck on `/api/status`) |
| `docker-compose.yml` | the two services, the volume, and the settings read from `.env` |
| `.env.example` | the settings to copy into `.env` (`.env` is git-ignored) |

Logs: `docker compose logs -f backend`. Only one backend should run (it runs the schedule).

## API (all GET; `date` in each answer is the day the price is for, YYYY-MM-DD)

| Path | Returns |
|---|---|
| `/api/fx/latest` | current rate of every currency |
| `/api/stocks/latest` | current price of every ticker and EGX30 |
| `/api/metals/latest` | current gold and silver prices together (404 before the first) |
| `/api/prices` | the current price of everything (used by the web page) |
| `/api/history?kind=gold&item=21&from=&to=` | one item's price per day, oldest first (used by the charts) |
| `/api/status` | how each source did in the last update |

`/api/history`: `kind` is `gold`, `silver`, `currencies` or `stocks`; `item` is the key that
`/api/prices` uses (`24`, `21`, `18`, `pound`; `999`, `925`, `800`; `USD`, `EUR`, ...; `COMI.CA`, ...,
`EGX30`). `from` and `to` (YYYY-MM-DD) are optional; without `from` you get every saved day.
Answer: `[{"date":"2026-11-25","price":5341.2},{"date":"2026-11-26","price":5357.26}]`. Prices are
EGP (per gram for gold and silver, per coin for the pound, per 1 unit of a currency, per share;
points for EGX30). An unknown `kind` gives 400.

Example: `{"date":"2026-11-26","currency":"USD","buy":54.8438,"sell":54.8438,"source":"allratestoday","fetchedAt":"..."}`

### Exchange rates

Rates in EGP for **every currency** in the AllRatesToday daily reference rate (160+), per 1 unit of
the currency (also the yen). Each run calls `https://allratestoday.com/api/open/reference-rate`
(`app.fx.allrates-url`). It is free and needs **no key**. The answer is one table per day, sampled at
16:00 London, with USD as the base (`{"rate_date":"2026-11-26","base":"USD","rates":[{"quote":"EGP","value":54.8438},...]}`),
so EGP per 1 unit of X = value(EGP) / value(X), and USD = value(EGP). It is a single median rate with
no spread, so `buy` and `sell` are the same number. The table changes once a day, so the three runs
of a day usually save the same rates; `date` is the table's `rate_date`. Currencies that drop out of
the table are deleted.

AllRatesToday says this is a reference rate, not the WM/Refinitiv fix or a regulated benchmark, and
not for settling financial instruments. Its terms: public pages that show the rates need a visible
link to allratestoday.com (the web page has one). Dated tables and history are paid plans only.

### Gold and silver

    {"date":"2026-11-22","pricedAt":"2026-11-22T04:26:39",
     "gold":  {"ounceUsd":3539.0,"24":6122.67,"21":5357.33,"18":4592.0,"pound":42858.67},
     "silver":{"ounceUsd":41.08,"999":71.0,"925":65.74,"800":56.86},
     "usdEgp":53.81075,"usdEgpDate":"2026-11-19","source":"gold-api.com","fetchedAt":"..."}

World prices come from gold-api.com (`https://api.gold-api.com/price/XAU` for gold,
`/price/XAG` for silver, US$ per troy ounce). They are turned into EGP per gram with the newest
USD rate (average of buy and sell): 24K = ounce x rate / 31.1035; 21K and 18K are 21/24
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
    @GET("api/stocks/latest") suspend fun stocksLatest(): List<StockPrice>
    @GET("api/metals/latest") suspend fun metalsLatest(): Metals
    @GET("api/history") suspend fun history(@Query("kind") kind: String, @Query("item") item: String,
                                            @Query("from") from: String? = null,
                                            @Query("to") to: String? = null): List<Point>
}
data class Point(val date: String, val price: Double)   // e.g. api.history("gold", "21") for a chart

val api = Retrofit.Builder()
    .baseUrl("https://your-server.example.com/")   // emulator + local server: http://10.0.2.2:8080/
    .addConverterFactory(GsonConverterFactory.create())
    .build()
    .create(FinanceApi::class.java)

// Example: val m = api.metalsLatest(); val gram21 = m.gold["21"]; val silver999 = m.silver["999"]
```

Use HTTPS in production; Android blocks plain `http://` unless you allow it.
