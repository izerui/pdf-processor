docker build -f Dockerfile -t pdf-processor:1.0
docker tag pdf-processor:1.0 harbor.yj2025.com/library/pdf-processor:1.0
docker push harbor.yj2025.com/library/pdf-processor:1.0