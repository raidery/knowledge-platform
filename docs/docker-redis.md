docker run -d \
  --name redis \
  --restart unless-stopped \
  -p 6379:6379 \
  --privileged \
  -v /data/redis:/data \
  --memory 2g \
  --cpus 2 \
  redis:8.4.2-alpine \
  redis-server --requirepass "Pass@1234" --appendonly yes 