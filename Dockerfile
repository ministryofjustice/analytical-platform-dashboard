FROM public.ecr.aws/docker/library/node:22.3.0 AS build-node

WORKDIR /
COPY package.json package-lock.json ./
COPY assets/scss/app.scss ./assets/scss/app.scss

RUN npm install \
    && npm run css

FROM public.ecr.aws/docker/library/python:3.12-alpine3.19 AS base

RUN apk add --no-cache --virtual .build-deps \
    libffi-dev=3.4.4-r3 \
    gcc=13.2.1_git20231014-r0 \
    musl-dev=1.2.4_git20230717-r4 \
    && apk add --no-cache libpq-dev=16.3-r0

WORKDIR /app

RUN mkdir --parents static/assets/fonts \
    && mkdir --parents static/assets/images \
    && mkdir --parents static/assets/js

COPY --from=build-node static/app.css static/app.css
COPY --from=build-node node_modules/govuk-frontend/dist/govuk/assets/fonts/. static/assets/fonts
COPY --from=build-node node_modules/govuk-frontend/dist/govuk/assets/images/. static/assets/images
COPY --from=build-node node_modules/govuk-frontend/dist/govuk/all.bundle.js static/assets/js/govuk.js
COPY scripts/container/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY requirements.txt manage.py ./
COPY ap ap
COPY tests tests

RUN pip install --no-cache-dir --requirement requirements.txt \
    && chmod +x /usr/local/bin/entrypoint.sh \
    && python manage.py collectstatic --noinput --ignore=*.scss \
    && apk del .build-deps

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["run"]
