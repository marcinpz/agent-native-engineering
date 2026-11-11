# Illustrative only: neither the base image nor JAR is built/resolved by adoption.
FROM eclipse-temurin:17-jre
WORKDIR /app
COPY target/adoption-fixture-0.0.1-SNAPSHOT.jar /app/service.jar
ENV PORT=8080
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "/app/service.jar"]
