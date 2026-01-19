# Dockerfile for running Metanome SPIDER with Java 11
FROM eclipse-temurin:11-jre-focal

# Install dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy JAR files
COPY metanome-cli-1.2-SNAPSHOT.jar /app/
COPY SPIDER-1.2-SNAPSHOT.jar /app/

# Set the entrypoint to run SPIDER
ENTRYPOINT ["java", "-cp", "/app/metanome-cli-1.2-SNAPSHOT.jar:/app/SPIDER-1.2-SNAPSHOT.jar", "de.metanome.cli.App"]
