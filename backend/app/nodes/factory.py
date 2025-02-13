import importlib
from typing import Annotated, Any, List, Dict

from fastapi import Depends

from .onegrep_types import OneGrepNodeRepository, get_onegrep_node_repository

from .repository import CompositeNodeRepository, NodeRepository, StaticNodeRepository

from ..schemas.node_type_schemas import NodeTypeSchema
from .base import BaseNode
from .node_types import NodeGroup

class NodeFactory:
    """
    Factory for creating node instances from a configuration.
    Node type definitions are expected to be in the nodes package.

    Conventions:
    - The node class should be named <NodeTypeName>Node
    - The config model should be named <NodeTypeName>NodeConfig
    - The input model should be named <NodeTypeName>NodeInput
    - The output model should be named <NodeTypeName>NodeOutput
    - There should be only one node type class per module
    - The module name should be the snake_case version of the node type name

    Example:
    - Node type: Example
    - Node class: ExampleNode
    - Config model: ExampleNodeConfig
    - Input model: ExampleNodeInput
    - Output model: ExampleNodeOutput
    - Module name: example

    - Node type: MCTS
    - Node class: MCTSNode
    - Config model: MCTSNodeConfig
    - Input model: MCTSNodeInput
    - Output model: MCTSNodeOutput
    - Module name: llm.mcts
    """

    def __init__(self, node_repository: NodeRepository):
        self.node_repository = node_repository

    def get_all_node_types_by_group(self) -> Dict[NodeGroup, List[NodeTypeSchema]]:
        """
        Returns a dictionary of all available node types grouped by category.
        """
        return self.node_repository.get_all_node_types_by_group()

    def is_valid_node_type(self, node_type_name: str) -> bool:
        """
        Checks if a node type is valid.
        """
        return self.node_repository.is_valid_node_type(node_type_name)

    def create_node(self, node_name: str, node_type_name: str, config: Any) -> BaseNode:
        """
        Creates a node instance from a configuration.
        """
        if not self.node_repository.is_valid_node_type(node_type_name):
            raise ValueError(f"Node type '{node_type_name}' is not valid.")

        node_type_schema = self.node_repository.get_node_type(node_type_name)
        node_class = node_type_schema.node_class
        return node_class(name=node_name, config=node_class.config_model(**config))


async def get_node_repository(
    onegrep_node_repository: Annotated[
        OneGrepNodeRepository, Depends(get_onegrep_node_repository)
    ]
) -> NodeRepository:
    """
    Returns a node repository.
    """
    return CompositeNodeRepository([StaticNodeRepository(), onegrep_node_repository])


async def get_node_factory(
    node_repository: Annotated[NodeRepository, Depends(get_node_repository)]
) -> NodeFactory:
    """
    Returns a node factory.
    """
    return NodeFactory(node_repository)
