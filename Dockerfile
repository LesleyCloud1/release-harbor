FROM python:3.12-slim
WORKDIR /app
RUN useradd --uid 10001 --create-home harbor && mkdir /app/.harbor && chown harbor:harbor /app/.harbor
COPY --chown=harbor:harbor harbor ./harbor
USER 10001:10001
EXPOSE 8088
CMD ["python", "-m", "harbor.server", "--host", "0.0.0.0"]
