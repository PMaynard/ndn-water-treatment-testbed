FROM openjdk:8-jdk
MAINTAINER Peter Maynard <pete@port22.co.uk>

RUN mkdir -p /opt/mango
COPY vendor/m2m2-core.zip /tmp/
RUN unzip /tmp/m2m2-core.zip -d /opt/mango \
    && rm  /tmp/m2m2-core.zip

ENV MA_HOME /opt/mango
ENV MA_CP $MA_HOME/overrides/classes:$MA_HOME/classes:$MA_HOME/overrides/properties:$MA_HOME/overrides/lib/*:$MA_HOME/lib/*

EXPOSE 8080

ENTRYPOINT exec java -server -cp $MA_CP -Dma.home=$MA_HOME -Djava.library.path=$MA_HOME/overrides/lib:$MA_HOME/lib:/usr/lib/jni/:$PATH com.serotonin.m2m2.Main
