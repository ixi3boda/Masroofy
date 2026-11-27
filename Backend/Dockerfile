# ---- Build stage: compile and package the Spring Boot jar ------------------------------------------------
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /workspace

# Resolve dependencies first so they are cached until pom.xml changes.
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 mvn -B -q dependency:go-offline -DexcludeReactor=true || true

COPY src ./src
# Tests run outside Docker (`./mvnw test`) because they start their own PostgreSQL container.
RUN --mount=type=cache,target=/root/.m2 mvn -B -q -DskipTests package \
    && cp target/masroofy-backend-*.jar /workspace/app.jar

# ---- Runtime stage: JRE only, non-root user --------------------------------------------------------------
# eclipse-temurin:17-jre is multi-arch (amd64 + arm64/Apple Silicon); the -alpine variant is amd64 only.
FROM eclipse-temurin:17-jre
WORKDIR /app

COPY --from=build --chown=10001:10001 /workspace/app.jar /app/app.jar
USER 10001:10001

# Every setting is read from environment variables (see ../.env.example); nothing secret is baked in.
ENV PORT=8080 \
    TZ=UTC \
    JAVA_OPTS="-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError"

EXPOSE 8080

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD wget -qO- "http://127.0.0.1:${PORT}/actuator/health" | grep -q '"status":"UP"' || exit 1

ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
