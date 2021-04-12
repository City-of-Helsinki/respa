
# Respa Deployment

Install requirements in this folder to Python virtual environment or use Dockerfile build from Respa root folder's context. 

Use Uwsgi as per sample files, both ini or environment variables.

From Respa root folder:

    uwsgi --ini deploy/uwsgi.ini

Or with environment variables, here from sample file, executed inside Respa root folder:

    (set -o allexport; source deploy/uwsgi.env; set +o allexport; uwsgi)

Environment variables are more useful with Docker or Kubernetes based environments. Hat tip to https://stackoverflow.com/a/30969768 for `allexport` trick.
