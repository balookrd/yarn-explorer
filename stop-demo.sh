#!/bin/bash
echo "=== Остановка демонстрационного стенда YARN Explorer ==="
docker compose -f docker-compose.demo.yml down -v
echo "Стенд остановлен и тома очищены."
