from abc import ABC, abstractmethod
from typing import Dict, List


from ..schemas.node_type_schemas import NodeTypeSchema
from .node_types import (
    get_supported_node_types_by_group,
    get_deprecated_node_types,
    NodeCategory,
    NodeGroup,
)


class NodeRepository(ABC):
    """
    Abstract base class for node repositories.
    """

    @abstractmethod
    def get_node_groups(self) -> List[NodeGroup]:
        pass

    @abstractmethod
    def get_node_types_for_group(
        self, group: NodeGroup
    ) -> List[NodeTypeSchema]:
        pass

    @abstractmethod
    def get_all_node_types_by_group(
        self,
    ) -> Dict[NodeGroup, List[NodeTypeSchema]]:
        pass

    @abstractmethod
    def get_node_type(self, node_type_name: str) -> NodeTypeSchema:
        pass

    @abstractmethod
    def is_valid_node_type(self, node_type_name: str) -> bool:
        pass


class StaticNodeRepository(NodeRepository):
    """
    Static node repository that uses a predefined set of node types.
    """

    def __init__(self):
        super().__init__()
        self.nodes = get_supported_node_types_by_group()
        self.deprecated_node_types = get_deprecated_node_types()

    def get_node_groups(self) -> List[NodeGroup]:
        return self.nodes.keys()

    def get_node_types_for_group(
        self, group: NodeGroup
    ) -> List[NodeTypeSchema]:
        return self.nodes[group]

    def get_all_node_types_by_group(
        self,
    ) -> Dict[NodeGroup, List[NodeTypeSchema]]:
        return self.nodes

    def get_node_type(self, node_type_name: str) -> NodeTypeSchema:
        for _, node_types in self.nodes.items():
            for node_type in node_types:
                if node_type.node_type_name == node_type_name:
                    return node_type
        raise ValueError(f"Node type '{node_type_name}' not found.")

    def is_valid_node_type(self, raw_node_type_name: str) -> bool:
        for _, node_types in self.nodes.items():
            for node_type in node_types:
                if node_type.node_type_name == raw_node_type_name:
                    return True
        for node_type in self.deprecated_node_types:
            if node_type.node_type_name == raw_node_type_name:
                return True
        return False


class CompositeNodeRepository(NodeRepository):
    """
    Composite node repository that uses a list of node repositories.
    """

    def __init__(self, repositories: List[NodeRepository]):
        self.group_repository_map: Dict[NodeGroup, NodeRepository] = {}
        for repository in repositories:
            for group in repository.get_node_groups():
                if group in self.group_repository_map:
                    raise ValueError(f"Duplicate node group: {group}")
                self.group_repository_map[group] = repository

    def get_node_groups(self) -> List[NodeGroup]:
        return self.group_repository_map.keys()

    def get_node_types_for_group(
        self, group: NodeGroup
    ) -> List[NodeTypeSchema]:
        return self.group_repository_map[group].get_node_types_for_group(
            group
        )

    def get_all_node_types_by_group(
        self,
    ) -> Dict[NodeGroup, List[NodeTypeSchema]]:
        return {
            group: self.group_repository_map[
                group
            ].get_node_types_for_group(group)
            for group in self.group_repository_map.keys()
        }
    
    def get_node_type(self, node_type_name: str) -> NodeTypeSchema:
        for repository in self.group_repository_map.values():
            if repository.is_valid_node_type(node_type_name):
                return repository.get_node_type(node_type_name)
        raise ValueError(f"Node type '{node_type_name}' not found.")

    def is_valid_node_type(self, raw_node_type_name: str) -> bool:
        return any(
            repository.is_valid_node_type(raw_node_type_name)
            for repository in self.group_repository_map.values()
        )
