FROM docker:29-cli AS docker-cli

FROM node:22-bookworm

# Supabase CLI invokes the Docker executable as well as accessing its socket.
# Copy only the client; all containers still run on the host's existing daemon.
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

