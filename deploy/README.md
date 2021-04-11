
# Respa Deployment

Use Uwsgi as per sample files, both ini or environment variables.

From Respa project root folder:

    uwsgi --ini deploy/uwsgi.ini

Or with environment variable file:

    (set -o allexport; source deploy/uwsgi.env; set +o allexport; uwsgi)

Variables are more useful with Docker or Kubernetes based environments. Hat tip to https://stackoverflow.com/a/30969768 for `allexport` trick.
