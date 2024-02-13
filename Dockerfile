FROM public.ecr.aws/docker/library/node:20.11.0 AS build-node

WORKDIR /
COPY package.json package-lock.json ./
COPY controlpanel/interfaces/web/static/app.scss ./controlpanel/interfaces/web/static/app.scss

RUN npm install \
    && npm run css

FROM public.ecr.aws/docker/library/python:3.11-alpine3.18 AS final

RUN apk add --no-cache --virtual .build-deps \
    libffi-dev=3.4.4-r2 \
    gcc=12.2.1_git20220924-r10 \
    musl-dev=1.2.4-r2 \
    && apk add --no-cache libpq-dev=15.5-r0

WORKDIR /controlpanel

RUN mkdir --parents static/assets/fonts \
    && mkdir --parents static/assets/images \
    && mkdir --parents static/assets/js

COPY --from=build-node static/app.css static/app.css
COPY --from=build-node node_modules/govuk-frontend/govuk/assets/fonts/. static/assets/fonts
COPY --from=build-node node_modules/govuk-frontend/govuk/assets/images/. static/assets/images
COPY --from=build-node node_modules/govuk-frontend/govuk/all.js static/assets/js/govuk.js
COPY scripts/container/entrypoint.sh /usr/local/bin/entrypoint.sh
COPY requirements.txt manage.py ./
COPY controlpanel controlpanel
COPY tests tests

RUN pip install --no-cache-dir --requirement requirements.txt \
    && chmod +x /usr/local/bin/entrypoint.sh \
    && python manage.py collectstatic --noinput --ignore=*.scss \
    && apk del .build-deps

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["run"]
