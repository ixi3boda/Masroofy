# syntax=docker/dockerfile:1
# Finance backend image: builds the jar with Maven, then runs it on a small Java 21 runtime.
#   docker build -t finance-backend:local .

# ---- build --------------------------------------------------------------------------------
FROM maven:3.9-eclipse-temurin-21 AS build
WORKDIR /src
COPY pom.xml .
COPY src ./src
# Maven's downloads stay in a cache between builds (BuildKit, the default since Docker 23).
# Tests run with ./mvnw package outside Docker; skipped here to keep image builds fast.
RUN --mount=type=cache,target=/root/.m2 mvn -B -q -DskipTests package \
 && cp target/finance-backend-*.jar /src/app.jar

# ---- run ----------------------------------------------------------------------------------
FROM eclipse-temurin:21-jre-alpine
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
COPY --from=build /src/app.jar app.jar
USER app

ENV PORT=8080 \
    TZ=Africa/Cairo \
    JAVA_OPTS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"
EXPOSE 8080

# /api/status answers as soon as the web server is up (the first update runs in the background).
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -q -O /dev/null "http://127.0.0.1:${PORT}/api/status" || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
