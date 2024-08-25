docker build -f Dockerfile -t pdf-processor:1.6 .
docker tag pdf-processor:1.6 harbor.yj2025.com/library/pdf-processor:1.6
docker push harbor.yj2025.com/library/pdf-processor:1.6