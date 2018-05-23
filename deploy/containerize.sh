#!/bin/bash

if [ "$TRAVIS_PYTHON_VERSION" != "3.5" ]; then
    echo "Only deploy on production Python build"
    exit 0
fi

export ORGANIZATION="helsinki"

export IMAGE="respa"

export REPO="$ORGANIZATION/$IMAGE"

export COMMIT=${TRAVIS_COMMIT::7}

export BRANCH=${TRAVIS_BRANCH//\//_}

echo "Building image"
docker build -t $IMAGE .

docker login -u "$DOCKER_USERNAME" -p "$DOCKER_PASSWORD"

docker run --rm $IMAGE /bin/bash -c "pytest --cov . resources respa_exchange caterings"

echo "Tagging branch " "$TRAVIS_BRANCH"
docker tag $IMAGE "$REPO:$COMMIT"
docker tag "$REPO:$COMMIT" "$REPO:$BRANCH"
docker tag "$REPO:$COMMIT" "$REPO:travis-$TRAVIS_BUILD_NUMBER"
docker push "$REPO:$COMMIT"
docker push "$REPO:travis-$TRAVIS_BUILD_NUMBER"
docker push "$REPO:$BRANCH"

env
