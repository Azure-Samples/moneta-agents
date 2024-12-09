az acr login --name moneta.azurecr.io
docker build --tag abertaga27/moneta-ai-backend:v1.1.6 .
docker tag abertaga27/moneta-ai-backend:v1.1.6 moneta.azurecr.io/moneta-ai-backend:v1.1.6
docker push moneta.azurecr.io/moneta-ai-backend:v1.1.6