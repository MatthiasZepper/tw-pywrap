

# Step 1: Build Tower CLI development version
FROM ghcr.io/graalvm/native-image-community:17-muslib AS build-tower-cli

# Provide your Github user name and a token with the build command:
# The token only requires read:packages scope
# docker build --build-arg GITHUB_USERNAME=<myusername> --build-arg GITHUB_TOKEN=<mytoken> -t tw-pywrap:dev .
ARG GITHUB_USERNAME
ARG GITHUB_TOKEN
ARG PLATFORM
ENV GITHUB_USERNAME=$GITHUB_USERNAME
ENV GITHUB_TOKEN=$GITHUB_TOKEN
ENV PLATFORM=${PLATFORM:-"linux-x86_64"}

WORKDIR "/tw-cli"
RUN microdnf -y install wget unzip
RUN wget "https://github.com/seqeralabs/tower-cli/archive/refs/heads/master.zip" && \
    unzip "master.zip" && \
    cd "./tower-cli-master" && \
    ./gradlew nativeCompile

# Step 2: Python setup and installation of tw-pywrap
FROM python:3.10-alpine

COPY --from=build-tower-cli /tw-cli/tower-cli-master/build/native/nativeCompile/tw /usr/local/bin/tw
ENV PATH=/usr/local/bin/tw:$PATH
#RUN chmod +x /usr/local/bin/tw

RUN apk update && apk --no-cache add bash ca-certificates && \
    pip install pyyaml>=6.0 tw-pywrap

CMD [ "/bin/bash", "-l","-c","tw-pywrap","-h"]
LABEL maintainer='https://github.com/seqeralabs/tw-pywrap'

# run with 
# docker run -e TOWER_ACCESS_TOKEN=<mytoweraccesstoken> tw-pywrap:dev