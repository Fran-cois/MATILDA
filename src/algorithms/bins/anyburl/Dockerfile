FROM eclipse-temurin:17-jre-focal

WORKDIR /app

# Copy the AnyBURL jar
COPY AnyBURL-23-1x.jar /app/

# The entrypoint will use -cp with the Learn class
ENTRYPOINT ["java", "-Xmx15G", "-cp", "/app/AnyBURL-23-1x.jar", "de.unima.ki.anyburl.Learn"]
