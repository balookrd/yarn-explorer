import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.yarn import QueueDraftItem, PartitionResourceConfig, QueueState
from app.services.capacity_scheduler import validate_queue_balance
from app.services.xml_generator import generate_capacity_scheduler_xml
from app.models.cluster import ClusterConfig, ClusterResources


def _make_queue(name: str, parent: str, capacity: float, max_cap: float, action: str = "modify"):
    path = f"{parent}.{name}" if parent else name
    return QueueDraftItem(
        path=path,
        name=name,
        parent_path=parent,
        action=action,
        is_leaf=True,
        state=QueueState.RUNNING,
        partitions={
            "DEFAULT": PartitionResourceConfig(
                partition_name="DEFAULT",
                capacity=capacity,
                max_capacity=max_cap,
                is_elastic=max_cap > capacity,
                elasticity_ratio=round(max_cap / capacity, 2) if capacity > 0 else 1.0,
            )
        }
    )


class TestValidateQueueBalance:
    def test_balanced_percentage_queues(self):
        queues = [
            _make_queue("spark", "root.prod", 40.0, 80.0),
            _make_queue("flink", "root.prod", 35.0, 50.0),
            _make_queue("trino", "root.prod", 25.0, 25.0),
        ]
        balances = validate_queue_balance(queues, "percentage", "DEFAULT")
        assert len(balances) == 1
        assert balances[0].is_balanced is True
        assert balances[0].status == "ok"
        assert abs(balances[0].total_children_capacity - 100.0) < 0.01

    def test_overallocated(self):
        queues = [
            _make_queue("spark", "root.prod", 50.0, 80.0),
            _make_queue("flink", "root.prod", 40.0, 50.0),
            _make_queue("trino", "root.prod", 30.0, 30.0),
        ]
        balances = validate_queue_balance(queues, "percentage", "DEFAULT")
        assert len(balances) == 1
        assert balances[0].is_balanced is False
        assert balances[0].status == "overallocated"
        assert balances[0].total_children_capacity == 120.0

    def test_underallocated(self):
        queues = [
            _make_queue("spark", "root.prod", 30.0, 80.0),
            _make_queue("flink", "root.prod", 25.0, 50.0),
        ]
        balances = validate_queue_balance(queues, "percentage", "DEFAULT")
        assert len(balances) == 1
        assert balances[0].is_balanced is False
        assert balances[0].status == "underallocated"
        assert balances[0].unallocated_capacity == 45.0

    def test_multiple_branches(self):
        queues = [
            _make_queue("prod", "root", 60.0, 90.0),
            _make_queue("dev", "root", 25.0, 50.0),
            _make_queue("default", "root", 15.0, 20.0),
            _make_queue("spark", "root.prod", 50.0, 80.0),
            _make_queue("flink", "root.prod", 50.0, 50.0),
        ]
        balances = validate_queue_balance(queues, "percentage", "DEFAULT")
        assert len(balances) == 2
        # root ветка
        root_balance = [b for b in balances if b.parent_path == "root"][0]
        assert root_balance.is_balanced is True
        # prod ветка
        prod_balance = [b for b in balances if b.parent_path == "root.prod"][0]
        assert prod_balance.is_balanced is True

    def test_deleted_queues_excluded(self):
        queues = [
            _make_queue("spark", "root.prod", 50.0, 80.0),
            _make_queue("flink", "root.prod", 50.0, 50.0),
            _make_queue("old", "root.prod", 20.0, 20.0, action="delete"),
        ]
        balances = validate_queue_balance(queues, "percentage", "DEFAULT")
        assert balances[0].is_balanced is True
        assert balances[0].total_children_capacity == 100.0


class TestXmlGenerator:
    def _make_cluster(self):
        return ClusterConfig(
            id="test-cluster",
            name="Test Cluster",
            resource_manager_urls=["http://rm1:8088"],
            total_resources=ClusterResources(memory_mb=1048576, vcores=512),
            default_partition="DEFAULT",
            partitions=["DEFAULT"],
        )

    def test_xml_generation(self):
        cluster = self._make_cluster()
        queues = [
            QueueDraftItem(
                path="root",
                name="root",
                parent_path=None,
                action="modify",
                is_leaf=False,
                state=QueueState.RUNNING,
                partitions={"DEFAULT": PartitionResourceConfig(
                    partition_name="DEFAULT", capacity=100.0, max_capacity=100.0,
                    is_elastic=False, elasticity_ratio=1.0,
                )},
            ),
            _make_queue("prod", "root", 60.0, 90.0),
            _make_queue("dev", "root", 40.0, 50.0),
        ]
        xml = generate_capacity_scheduler_xml(queues, cluster, generated_by="test_user")
        assert '<?xml version="1.0"' in xml
        assert '<configuration>' in xml
        assert '</configuration>' in xml
        assert 'yarn.scheduler.capacity.root.prod.capacity' in xml
        assert '60.0' in xml
        assert 'yarn.scheduler.capacity.root.queues' in xml

    def test_xml_has_valid_structure(self):
        import xml.etree.ElementTree as ET
        cluster = self._make_cluster()
        queues = [
            _make_queue("default", "root", 100.0, 100.0),
        ]
        xml = generate_capacity_scheduler_xml(queues, cluster)
        # Должен парситься как валидный XML
        tree = ET.fromstring(xml.split("-->")[-1].strip())
        assert tree.tag == "configuration"
        props = tree.findall("property")
        assert len(props) > 0
        for prop in props:
            assert prop.find("name") is not None
            assert prop.find("value") is not None

    def test_xml_generation_absolute(self):
        cluster = self._make_cluster()
        queues = [
            _make_queue("prod", "root", 60.0, 90.0),
        ]
        xml = generate_capacity_scheduler_xml(queues, cluster, resource_mode="absolute")
        assert "[memory=" in xml
        assert "vcores=" in xml

    def test_xml_generation_per_queue_mode(self):
        cluster = self._make_cluster()  # cluster.resource_mode is "percentage"
        q1 = _make_queue("prod", "root", 60.0, 90.0)
        q1.resource_mode = "absolute"
        q2 = _make_queue("dev", "root", 40.0, 50.0)
        q2.resource_mode = "percentage"
        xml = generate_capacity_scheduler_xml([q1, q2], cluster)
        # q1 should be generated in absolute format
        assert "yarn.scheduler.capacity.root.prod.capacity" in xml
        assert "[memory=" in xml
        # q2 should have percentage format
        assert "<name>yarn.scheduler.capacity.root.dev.capacity</name>\n    <value>40.0</value>" in xml

    def test_xml_generation_advanced_properties(self):
        cluster = self._make_cluster()
        q = _make_queue("prod", "root", 100.0, 100.0)
        q.is_leaf = True
        q.user_limit_factor = 2.5
        q.ordering_policy = "fair"

        xml = generate_capacity_scheduler_xml(
            [q],
            cluster,
            queue_mappings="u:%user:%user,g:devs:root.prod",
            queue_mappings_override=True,
        )

        assert "yarn.scheduler.capacity.root.prod.user-limit-factor" in xml
        assert "<value>2.5</value>" in xml
        assert "yarn.scheduler.capacity.root.prod.ordering-policy" in xml
        assert "<value>fair</value>" in xml
        assert "yarn.scheduler.capacity.queue-mappings" in xml
        assert "<value>u:%user:%user,g:devs:root.prod</value>" in xml
        assert "yarn.scheduler.capacity.queue-mappings-override.enable" in xml
        assert "<value>true</value>" in xml
