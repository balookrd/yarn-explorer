import logging
from typing import List, Optional, Tuple
import httpx

from app.models.cluster import ClusterConfig
from app.models.yarn import (
    QueueNode, QueueState, PartitionResourceConfig,
    ResourceAllocation, ClusterMetrics
)

logger = logging.getLogger(__name__)


class YarnClient:
    """
    Асинхронный клиент к YARN ResourceManager REST API.
    Поддерживает RM HA Failover и имперсонацию (doAs).
    """

    def __init__(self, cluster: ClusterConfig):
        self.cluster = cluster
        self._active_rm_url: Optional[str] = None

    async def _get_active_rm(self) -> str:
        """Определяет активный ResourceManager из списка URL."""
        if self._active_rm_url:
            return self._active_rm_url

        for url in self.cluster.resource_manager_urls:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{url}/ws/v1/cluster/info")
                    if resp.status_code == 200:
                        info = resp.json()
                        ha_state = info.get("clusterInfo", {}).get("haState", "ACTIVE")
                        if ha_state == "ACTIVE":
                            self._active_rm_url = url
                            logger.info(f"Активный RM: {url}")
                            return url
            except Exception as e:
                logger.warning(f"RM {url} недоступен: {e}")
                continue

        # Fallback: берём первый URL
        fallback = self.cluster.resource_manager_urls[0]
        self._active_rm_url = fallback
        logger.warning(f"Не удалось определить активный RM, используем: {fallback}")
        return fallback

    def _build_params(self, do_as: str) -> dict:
        """Формирует query-параметры для имперсонации."""
        params = {}
        if self.cluster.impersonation_enabled and do_as:
            params["user.name"] = do_as
        return params

    async def _request(self, path: str, do_as: str) -> dict:
        """Выполняет GET запрос к YARN RM с failover."""
        params = self._build_params(do_as)
        last_error = None

        for attempt in range(len(self.cluster.resource_manager_urls)):
            rm_url = await self._get_active_rm()
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    url = f"{rm_url}{path}"
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    return resp.json()
            except Exception as e:
                logger.warning(f"Ошибка запроса к {rm_url}{path}: {e}")
                last_error = e
                # Сбрасываем кэш активного RM для следующей попытки
                self._active_rm_url = None

        raise RuntimeError(f"Все ResourceManager недоступны: {last_error}")

    async def get_cluster_metrics(self, do_as: str) -> ClusterMetrics:
        """Получает метрики кластера."""
        data = await self._request("/ws/v1/cluster/metrics", do_as)
        m = data.get("clusterMetrics", {})
        return ClusterMetrics(
            total_memory_mb=m.get("totalMB", 0),
            total_vcores=m.get("totalVirtualCores", 0),
            allocated_memory_mb=m.get("allocatedMB", 0),
            allocated_vcores=m.get("allocatedVirtualCores", 0),
            available_memory_mb=m.get("availableMB", 0),
            available_vcores=m.get("availableVirtualCores", 0),
            active_nodes=m.get("activeNodes", 0),
            unhealthy_nodes=m.get("unhealthyNodes", 0),
            total_containers=m.get("containersAllocated", 0),
            running_apps=m.get("appsRunning", 0),
            partitions=self.cluster.partitions,
        )

    async def get_scheduler_info(self, do_as: str) -> dict:
        """Получает информацию о Capacity Scheduler."""
        return await self._request("/ws/v1/cluster/scheduler", do_as)

    async def get_node_labels(self, do_as: str) -> List[str]:
        """Получает список Node Labels (партиций)."""
        try:
            data = await self._request("/ws/v1/cluster/get-node-labels", do_as)
            labels = data.get("nodeLabels", [])
            return [label.get("name", "") for label in labels if label.get("name")]
        except Exception:
            return []

    def _parse_queue_tree(self, queue_json: dict, parent_path: Optional[str] = None) -> QueueNode:
        """Рекурсивно парсит JSON ответ Capacity Scheduler в дерево QueueNode."""
        name = queue_json.get("queueName", "")
        path = f"{parent_path}.{name}" if parent_path else name

        # Партиции
        partitions = {}
        cap = queue_json.get("capacity", 0.0)
        max_cap = queue_json.get("maxCapacity", 100.0)
        is_elastic = max_cap > cap
        partitions["DEFAULT"] = PartitionResourceConfig(
            partition_name="DEFAULT",
            capacity=cap,
            max_capacity=max_cap,
            is_elastic=is_elastic,
            elasticity_ratio=round(max_cap / cap, 2) if cap > 0 else 1.0,
            absolute_resources=ResourceAllocation(
                memory_mb=int(queue_json.get("resourcesUsed", {}).get("memory", 0)),
                vcores=int(queue_json.get("resourcesUsed", {}).get("vCores", 0))
            )
        )

        # Партиции через capacities
        capacities = queue_json.get("capacities", {}).get("queueCapacitiesByPartition", [])
        for part_info in capacities:
            part_name = part_info.get("partitionName", "")
            if part_name and part_name != "":
                p_cap = part_info.get("capacity", 0.0)
                p_max = part_info.get("maxCapacity", 100.0)
                partitions[part_name] = PartitionResourceConfig(
                    partition_name=part_name,
                    capacity=p_cap,
                    max_capacity=p_max,
                    is_elastic=p_max > p_cap,
                    elasticity_ratio=round(p_max / p_cap, 2) if p_cap > 0 else 1.0,
                )

        # Дочерние очереди
        children = []
        queues_data = queue_json.get("queues", {})
        if queues_data:
            child_list = queues_data.get("queue", [])
            if isinstance(child_list, dict):
                child_list = [child_list]
            for child_json in child_list:
                children.append(self._parse_queue_tree(child_json, path))

        state_str = queue_json.get("state", "RUNNING").upper()
        try:
            state = QueueState(state_str)
        except ValueError:
            state = QueueState.RUNNING

        resources_used = queue_json.get("resourcesUsed", {})
        used_mem = resources_used.get("memory", 0)
        used_cores = resources_used.get("vCores", 0)

        return QueueNode(
            name=name,
            path=path,
            parent_path=parent_path,
            is_leaf=len(children) == 0,
            state=state,
            partitions=partitions,
            current_used_resources=ResourceAllocation(memory_mb=used_mem, vcores=used_cores),
            allocated_resources=ResourceAllocation(memory_mb=used_mem, vcores=used_cores),
            current_used_percent=queue_json.get("usedCapacity", 0.0),
            num_applications=queue_json.get("numApplications", 0),
            num_active_applications=queue_json.get("numActiveApplications", 0),
            num_pending_applications=queue_json.get("numPendingApplications", 0),
            children=children,
        )

    async def get_queue_tree(self, do_as: str) -> Tuple[QueueNode, ClusterMetrics]:
        """Полная загрузка дерева очередей и метрик."""
        scheduler_data = await self.get_scheduler_info(do_as)
        metrics = await self.get_cluster_metrics(do_as)

        scheduler_info = scheduler_data.get("scheduler", {}).get("schedulerInfo", {})
        root_queue = self._parse_queue_tree(scheduler_info)

        return root_queue, metrics
