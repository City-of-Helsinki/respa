#!/bin/bash

if [ -z "$DOCKER_USERNAME" ]; then
    echo "Need Docker login credentials to proceed"
    exit 0
fi

if [ "$TRAVIS_PYTHON_VERSION" != "3.6" ]; then
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

if [ "$TRAVIS_PULL_REQUEST" != false ]; then
    echo "Tagging pull request" "$TRAVIS_PULL_REQUEST"
    export BASE="$REPO:pr-$TRAVIS_PULL_REQUEST"
    docker tag "$IMAGE" "$BASE"
    docker tag "$BASE" "$REPO-$TRAVIS_BUILD_NUMBER"
    docker push "$BASE"
    docker push "$REPO:travis-$TRAVIS_BUILD_NUMBER"
    exit 0
fi

echo "Tagging branch " "$TRAVIS_BRANCH"
docker tag "$IMAGE" "$REPO:$COMMIT"
docker tag "$REPO:$COMMIT" "$REPO:$BRANCH"
docker tag "$REPO:$COMMIT" "$REPO:travis-$TRAVIS_BUILD_NUMBER"
docker push "$REPO:$COMMIT"
docker push "$REPO:travis-$TRAVIS_BUILD_NUMBER"
docker push "$REPO:$BRANCH"
exit 0
