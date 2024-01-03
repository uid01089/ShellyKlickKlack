pip freeze > requirements.txt
docker build -t shellyklickklack -f Dockerfile .
docker tag shellyklickklack:latest docker.diskstation/shellyklickklack
docker push docker.diskstation/shellyklickklack:latest